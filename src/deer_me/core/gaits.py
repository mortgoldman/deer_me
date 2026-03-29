"""Parameterized quadruped gait cycle definitions.

Each gait defines:
- Per-leg phase offsets (which legs move together / alternately)
- Foot height curve over the cycle (swing vs stance)
- Stride length curve
- Body bob / pitch oscillation

All functions are pure math — no Blender dependency.

Gait reference (phase offsets as fraction of cycle):
  Walk:   FL=0.0  FR=0.5  RL=0.75  RR=0.25   (lateral sequence)
  Trot:   FL=0.0  FR=0.5  RL=0.5   RR=0.0    (diagonal pairs)
  Gallop: FL=0.0  FR=0.1  RL=0.5   RR=0.6    (gathered gallop)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict

from .types import GaitPhase, GaitType, LegId, vec3, Vec3


# ---------------------------------------------------------------------------
# Gait parameters
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class GaitParams:
    """Tunable parameters for a single gait type."""

    gait_type: GaitType

    # Per-leg phase offsets within the cycle [0, 1)
    leg_offsets: Dict[LegId, float]

    # Fraction of the cycle each foot is on the ground (0–1).
    # Higher = more time in stance (walk ≈ 0.65, trot ≈ 0.5, gallop ≈ 0.35)
    duty_factor: float = 0.6

    # Peak foot lift height during swing phase (meters)
    swing_height: float = 0.08

    # Stride length at speed=1.0 (meters per full cycle)
    stride_length: float = 0.6

    # Vertical body oscillation amplitude (meters)
    body_bob_amplitude: float = 0.01

    # Body pitch oscillation amplitude (radians)
    body_pitch_amplitude: float = 0.02

    # Cycles per second at speed=1.0
    cycle_rate: float = 1.0


# ---------------------------------------------------------------------------
# Preset gait definitions
# ---------------------------------------------------------------------------

WALK_PARAMS = GaitParams(
    gait_type=GaitType.WALK,
    leg_offsets={
        LegId.FRONT_LEFT: 0.0,
        LegId.FRONT_RIGHT: 0.5,
        LegId.REAR_LEFT: 0.75,
        LegId.REAR_RIGHT: 0.25,
    },
    duty_factor=0.65,
    swing_height=0.06,
    stride_length=0.55,
    body_bob_amplitude=0.008,
    body_pitch_amplitude=0.015,
    cycle_rate=0.9,
)

TROT_PARAMS = GaitParams(
    gait_type=GaitType.TROT,
    leg_offsets={
        LegId.FRONT_LEFT: 0.0,
        LegId.FRONT_RIGHT: 0.5,
        LegId.REAR_LEFT: 0.5,
        LegId.REAR_RIGHT: 0.0,
    },
    duty_factor=0.5,
    swing_height=0.10,
    stride_length=0.80,
    body_bob_amplitude=0.015,
    body_pitch_amplitude=0.025,
    cycle_rate=1.4,
)

GALLOP_PARAMS = GaitParams(
    gait_type=GaitType.GALLOP,
    leg_offsets={
        LegId.FRONT_LEFT: 0.0,
        LegId.FRONT_RIGHT: 0.1,
        LegId.REAR_LEFT: 0.5,
        LegId.REAR_RIGHT: 0.6,
    },
    duty_factor=0.35,
    swing_height=0.14,
    stride_length=1.40,
    body_bob_amplitude=0.025,
    body_pitch_amplitude=0.04,
    cycle_rate=2.0,
)

GAIT_PRESETS: Dict[GaitType, GaitParams] = {
    GaitType.WALK: WALK_PARAMS,
    GaitType.TROT: TROT_PARAMS,
    GaitType.GALLOP: GALLOP_PARAMS,
}


# ---------------------------------------------------------------------------
# Gait cycle evaluation
# ---------------------------------------------------------------------------


def _wrap_phase(phase: float) -> float:
    """Wrap phase into [0, 1)."""
    return phase % 1.0


def leg_phase(cycle_phase: float, leg: LegId, params: GaitParams) -> float:
    """Get the phase [0, 1) for a specific leg given the overall cycle phase."""
    return _wrap_phase(cycle_phase + params.leg_offsets[leg])


def is_stance(leg_ph: float, duty_factor: float) -> bool:
    """True if the leg is in the stance (ground contact) phase."""
    return leg_ph < duty_factor


def swing_progress(leg_ph: float, duty_factor: float) -> float:
    """Return 0–1 progress through the swing phase, or -1 if in stance."""
    if leg_ph < duty_factor:
        return -1.0
    return (leg_ph - duty_factor) / (1.0 - duty_factor)


def foot_height(leg_ph: float, params: GaitParams) -> float:
    """Compute the foot lift height at a given leg phase.

    Returns 0 during stance, a smooth arc during swing.
    Uses a sine curve for a natural-looking arc.
    """
    if is_stance(leg_ph, params.duty_factor):
        return 0.0
    t = swing_progress(leg_ph, params.duty_factor)
    return params.swing_height * math.sin(t * math.pi)


def foot_stride_offset(leg_ph: float, params: GaitParams, speed: float = 1.0) -> float:
    """Compute forward/backward offset of the foot along the stride.

    Returns a value in [-stride/2, +stride/2]:
    - During stance: foot slides backward (ground contact)
    - During swing: foot swings forward to the next plant position

    The result is scaled by speed.
    """
    half_stride = params.stride_length * speed * 0.5

    if is_stance(leg_ph, params.duty_factor):
        # Stance: linear slide from +half_stride to -half_stride
        t = leg_ph / params.duty_factor
        return half_stride * (1.0 - 2.0 * t)
    else:
        # Swing: smooth return from -half_stride to +half_stride
        t = swing_progress(leg_ph, params.duty_factor)
        # Use smoothstep for a natural acceleration/deceleration
        t_smooth = t * t * (3.0 - 2.0 * t)
        return half_stride * (-1.0 + 2.0 * t_smooth)


def body_bob(cycle_phase: float, params: GaitParams) -> float:
    """Vertical body oscillation at a given cycle phase.

    Walk/trot: two bobs per cycle (peak when diagonal pair in mid-stance).
    Gallop: one larger bob per cycle.
    """
    if params.gait_type == GaitType.GALLOP:
        return params.body_bob_amplitude * math.sin(cycle_phase * 2.0 * math.pi)
    return params.body_bob_amplitude * math.sin(cycle_phase * 4.0 * math.pi)


def body_pitch(cycle_phase: float, params: GaitParams) -> float:
    """Body pitch oscillation in radians (positive = nose down)."""
    if params.gait_type == GaitType.GALLOP:
        return params.body_pitch_amplitude * math.sin(cycle_phase * 2.0 * math.pi)
    return params.body_pitch_amplitude * math.sin(
        cycle_phase * 4.0 * math.pi + math.pi * 0.25
    )


# ---------------------------------------------------------------------------
# High-level: compute full foot target for one leg
# ---------------------------------------------------------------------------


def compute_foot_target(
    cycle_phase: float,
    leg: LegId,
    params: GaitParams,
    rest_foot_pos: Vec3,
    speed: float = 1.0,
    forward_axis: int = 1,
) -> Vec3:
    """Compute the world-space target position for one foot.

    Args:
        cycle_phase: overall gait cycle position [0, 1)
        leg: which leg
        params: gait parameters
        rest_foot_pos: the foot's rest position (standing neutral)
        speed: locomotion speed multiplier
        forward_axis: which axis is forward (default 1 = +Y)

    Returns:
        Target foot position with stride offset and lift applied.
    """
    lp = leg_phase(cycle_phase, leg, params)
    target = rest_foot_pos.copy()

    # Forward/backward stride offset
    target[forward_axis] += foot_stride_offset(lp, params, speed)

    # Vertical lift (always Z-up)
    target[2] += foot_height(lp, params)

    return target
