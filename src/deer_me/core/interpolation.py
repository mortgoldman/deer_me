"""Interpolation and easing utilities for animation blending.

Pure math — no Blender dependency.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np

from .types import JointTransform, Pose, Quaternion, Vec3, slerp, vec3


# ---------------------------------------------------------------------------
# Easing functions:  f(t) -> t'   where t in [0, 1]
# ---------------------------------------------------------------------------

EasingFn = Callable[[float], float]


def linear(t: float) -> float:
    return t


def ease_in_quad(t: float) -> float:
    return t * t


def ease_out_quad(t: float) -> float:
    return t * (2.0 - t)


def ease_in_out_quad(t: float) -> float:
    if t < 0.5:
        return 2.0 * t * t
    return -1.0 + (4.0 - 2.0 * t) * t


def ease_in_cubic(t: float) -> float:
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t1 = t - 1.0
    return t1 * t1 * t1 + 1.0


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4.0 * t * t * t
    return (t - 1.0) * (2.0 * t - 2.0) * (2.0 * t - 2.0) + 1.0


def ease_in_sine(t: float) -> float:
    return 1.0 - math.cos(t * math.pi / 2.0)


def ease_out_sine(t: float) -> float:
    return math.sin(t * math.pi / 2.0)


def ease_in_out_sine(t: float) -> float:
    return 0.5 * (1.0 - math.cos(math.pi * t))


def smoothstep(t: float) -> float:
    """Hermite smoothstep — zero first derivative at endpoints."""
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Vector / transform interpolation
# ---------------------------------------------------------------------------


def lerp_vec3(a: Vec3, b: Vec3, t: float) -> Vec3:
    """Linear interpolation between two Vec3."""
    return a + t * (b - a)


def lerp_float(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def blend_joint(a: JointTransform, b: JointTransform, t: float) -> JointTransform:
    """Blend two joint transforms using lerp (position) and slerp (rotation)."""
    return JointTransform(
        position=lerp_vec3(a.position, b.position, t),
        rotation=slerp(a.rotation, b.rotation, t),
    )


def blend_pose(pose_a: Pose, pose_b: Pose, t: float,
               easing: EasingFn = linear) -> Pose:
    """Blend two poses. Every joint in pose_b is blended with pose_a.

    Joints present in only one pose are taken as-is at the appropriate extreme.
    """
    t_eased = easing(max(0.0, min(1.0, t)))
    result = Pose()

    all_keys = set(pose_a.joints) | set(pose_b.joints)
    for name in all_keys:
        ja = pose_a.joints.get(name, JointTransform())
        jb = pose_b.joints.get(name, JointTransform())
        result.joints[name] = blend_joint(ja, jb, t_eased)

    # Propagate dirty positions from either source
    result._dirty_positions = pose_a._dirty_positions | pose_b._dirty_positions

    return result


# ---------------------------------------------------------------------------
# Cubic Hermite spline (for smooth gait curves)
# ---------------------------------------------------------------------------


def cubic_hermite(p0: float, m0: float, p1: float, m1: float, t: float) -> float:
    """Evaluate a cubic Hermite spline segment at parameter t in [0, 1].

    p0, p1: endpoint values
    m0, m1: endpoint tangents
    """
    t2 = t * t
    t3 = t2 * t
    h00 = 2.0 * t3 - 3.0 * t2 + 1.0
    h10 = t3 - 2.0 * t2 + t
    h01 = -2.0 * t3 + 3.0 * t2
    h11 = t3 - t2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1


def catmull_rom(points: list[float], t: float) -> float:
    """Evaluate a Catmull-Rom spline through a list of equally-spaced points.

    t ranges from 0.0 (first point) to 1.0 (last point).
    The spline passes through every point.
    """
    n = len(points)
    if n < 2:
        return points[0] if points else 0.0

    # Map t to segment
    t_scaled = t * (n - 1)
    seg = int(t_scaled)
    seg = max(0, min(seg, n - 2))
    local_t = t_scaled - seg

    # Neighboring points with clamped indices
    def _p(i: int) -> float:
        return points[max(0, min(i, n - 1))]

    p0 = _p(seg - 1)
    p1 = _p(seg)
    p2 = _p(seg + 1)
    p3 = _p(seg + 2)

    # Catmull-Rom tangents
    m1 = 0.5 * (p2 - p0)
    m2 = 0.5 * (p3 - p1)

    return cubic_hermite(p1, m1, p2, m2, local_t)
