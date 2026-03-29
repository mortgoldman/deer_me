"""Timeline sequencer — chain animation commands over frames.

Provides a fluent builder API for scripting deer animations:

    seq = Sequence(deer)
    seq.at(0).walk(speed=1.0)
    seq.at(120).trot(speed=1.5)
    seq.at(200).idle()
    frames = seq.bake()

The sequencer applies commands at specified frames, advances the deer's
internal state between them, and collects the resulting poses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from deer_me.core.state_machine import LocoState
from deer_me.core.types import Pose

if TYPE_CHECKING:
    import bpy
    from deer_me.api.deer import Deer


# ---------------------------------------------------------------------------
# Command representation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Command:
    """A single command scheduled at a specific frame."""

    frame: int
    action: Callable[[], bool]
    description: str = ""


# ---------------------------------------------------------------------------
# Sequence builder
# ---------------------------------------------------------------------------


class Sequence:
    """Fluent timeline builder for deer animation.

    Usage:
        seq = Sequence(deer)
        seq.at(0).walk(speed=1.0)
        seq.at(120).trot(speed=1.5)
        seq.hold(60)                    # Hold current state for 60 frames
        seq.at(240).idle()
        frames = seq.bake()             # Returns [(frame, Pose), ...]
    """

    def __init__(self, deer: Deer) -> None:
        self._deer = deer
        self._commands: List[_Command] = []
        self._cursor: int = 0  # Current frame cursor for .at()

    @property
    def deer(self) -> Deer:
        return self._deer

    @property
    def commands(self) -> List[_Command]:
        """All scheduled commands, sorted by frame."""
        return sorted(self._commands, key=lambda c: c.frame)

    @property
    def end_frame(self) -> int:
        """The last frame with a scheduled command."""
        if not self._commands:
            return 0
        return max(c.frame for c in self._commands)

    # ---------------------------------------------------------------------------
    # Cursor positioning
    # ---------------------------------------------------------------------------

    def at(self, frame: int) -> Sequence:
        """Set the cursor to a specific frame for the next command.

        Returns self for chaining.
        """
        self._cursor = frame
        return self

    def hold(self, num_frames: int) -> Sequence:
        """Advance the cursor by num_frames without changing state.

        Useful for holding a gait for a duration before the next transition.
        """
        self._cursor += num_frames
        return self

    # ---------------------------------------------------------------------------
    # Animation commands (scheduled at cursor position)
    # ---------------------------------------------------------------------------

    def walk(self, speed: float = 1.0) -> Sequence:
        """Schedule a walk transition at the current cursor frame."""
        frame = self._cursor
        self._commands.append(
            _Command(frame, lambda s=speed: self._deer.walk(s), f"walk({speed})")
        )
        return self

    def trot(self, speed: float = 1.3) -> Sequence:
        """Schedule a trot transition at the current cursor frame."""
        frame = self._cursor
        self._commands.append(
            _Command(frame, lambda s=speed: self._deer.trot(s), f"trot({speed})")
        )
        return self

    def gallop(self, speed: float = 2.0) -> Sequence:
        """Schedule a gallop transition at the current cursor frame."""
        frame = self._cursor
        self._commands.append(
            _Command(frame, lambda s=speed: self._deer.gallop(s), f"gallop({speed})")
        )
        return self

    def idle(self) -> Sequence:
        """Schedule an idle transition at the current cursor frame."""
        frame = self._cursor
        self._commands.append(
            _Command(frame, lambda: self._deer.idle(), "idle()")
        )
        return self

    def turn_left(self, speed: float = 1.0) -> Sequence:
        """Schedule a left turn at the current cursor frame."""
        frame = self._cursor
        self._commands.append(
            _Command(
                frame, lambda s=speed: self._deer.turn_left(s), f"turn_left({speed})"
            )
        )
        return self

    def turn_right(self, speed: float = 1.0) -> Sequence:
        """Schedule a right turn at the current cursor frame."""
        frame = self._cursor
        self._commands.append(
            _Command(
                frame, lambda s=speed: self._deer.turn_right(s), f"turn_right({speed})"
            )
        )
        return self

    # ---------------------------------------------------------------------------
    # Baking
    # ---------------------------------------------------------------------------

    def bake(self, extra_frames: int = 24) -> List[Tuple[int, Pose]]:
        """Execute all commands and generate the full pose sequence.

        Resets the deer, plays through the timeline frame by frame, fires
        commands at their scheduled frames, and collects poses.

        Args:
            extra_frames: Extra frames to append after the last command,
                          to let the final transition complete.

        Returns:
            List of (frame_number, Pose) pairs for the entire sequence.
        """
        self._deer.reset()
        sorted_cmds = self.commands
        total_frames = self.end_frame + extra_frames

        if total_frames <= 0:
            return []

        cmd_idx = 0
        sequence: List[Tuple[int, Pose]] = []
        dt = 1.0 / self._deer.fps

        for frame in range(1, total_frames + 1):
            # Fire any commands scheduled for this frame
            while cmd_idx < len(sorted_cmds) and sorted_cmds[cmd_idx].frame <= frame:
                sorted_cmds[cmd_idx].action()
                cmd_idx += 1

            self._deer.update(dt)
            sequence.append((frame, self._deer.pose()))

        return sequence

    def bake_to_blender(
        self,
        extra_frames: int = 24,
        setup_scene: bool = True,
        create_proxy: bool = True,
    ) -> "bpy.types.Object":
        """Bake the sequence directly into Blender.

        Args:
            extra_frames: Extra frames after last command.
            setup_scene: Create ground, lights, camera.
            create_proxy: Create proxy deer mesh.

        Returns:
            The Blender armature object.
        """
        from deer_me.adapter.keyframe import batch_insert_sequence, set_frame_range
        from deer_me.adapter.rig import create_armature
        from deer_me.adapter.scene import setup_deer_scene
        from deer_me.adapter.skin import create_proxy_mesh

        sequence = self.bake(extra_frames=extra_frames)

        if not sequence:
            raise ValueError("No frames to bake — add commands first")

        if setup_scene:
            setup_deer_scene(
                fps=int(self._deer.fps),
                frame_end=sequence[-1][0],
            )

        arm_obj = create_armature(
            self._deer.skeleton, name=f"{self._deer.name}Armature"
        )
        batch_insert_sequence(arm_obj, sequence)
        set_frame_range(1, sequence[-1][0])

        if create_proxy:
            create_proxy_mesh(arm_obj, name=f"{self._deer.name}Mesh")

        return arm_obj

    # ---------------------------------------------------------------------------
    # Inspection
    # ---------------------------------------------------------------------------

    def describe(self) -> str:
        """Return a human-readable description of the sequence timeline."""
        lines = [f"Sequence for '{self._deer.name}' ({len(self._commands)} commands):"]
        for cmd in self.commands:
            lines.append(f"  frame {cmd.frame:>4d}: {cmd.description}")
        total = self.end_frame + 24
        lines.append(f"  Total: ~{total} frames ({total / self._deer.fps:.1f}s)")
        return "\n".join(lines)
