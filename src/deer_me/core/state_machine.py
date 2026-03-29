"""Locomotion state machine with cross-fade blending.

Manages transitions between locomotion states (idle, walk, trot, gallop, turn)
with configurable blend durations. During a transition, the system cross-fades
between the outgoing and incoming states.

Pure Python — no Blender dependency.

Usage:
    sm = LocomotionStateMachine()
    sm.request_transition(LocoState.WALK, speed=1.0)

    # Each frame:
    sm.update(dt)
    pose = sm.evaluate(skeleton, cycle_phase)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, Tuple

from .gaits import (
    GAIT_PRESETS,
    GaitParams,
    body_bob,
    body_pitch,
    compute_foot_target,
)
from .interpolation import blend_pose, smoothstep
from .skeleton import (
    FRONT_HOOF_L,
    FRONT_HOOF_R,
    HEAD,
    NECK_BASE,
    NECK_MID,
    REAR_HOOF_L,
    REAR_HOOF_R,
    ROOT,
    SPINE_BASE,
    SPINE_MID,
    SPINE_UPPER,
    TAIL_BASE,
    TAIL_TIP,
    Skeleton,
)
from .spine import (
    compute_neck_rotations,
    compute_spine_rotations as compute_spine_rots,
    compute_tail_rotations,
)
from .types import GaitType, LegId, Pose, Quaternion, vec3


# ---------------------------------------------------------------------------
# Locomotion states
# ---------------------------------------------------------------------------


class LocoState(Enum):
    """High-level locomotion states."""

    IDLE = auto()
    WALK = auto()
    TROT = auto()
    GALLOP = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()


# Map locomotion states to gait types (where applicable)
_STATE_TO_GAIT: Dict[LocoState, GaitType] = {
    LocoState.WALK: GaitType.WALK,
    LocoState.TROT: GaitType.TROT,
    LocoState.GALLOP: GaitType.GALLOP,
}


# ---------------------------------------------------------------------------
# Transition rules
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TransitionRule:
    """Defines how one state transitions to another."""

    from_state: LocoState
    to_state: LocoState

    # Blend duration in seconds
    blend_duration: float = 0.4

    # Whether the transition is allowed
    allowed: bool = True


def _build_default_transitions() -> Dict[Tuple[LocoState, LocoState], TransitionRule]:
    """Build the default transition table.

    Most transitions are allowed with varying blend durations.
    Direct idle↔gallop requires passing through walk/trot.
    """
    rules: Dict[Tuple[LocoState, LocoState], TransitionRule] = {}

    all_states = list(LocoState)

    # Default: all transitions allowed with standard blend
    for from_s in all_states:
        for to_s in all_states:
            if from_s == to_s:
                continue
            rules[(from_s, to_s)] = TransitionRule(
                from_state=from_s,
                to_state=to_s,
                blend_duration=0.4,
            )

    # Faster blends for similar gaits
    for pair in [
        (LocoState.WALK, LocoState.TROT),
        (LocoState.TROT, LocoState.WALK),
    ]:
        rules[pair].blend_duration = 0.3

    # Slower blends for large gait changes
    for pair in [
        (LocoState.TROT, LocoState.GALLOP),
        (LocoState.GALLOP, LocoState.TROT),
    ]:
        rules[pair].blend_duration = 0.5

    # Disallow direct idle↔gallop (must go through walk or trot)
    rules[(LocoState.IDLE, LocoState.GALLOP)].allowed = False
    rules[(LocoState.GALLOP, LocoState.IDLE)].allowed = False

    # Quick turn transitions
    for turn in [LocoState.TURN_LEFT, LocoState.TURN_RIGHT]:
        for other in [LocoState.IDLE, LocoState.WALK, LocoState.TROT]:
            rules[(other, turn)].blend_duration = 0.25
            rules[(turn, other)].blend_duration = 0.25

    return rules


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


@dataclass
class LocomotionStateMachine:
    """Manages locomotion state transitions with cross-fade blending.

    The state machine tracks:
    - Current state and its gait cycle phase
    - Pending transition (if any) with blend progress
    - Speed parameter that scales gait cycle rate and stride
    """

    current_state: LocoState = LocoState.IDLE
    speed: float = 0.0

    # Gait cycle phase [0, 1) — advances based on gait cycle rate
    cycle_phase: float = 0.0

    # Transition state
    _target_state: Optional[LocoState] = field(default=None, repr=False)
    _target_speed: float = field(default=0.0, repr=False)
    _blend_progress: float = field(default=0.0, repr=False)
    _blend_duration: float = field(default=0.4, repr=False)
    _is_transitioning: bool = field(default=False, repr=False)

    # Previous state's frozen phase for blending
    _prev_phase: float = field(default=0.0, repr=False)
    _prev_state: LocoState = field(default=LocoState.IDLE, repr=False)

    # Transition rules
    _rules: Dict[Tuple[LocoState, LocoState], TransitionRule] = field(
        default_factory=_build_default_transitions, repr=False
    )

    @property
    def is_transitioning(self) -> bool:
        return self._is_transitioning

    @property
    def blend_progress(self) -> float:
        """Current blend progress (0 = fully old state, 1 = fully new state)."""
        return self._blend_progress

    @property
    def target_state(self) -> Optional[LocoState]:
        return self._target_state if self._is_transitioning else None

    def can_transition(self, to_state: LocoState) -> bool:
        """Check if a transition from the current state is allowed."""
        if to_state == self.current_state and not self._is_transitioning:
            return True  # Already there
        key = (self.current_state, to_state)
        rule = self._rules.get(key)
        return rule is not None and rule.allowed

    def request_transition(self, to_state: LocoState, speed: float = 1.0) -> bool:
        """Request a state transition.

        Returns True if the transition was accepted, False if not allowed.
        If already transitioning, the new request replaces the current one
        (blending from the current blended state).
        """
        if to_state == self.current_state and not self._is_transitioning:
            self.speed = speed
            return True

        effective_from = self.current_state
        if self._is_transitioning and self._target_state is not None:
            # Already mid-transition — transition from wherever we're heading
            effective_from = self._target_state

        key = (effective_from, to_state)
        rule = self._rules.get(key)

        if rule is None or not rule.allowed:
            return False

        # Start the transition
        self._prev_state = self.current_state
        self._prev_phase = self.cycle_phase
        if self._is_transitioning and self._target_state is not None:
            # Chain: was already transitioning, snap to target as new "current"
            self.current_state = self._target_state
            self._prev_state = self._target_state
            self._prev_phase = self.cycle_phase

        self._target_state = to_state
        self._target_speed = speed
        self._blend_progress = 0.0
        self._blend_duration = rule.blend_duration
        self._is_transitioning = True

        return True

    def update(self, dt: float) -> None:
        """Advance the state machine by dt seconds.

        Updates the gait cycle phase and blend progress.
        """
        # Advance blend if transitioning
        if self._is_transitioning:
            self._blend_progress += dt / self._blend_duration
            if self._blend_progress >= 1.0:
                self._blend_progress = 1.0
                self._finish_transition()

            # Interpolate speed during transition
            blend_t = smoothstep(self._blend_progress)
            effective_speed = self.speed + blend_t * (self._target_speed - self.speed)
        else:
            effective_speed = self.speed

        # Advance cycle phase based on current gait's cycle rate
        gait_type = _STATE_TO_GAIT.get(self.current_state)
        if gait_type is not None and gait_type in GAIT_PRESETS:
            rate = GAIT_PRESETS[gait_type].cycle_rate * effective_speed
            self.cycle_phase = (self.cycle_phase + rate * dt) % 1.0
        elif self.current_state == LocoState.IDLE:
            # Idle: slow breathing-like cycle for subtle motion
            self.cycle_phase = (self.cycle_phase + 0.15 * dt) % 1.0
        else:
            # Turns use walk rate
            rate = GAIT_PRESETS[GaitType.WALK].cycle_rate * effective_speed
            self.cycle_phase = (self.cycle_phase + rate * dt) % 1.0

    def _finish_transition(self) -> None:
        """Complete the current transition."""
        if self._target_state is not None:
            self.current_state = self._target_state
            self.speed = self._target_speed
        self._target_state = None
        self._is_transitioning = False
        self._blend_progress = 0.0

    def get_transition_rule(
        self, from_state: LocoState, to_state: LocoState
    ) -> Optional[TransitionRule]:
        """Look up the transition rule between two states."""
        return self._rules.get((from_state, to_state))

    def set_transition_rule(self, rule: TransitionRule) -> None:
        """Override a transition rule."""
        self._rules[(rule.from_state, rule.to_state)] = rule

    # ------------------------------------------------------------------
    # Pose generation
    # ------------------------------------------------------------------

    def evaluate(self, skeleton: Skeleton) -> Pose:
        """Generate the current pose based on state, phase, and blend.

        Returns a complete Pose with rotations/positions for all bones.
        """
        if self._is_transitioning and self._target_state is not None:
            pose_a = self._generate_pose(
                self._prev_state, self._prev_phase, self.speed, skeleton
            )
            pose_b = self._generate_pose(
                self._target_state, self.cycle_phase, self._target_speed, skeleton
            )
            return blend_pose(pose_a, pose_b, self._blend_progress, easing=smoothstep)
        else:
            return self._generate_pose(
                self.current_state, self.cycle_phase, self.speed, skeleton
            )

    def _generate_pose(
        self, state: LocoState, phase: float, speed: float, skeleton: Skeleton
    ) -> Pose:
        """Generate a pose for a specific state/phase/speed."""
        pose = skeleton.rest_pose()

        if state == LocoState.IDLE:
            self._apply_idle(pose, phase, skeleton)
        elif state in (LocoState.WALK, LocoState.TROT, LocoState.GALLOP):
            gait_type = _STATE_TO_GAIT[state]
            params = GAIT_PRESETS[gait_type]
            self._apply_locomotion(pose, phase, speed, params, skeleton)
        elif state in (LocoState.TURN_LEFT, LocoState.TURN_RIGHT):
            direction = -1.0 if state == LocoState.TURN_LEFT else 1.0
            self._apply_turn(pose, phase, speed, direction, skeleton)

        return pose

    def _apply_idle(self, pose: Pose, phase: float, skeleton: Skeleton) -> None:
        """Apply subtle idle animation (breathing, weight shift)."""
        # Gentle breathing on spine
        breath = math.sin(phase * 2.0 * math.pi) * 0.005
        pose.set_rotation(
            SPINE_MID,
            Quaternion.from_axis_angle(vec3(1, 0, 0), breath),
        )

        # Subtle ear flicks
        ear_angle = math.sin(phase * 4.0 * math.pi) * 0.05
        pose.set_rotation(
            "ear_l",
            Quaternion.from_axis_angle(vec3(0, 1, 0), ear_angle),
        )
        pose.set_rotation(
            "ear_r",
            Quaternion.from_axis_angle(vec3(0, 1, 0), -ear_angle * 0.7),
        )

        # Slight tail sway
        tail_angle = math.sin(phase * 3.0 * math.pi) * 0.03
        pose.set_rotation(
            TAIL_BASE,
            Quaternion.from_axis_angle(vec3(0, 0, 1), tail_angle),
        )

    def _apply_locomotion(
        self,
        pose: Pose,
        phase: float,
        speed: float,
        params: GaitParams,
        skeleton: Skeleton,
    ) -> None:
        """Apply full locomotion: feet, spine, neck, tail."""
        # Body bob and pitch
        bob = body_bob(phase, params) * speed
        pitch = body_pitch(phase, params) * speed

        pose.set_rotation(
            ROOT,
            Quaternion.from_axis_angle(vec3(1, 0, 0), pitch),
        )
        root_pos = pose.get(ROOT).position.copy()
        root_pos[2] += bob
        pose.set_position(ROOT, root_pos)

        # Spine undulation
        spine_bones = [SPINE_BASE, SPINE_MID, SPINE_UPPER]
        spine_rots = compute_spine_rots(phase, speed, num_bones=3)
        for bone_name, rot in zip(spine_bones, spine_rots):
            pose.set_rotation(bone_name, rot)

        # Neck and head
        neck_bones = [NECK_BASE, NECK_MID, HEAD]
        spine_lateral = 0.0
        if len(spine_rots) > 0:
            # Approximate lateral from first spine bone
            arr = spine_rots[0].to_array()
            spine_lateral = arr[2] * 2.0  # rough Y-rotation component
        neck_rots = compute_neck_rotations(
            phase, speed, body_pitch=pitch, body_lateral=spine_lateral
        )
        for bone_name, rot in zip(neck_bones, neck_rots):
            pose.set_rotation(bone_name, rot)

        # Tail
        tail_bones = [TAIL_BASE, TAIL_TIP]
        tail_rots = compute_tail_rotations(phase, speed)
        for bone_name, rot in zip(tail_bones, tail_rots):
            pose.set_rotation(bone_name, rot)

        # Foot targets (store as positions — IK applied by adapter layer)
        leg_map = {
            LegId.FRONT_LEFT: FRONT_HOOF_L,
            LegId.FRONT_RIGHT: FRONT_HOOF_R,
            LegId.REAR_LEFT: REAR_HOOF_L,
            LegId.REAR_RIGHT: REAR_HOOF_R,
        }
        rest = skeleton.rest_pose()
        for leg_id, hoof_name in leg_map.items():
            rest_pos = rest.joints[hoof_name].position
            target = compute_foot_target(phase, leg_id, params, rest_pos, speed)
            pose.set_position(hoof_name, target)

    def _apply_turn(
        self,
        pose: Pose,
        phase: float,
        speed: float,
        direction: float,
        skeleton: Skeleton,
    ) -> None:
        """Apply a turning motion.

        Uses walk gait as base with added lateral spine bend and head turn.
        """
        # Base walk motion
        self._apply_locomotion(
            pose, phase, max(speed, 0.5), GAIT_PRESETS[GaitType.WALK], skeleton
        )

        # Add spine lateral bend toward turn direction
        turn_angle = direction * 0.06 * min(speed, 1.5)
        for bone in [SPINE_BASE, SPINE_MID, SPINE_UPPER]:
            existing = pose.get(bone).rotation
            turn_rot = Quaternion.from_axis_angle(vec3(0, 0, 1), turn_angle)
            pose.set_rotation(bone, turn_rot * existing)

        # Head looks into the turn
        head_turn = direction * 0.1
        existing_head = pose.get(HEAD).rotation
        head_rot = Quaternion.from_axis_angle(vec3(0, 0, 1), head_turn)
        pose.set_rotation(HEAD, head_rot * existing_head)
