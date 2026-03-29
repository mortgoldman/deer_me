"""Pre-built motion presets — compound behaviors for common deer actions.

Each preset takes a Sequence and appends a series of commands to it.
This makes it easy to build complex animations from reusable building blocks:

    seq = Sequence(deer)
    seq.at(0)
    presets.graze(seq, duration_frames=120)
    presets.startle(seq)
    presets.flee(seq, duration_frames=96)
    frames = seq.bake()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deer_me.api.sequence import Sequence


def graze(seq: Sequence, duration_frames: int = 120) -> Sequence:
    """Deer walks slowly then stops to graze.

    Pattern: walk(slow) → idle
    The idle portion simulates grazing with the deer's head-down breathing cycle.

    Args:
        seq: The sequence to append to.
        duration_frames: Total duration of the graze behavior.

    Returns:
        The sequence (for chaining).
    """
    walk_frames = min(duration_frames // 3, 48)
    seq.walk(speed=0.4)
    seq.hold(walk_frames).idle()
    seq.hold(duration_frames - walk_frames)
    return seq


def startle(seq: Sequence, pause_frames: int = 18) -> Sequence:
    """Deer freezes briefly (alert reaction).

    Pattern: idle (brief freeze with ears perked).
    The idle animation's ear flicks sell the alert look.

    Args:
        seq: The sequence to append to.
        pause_frames: How long the freeze lasts.

    Returns:
        The sequence (for chaining).
    """
    seq.idle()
    seq.hold(pause_frames)
    return seq


def flee(seq: Sequence, duration_frames: int = 96) -> Sequence:
    """Deer bolts away — walk → trot → gallop.

    Pattern: rapid acceleration through all gaits.

    Args:
        seq: The sequence to append to.
        duration_frames: Total duration of the flee.

    Returns:
        The sequence (for chaining).
    """
    # Quick walk to get moving
    seq.walk(speed=1.5)
    ramp = duration_frames // 4
    seq.hold(ramp).trot(speed=1.8)
    seq.hold(ramp).gallop(speed=2.5)
    seq.hold(duration_frames - 2 * ramp)
    return seq


def look_around(seq: Sequence, duration_frames: int = 96) -> Sequence:
    """Deer looks left, then right, then forward.

    Pattern: turn_left → turn_right → idle.

    Args:
        seq: The sequence to append to.
        duration_frames: Total duration.

    Returns:
        The sequence (for chaining).
    """
    segment = duration_frames // 3
    seq.turn_left(speed=0.3)
    seq.hold(segment).turn_right(speed=0.3)
    seq.hold(segment).idle()
    seq.hold(segment)
    return seq


def patrol(seq: Sequence, duration_frames: int = 240) -> Sequence:
    """Deer walks, pauses to look around, then continues.

    Pattern: walk → idle → look_around → walk.

    Args:
        seq: The sequence to append to.
        duration_frames: Total duration.

    Returns:
        The sequence (for chaining).
    """
    segment = duration_frames // 4
    seq.walk(speed=0.8)
    seq.hold(segment).idle()
    seq.hold(segment // 2)
    look_around(seq, duration_frames=segment)
    seq.walk(speed=0.8)
    seq.hold(segment)
    return seq


def approach_and_graze(seq: Sequence, duration_frames: int = 240) -> Sequence:
    """Deer walks forward cautiously, looks around, then grazes.

    Pattern: slow walk → look_around → graze.

    Args:
        seq: The sequence to append to.
        duration_frames: Total duration.

    Returns:
        The sequence (for chaining).
    """
    walk_segment = duration_frames // 4
    look_segment = duration_frames // 4
    graze_segment = duration_frames // 2

    seq.walk(speed=0.5)
    seq.hold(walk_segment)
    look_around(seq, duration_frames=look_segment)
    graze(seq, duration_frames=graze_segment)
    return seq
