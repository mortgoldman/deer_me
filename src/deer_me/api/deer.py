"""High-level Deer animator class.

This is the main entry point for animators. It wraps the locomotion state
machine and skeleton into simple, expressive method calls:

    deer = Deer()
    deer.walk(speed=1.2, direction=0.0)
    deer.trot(speed=1.5)
    deer.idle()

Each call requests a state transition. Call `update(dt)` to advance time,
and `pose()` to get the current Pose. For Blender integration, use
`bake_to_blender()` or the Sequence API.

Pure Python except for optional Blender export methods (lazy-imported).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Tuple

from deer_me.core.skeleton import Skeleton
from deer_me.core.state_machine import LocoState, LocomotionStateMachine
from deer_me.core.types import Pose

if TYPE_CHECKING:
    import bpy


@dataclass
class Deer:
    """High-level animator interface for a deer character.

    Args:
        skeleton: Skeleton definition. Uses the default deer rig if omitted.
        name: Name for this deer (used in Blender object naming).
        fps: Frames per second for time calculations.
    """

    skeleton: Skeleton = field(default_factory=Skeleton)
    name: str = "Deer"
    fps: float = 24.0

    _sm: LocomotionStateMachine = field(
        default_factory=LocomotionStateMachine, repr=False
    )
    _time: float = field(default=0.0, repr=False)

    # ---------------------------------------------------------------------------
    # Locomotion commands
    # ---------------------------------------------------------------------------

    def walk(self, speed: float = 1.0) -> bool:
        """Transition to walking.

        Args:
            speed: Walk speed multiplier (1.0 = normal).

        Returns:
            True if the transition was accepted.
        """
        return self._sm.request_transition(LocoState.WALK, speed=speed)

    def trot(self, speed: float = 1.3) -> bool:
        """Transition to trotting.

        Args:
            speed: Trot speed multiplier.

        Returns:
            True if the transition was accepted.
        """
        return self._sm.request_transition(LocoState.TROT, speed=speed)

    def gallop(self, speed: float = 2.0) -> bool:
        """Transition to galloping.

        Note: Cannot gallop directly from idle — must walk or trot first.

        Returns:
            True if the transition was accepted.
        """
        return self._sm.request_transition(LocoState.GALLOP, speed=speed)

    def idle(self) -> bool:
        """Transition to idle (standing still).

        Note: Cannot idle directly from gallop — must slow to trot/walk first.

        Returns:
            True if the transition was accepted.
        """
        return self._sm.request_transition(LocoState.IDLE, speed=0.0)

    def turn_left(self, speed: float = 1.0) -> bool:
        """Transition to turning left.

        Returns:
            True if the transition was accepted.
        """
        return self._sm.request_transition(LocoState.TURN_LEFT, speed=speed)

    def turn_right(self, speed: float = 1.0) -> bool:
        """Transition to turning right.

        Returns:
            True if the transition was accepted.
        """
        return self._sm.request_transition(LocoState.TURN_RIGHT, speed=speed)

    # ---------------------------------------------------------------------------
    # Simulation
    # ---------------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the animation by dt seconds."""
        self._sm.update(dt)
        self._time += dt

    def advance_frames(self, num_frames: int = 1) -> None:
        """Advance by a number of frames at the configured fps."""
        dt = num_frames / self.fps
        self.update(dt)

    def pose(self) -> Pose:
        """Get the current pose of the deer."""
        return self._sm.evaluate(self.skeleton)

    # ---------------------------------------------------------------------------
    # State queries
    # ---------------------------------------------------------------------------

    @property
    def state(self) -> LocoState:
        """Current locomotion state."""
        return self._sm.current_state

    @property
    def speed(self) -> float:
        """Current speed parameter."""
        return self._sm.speed

    @property
    def is_transitioning(self) -> bool:
        """Whether the deer is currently blending between states."""
        return self._sm.is_transitioning

    @property
    def time(self) -> float:
        """Total elapsed time in seconds."""
        return self._time

    @property
    def cycle_phase(self) -> float:
        """Current gait cycle phase [0, 1)."""
        return self._sm.cycle_phase

    def can_gallop(self) -> bool:
        """Whether gallop is available from the current state."""
        return self._sm.can_transition(LocoState.GALLOP)

    def can_idle(self) -> bool:
        """Whether idle is available from the current state."""
        return self._sm.can_transition(LocoState.IDLE)

    # ---------------------------------------------------------------------------
    # Pose generation helpers
    # ---------------------------------------------------------------------------

    def generate_frames(
        self, num_frames: int, start_frame: int = 1
    ) -> List[Tuple[int, Pose]]:
        """Generate a sequence of (frame_number, Pose) pairs.

        Useful for baking animations. Advances internal time by num_frames.

        Args:
            num_frames: How many frames to generate.
            start_frame: Frame number of the first pose.

        Returns:
            List of (frame, Pose) tuples.
        """
        sequence = []
        dt = 1.0 / self.fps
        for i in range(num_frames):
            self.update(dt)
            sequence.append((start_frame + i, self.pose()))
        return sequence

    def reset(self) -> None:
        """Reset the deer to idle at time zero."""
        self._sm = LocomotionStateMachine()
        self._time = 0.0

    # ---------------------------------------------------------------------------
    # Blender export (lazy imports)
    # ---------------------------------------------------------------------------

    def bake_to_blender(
        self,
        num_frames: int = 240,
        setup_scene: bool = True,
        create_proxy: bool = True,
    ) -> "bpy.types.Object":
        """Generate animation and bake it into Blender.

        This is the one-call method to go from nothing to a viewable animation.

        Args:
            num_frames: Total frames to generate.
            setup_scene: If True, create ground, lights, camera.
            create_proxy: If True, create a proxy deer mesh.

        Returns:
            The Blender armature object.
        """
        from deer_me.adapter.keyframe import batch_insert_sequence, set_frame_range
        from deer_me.adapter.rig import create_armature
        from deer_me.adapter.scene import setup_deer_scene
        from deer_me.adapter.skin import create_proxy_mesh

        if setup_scene:
            setup_deer_scene(fps=int(self.fps), frame_end=num_frames)

        arm_obj = create_armature(self.skeleton, name=f"{self.name}Armature")

        sequence = self.generate_frames(num_frames)
        batch_insert_sequence(arm_obj, sequence)
        set_frame_range(1, num_frames)

        if create_proxy:
            create_proxy_mesh(arm_obj, name=f"{self.name}Mesh")

        return arm_obj
