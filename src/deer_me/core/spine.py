"""Procedural spine and neck dynamics for the deer rig.

Computes secondary motion on the spine/neck chain based on locomotion state:
- Spine undulation that follows the gait rhythm
- Neck follow-through with dampened head stabilization
- Tail sway as a trailing oscillation

All functions are pure math — no Blender dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

import numpy as np

from .types import Quaternion, Vec3, vec3


@dataclass(slots=True)
class SpineParams:
    """Tunable parameters for spine dynamics."""

    # Lateral sway amplitude per spine bone (radians)
    lateral_sway: float = 0.03

    # Vertical undulation amplitude per spine bone (radians)
    vertical_undulation: float = 0.02

    # Phase delay between successive spine bones (fraction of cycle)
    bone_phase_delay: float = 0.08

    # How much the spine compresses/extends with speed (radians)
    compression_factor: float = 0.01


@dataclass(slots=True)
class NeckParams:
    """Tunable parameters for neck/head dynamics."""

    # How much the neck compensates for body pitch (0 = none, 1 = full)
    pitch_compensation: float = 0.7

    # Lateral follow-through from body sway (multiplier)
    lateral_follow: float = 0.5

    # Head stabilization factor (0 = no stabilization, 1 = perfectly stable)
    head_stabilization: float = 0.6

    # Head bob amplitude (radians) — small nod with each step
    head_bob_amplitude: float = 0.02

    # Head bob frequency multiplier relative to gait cycle
    head_bob_freq: float = 2.0


@dataclass(slots=True)
class TailParams:
    """Tunable parameters for tail dynamics."""

    # Lateral sway amplitude (radians)
    lateral_sway: float = 0.08

    # Vertical sway amplitude (radians)
    vertical_sway: float = 0.04

    # Phase lag behind the spine (fraction of cycle)
    phase_lag: float = 0.15

    # Phase delay between tail_base and tail_tip
    tip_delay: float = 0.1


# ---------------------------------------------------------------------------
# Spine chain computation
# ---------------------------------------------------------------------------


def compute_spine_rotations(
    cycle_phase: float,
    speed: float,
    num_bones: int = 3,
    params: SpineParams | None = None,
) -> List[Quaternion]:
    """Compute local rotations for each spine bone.

    The spine undulates laterally and vertically with the gait cycle,
    with a wave traveling from rear to front.

    Args:
        cycle_phase: overall gait phase [0, 1)
        speed: locomotion speed (0 = idle, higher = more motion)
        num_bones: number of spine bones in the chain
        params: tuning parameters

    Returns:
        List of Quaternion rotations, one per spine bone (base to upper).
    """
    if params is None:
        params = SpineParams()

    rotations: List[Quaternion] = []
    speed_factor = min(speed, 2.0)

    for i in range(num_bones):
        bone_phase = cycle_phase - i * params.bone_phase_delay
        angle_2pi = bone_phase * 2.0 * math.pi

        # Lateral sway (rotation around forward axis Y)
        lateral = (
            params.lateral_sway
            * speed_factor
            * math.sin(angle_2pi * 2.0)
        )

        # Vertical undulation (rotation around lateral axis X)
        vertical = (
            params.vertical_undulation
            * speed_factor
            * math.sin(angle_2pi * 2.0 + math.pi * 0.5)
        )

        # Speed-dependent compression on the rear bones
        compression = params.compression_factor * speed_factor * (num_bones - 1 - i) / max(num_bones - 1, 1)

        q_lateral = Quaternion.from_axis_angle(vec3(0, 1, 0), lateral)
        q_vertical = Quaternion.from_axis_angle(vec3(1, 0, 0), vertical + compression)
        rotations.append(q_lateral * q_vertical)

    return rotations


# ---------------------------------------------------------------------------
# Neck / head computation
# ---------------------------------------------------------------------------


def compute_neck_rotations(
    cycle_phase: float,
    speed: float,
    body_pitch: float = 0.0,
    body_lateral: float = 0.0,
    num_bones: int = 3,
    params: NeckParams | None = None,
) -> List[Quaternion]:
    """Compute local rotations for neck chain (neck_base, neck_mid, head).

    The neck partially compensates for body pitch to keep the head stable,
    and adds subtle secondary motion (bob, follow-through).

    Args:
        cycle_phase: gait phase [0, 1)
        speed: locomotion speed
        body_pitch: current body pitch angle (radians, from gait)
        body_lateral: current body lateral sway (radians, from spine)
        num_bones: number of neck+head bones
        params: tuning parameters

    Returns:
        List of Quaternion rotations for [neck_base, neck_mid, head].
    """
    if params is None:
        params = NeckParams()

    rotations: List[Quaternion] = []
    speed_factor = min(speed, 2.0)

    for i in range(num_bones):
        is_head = (i == num_bones - 1)

        # Pitch compensation — distribute across neck bones
        # Head gets the most compensation
        if is_head:
            comp_weight = params.head_stabilization
        else:
            comp_weight = params.pitch_compensation * (i + 1) / num_bones

        pitch_comp = -body_pitch * comp_weight

        # Lateral follow-through (opposite to body sway for balance)
        lateral_comp = -body_lateral * params.lateral_follow * (i + 1) / num_bones

        # Head bob — small rhythmic nod
        bob = 0.0
        if speed_factor > 0.1:
            bob_phase = cycle_phase * params.head_bob_freq * 2.0 * math.pi
            bob = params.head_bob_amplitude * speed_factor * math.sin(bob_phase)
            if is_head:
                bob *= 0.5  # Less bob on head itself (stabilized)

        q_pitch = Quaternion.from_axis_angle(vec3(1, 0, 0), pitch_comp + bob)
        q_lateral = Quaternion.from_axis_angle(vec3(0, 1, 0), lateral_comp)
        rotations.append(q_pitch * q_lateral)

    return rotations


# ---------------------------------------------------------------------------
# Tail computation
# ---------------------------------------------------------------------------


def compute_tail_rotations(
    cycle_phase: float,
    speed: float,
    num_bones: int = 2,
    params: TailParams | None = None,
) -> List[Quaternion]:
    """Compute local rotations for tail bones.

    The tail sways as a trailing wave behind the spine motion.

    Args:
        cycle_phase: gait phase [0, 1)
        speed: locomotion speed
        num_bones: number of tail bones
        params: tuning parameters

    Returns:
        List of Quaternion rotations for [tail_base, tail_tip].
    """
    if params is None:
        params = TailParams()

    rotations: List[Quaternion] = []
    speed_factor = min(speed, 2.0)

    for i in range(num_bones):
        bone_phase = cycle_phase - params.phase_lag - i * params.tip_delay
        angle_2pi = bone_phase * 2.0 * math.pi

        # Lateral sway — larger amplitude, increasing toward tip
        amp_scale = 1.0 + 0.5 * i  # tip sways more
        lateral = (
            params.lateral_sway
            * speed_factor
            * amp_scale
            * math.sin(angle_2pi * 2.0)
        )

        # Vertical sway
        vertical = (
            params.vertical_sway
            * speed_factor
            * math.sin(angle_2pi * 2.0 + math.pi * 0.3)
        )

        q_lateral = Quaternion.from_axis_angle(vec3(0, 0, 1), lateral)
        q_vertical = Quaternion.from_axis_angle(vec3(1, 0, 0), vertical)
        rotations.append(q_lateral * q_vertical)

    return rotations
