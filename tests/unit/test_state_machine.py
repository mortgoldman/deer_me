"""Tests for the locomotion state machine."""

import math

import numpy as np
import pytest

from deer_me.core.skeleton import Skeleton
from deer_me.core.state_machine import (
    LocoState,
    LocomotionStateMachine,
    TransitionRule,
    _build_default_transitions,
)
from deer_me.core.types import Pose, Quaternion


# ---------------------------------------------------------------------------
# Transition rules
# ---------------------------------------------------------------------------


class TestTransitionRules:
    def test_default_rules_exist(self):
        rules = _build_default_transitions()
        # Should have entries for all non-self pairs
        n_states = len(LocoState)
        # Minus the disallowed ones, but they still exist in the dict
        assert len(rules) == n_states * (n_states - 1)

    def test_idle_to_gallop_disallowed(self):
        rules = _build_default_transitions()
        assert rules[(LocoState.IDLE, LocoState.GALLOP)].allowed is False

    def test_gallop_to_idle_disallowed(self):
        rules = _build_default_transitions()
        assert rules[(LocoState.GALLOP, LocoState.IDLE)].allowed is False

    def test_walk_to_trot_allowed(self):
        rules = _build_default_transitions()
        assert rules[(LocoState.WALK, LocoState.TROT)].allowed is True

    def test_walk_trot_faster_blend(self):
        rules = _build_default_transitions()
        wt = rules[(LocoState.WALK, LocoState.TROT)].blend_duration
        tg = rules[(LocoState.TROT, LocoState.GALLOP)].blend_duration
        assert wt < tg  # Walk↔trot blends faster than trot↔gallop


# ---------------------------------------------------------------------------
# State machine basics
# ---------------------------------------------------------------------------


class TestStateMachineBasics:
    def test_initial_state(self):
        sm = LocomotionStateMachine()
        assert sm.current_state == LocoState.IDLE
        assert sm.speed == 0.0
        assert sm.is_transitioning is False

    def test_request_same_state(self):
        sm = LocomotionStateMachine()
        result = sm.request_transition(LocoState.IDLE, speed=0.0)
        assert result is True
        assert sm.is_transitioning is False

    def test_request_walk(self):
        sm = LocomotionStateMachine()
        result = sm.request_transition(LocoState.WALK, speed=1.0)
        assert result is True
        assert sm.is_transitioning is True
        assert sm.target_state == LocoState.WALK

    def test_disallowed_transition(self):
        sm = LocomotionStateMachine()
        result = sm.request_transition(LocoState.GALLOP, speed=2.0)
        assert result is False
        assert sm.current_state == LocoState.IDLE

    def test_can_transition(self):
        sm = LocomotionStateMachine()
        assert sm.can_transition(LocoState.WALK) is True
        assert sm.can_transition(LocoState.GALLOP) is False
        assert sm.can_transition(LocoState.IDLE) is True  # Already there


# ---------------------------------------------------------------------------
# Update and blend progression
# ---------------------------------------------------------------------------


class TestUpdateAndBlend:
    def test_blend_progress_advances(self):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.1)  # 0.1s into a 0.4s blend
        assert 0.2 < sm.blend_progress < 0.3

    def test_blend_completes(self):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        # Update past the blend duration
        sm.update(0.5)
        assert sm.is_transitioning is False
        assert sm.current_state == LocoState.WALK
        assert sm.speed == 1.0

    def test_cycle_phase_advances(self):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)  # Complete transition
        initial_phase = sm.cycle_phase
        sm.update(0.5)
        assert sm.cycle_phase != initial_phase

    def test_cycle_phase_wraps(self):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)  # Complete transition
        # Run for many seconds
        for _ in range(100):
            sm.update(0.1)
        assert 0.0 <= sm.cycle_phase < 1.0

    def test_idle_phase_advances_slowly(self):
        sm = LocomotionStateMachine()
        sm.update(1.0)
        assert sm.cycle_phase > 0.0
        assert sm.cycle_phase < 0.5  # Much slower than locomotion


# ---------------------------------------------------------------------------
# Transition sequences
# ---------------------------------------------------------------------------


class TestTransitionSequences:
    def test_idle_walk_trot(self):
        sm = LocomotionStateMachine()

        # Idle → Walk
        assert sm.request_transition(LocoState.WALK, speed=1.0)
        for _ in range(10):
            sm.update(0.05)
        assert sm.current_state == LocoState.WALK

        # Walk → Trot
        assert sm.request_transition(LocoState.TROT, speed=1.5)
        for _ in range(10):
            sm.update(0.05)
        assert sm.current_state == LocoState.TROT

    def test_walk_to_gallop_via_trot(self):
        sm = LocomotionStateMachine()

        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)
        assert sm.current_state == LocoState.WALK

        sm.request_transition(LocoState.TROT, speed=1.5)
        sm.update(0.5)
        assert sm.current_state == LocoState.TROT

        sm.request_transition(LocoState.GALLOP, speed=2.0)
        sm.update(0.6)
        assert sm.current_state == LocoState.GALLOP

    def test_interrupt_transition(self):
        """Requesting a new transition mid-blend should work."""
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.1)  # Mid-blend

        # Interrupt with trot (from walk, since that's where we're heading)
        result = sm.request_transition(LocoState.TROT, speed=1.5)
        assert result is True
        assert sm.target_state == LocoState.TROT

        # Complete
        sm.update(0.5)
        assert sm.current_state == LocoState.TROT

    def test_turn_from_walk(self):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)

        assert sm.request_transition(LocoState.TURN_LEFT, speed=1.0)
        sm.update(0.3)
        assert sm.current_state == LocoState.TURN_LEFT

    def test_full_sequence_idle_walk_trot_walk_idle(self):
        sm = LocomotionStateMachine()

        states = [
            (LocoState.WALK, 1.0),
            (LocoState.TROT, 1.5),
            (LocoState.WALK, 1.0),
            (LocoState.IDLE, 0.0),
        ]
        for target, spd in states:
            assert sm.request_transition(target, speed=spd), f"Failed: → {target}"
            sm.update(0.6)  # Enough to complete any blend
            assert sm.current_state == target


# ---------------------------------------------------------------------------
# Custom rules
# ---------------------------------------------------------------------------


class TestCustomRules:
    def test_override_blend_duration(self):
        sm = LocomotionStateMachine()
        sm.set_transition_rule(
            TransitionRule(LocoState.IDLE, LocoState.WALK, blend_duration=1.0)
        )
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)
        # Should still be transitioning (1.0s blend, only 0.5s elapsed)
        assert sm.is_transitioning is True
        sm.update(0.6)
        assert sm.is_transitioning is False

    def test_disallow_transition(self):
        sm = LocomotionStateMachine()
        sm.set_transition_rule(
            TransitionRule(LocoState.IDLE, LocoState.WALK, allowed=False)
        )
        assert sm.request_transition(LocoState.WALK) is False

    def test_allow_idle_to_gallop(self):
        """Override default to allow direct idle→gallop."""
        sm = LocomotionStateMachine()
        sm.set_transition_rule(
            TransitionRule(LocoState.IDLE, LocoState.GALLOP, blend_duration=0.8)
        )
        assert sm.request_transition(LocoState.GALLOP, speed=2.0) is True


# ---------------------------------------------------------------------------
# Pose evaluation
# ---------------------------------------------------------------------------


class TestPoseEvaluation:
    @pytest.fixture
    def skeleton(self):
        return Skeleton()

    def test_idle_pose(self, skeleton):
        sm = LocomotionStateMachine()
        sm.update(0.5)
        pose = sm.evaluate(skeleton)
        assert isinstance(pose, Pose)
        assert len(pose.joints) > 0

    def test_walk_pose(self, skeleton):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)
        pose = sm.evaluate(skeleton)
        assert isinstance(pose, Pose)

    def test_blend_pose_during_transition(self, skeleton):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.2)  # Mid-transition
        assert sm.is_transitioning
        pose = sm.evaluate(skeleton)
        assert isinstance(pose, Pose)

    def test_poses_vary_with_phase(self, skeleton):
        """Poses at different cycle phases should not be identical."""
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)

        pose_a = sm.evaluate(skeleton)
        sm.update(0.3)
        pose_b = sm.evaluate(skeleton)

        # At least some joints should differ
        any_differ = False
        for name in pose_a.joints:
            if name in pose_b.joints:
                pa = pose_a.joints[name].rotation.to_array()
                pb = pose_b.joints[name].rotation.to_array()
                if not np.allclose(pa, pb, atol=1e-6):
                    any_differ = True
                    break
        assert any_differ

    def test_turn_pose(self, skeleton):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)
        sm.request_transition(LocoState.TURN_LEFT, speed=1.0)
        sm.update(0.3)
        pose = sm.evaluate(skeleton)
        assert isinstance(pose, Pose)

    def test_gallop_pose(self, skeleton):
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)
        sm.request_transition(LocoState.TROT, speed=1.5)
        sm.update(0.5)
        sm.request_transition(LocoState.GALLOP, speed=2.0)
        sm.update(0.6)
        pose = sm.evaluate(skeleton)
        assert isinstance(pose, Pose)
