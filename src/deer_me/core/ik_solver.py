"""Two-bone IK solver for quadruped legs.

Solves the classic two-bone (upper + lower leg) inverse kinematics problem:
given a target foot position, compute the joint angles for the upper and
lower segments so the end effector reaches the target.

Pure math — no Blender dependency.

Coordinate convention:
    The solver works in the plane defined by the shoulder/hip, the knee
    direction hint, and the target. It outputs rotation angles that the
    caller applies to the skeleton bones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .types import Quaternion, Vec3, vec3


@dataclass(slots=True)
class IKResult:
    """Result of a two-bone IK solve."""

    # Rotation for the upper bone (shoulder/hip joint)
    upper_rotation: Quaternion

    # Rotation for the lower bone (knee/hock joint)
    lower_rotation: Quaternion

    # Whether the target was reachable
    reached: bool

    # Actual end-effector position achieved
    end_position: Vec3


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def solve_two_bone(
    root_pos: Vec3,
    target_pos: Vec3,
    upper_length: float,
    lower_length: float,
    pole_target: Vec3 | None = None,
    bend_axis: Vec3 | None = None,
) -> IKResult:
    """Solve two-bone IK from root_pos to target_pos.

    Args:
        root_pos: Position of the upper joint (shoulder/hip) in world space.
        target_pos: Desired end-effector (hoof) position in world space.
        upper_length: Length of the upper bone segment.
        lower_length: Length of the lower bone segment.
        pole_target: Optional point that the knee/hock should aim toward,
                     used to resolve the bend plane.
        bend_axis: Fallback bend axis if pole_target is not given.
                   Defaults to +X (knees bend in the XZ plane).

    Returns:
        IKResult with the computed rotations and reachability info.
    """
    if bend_axis is None:
        bend_axis = vec3(1.0, 0.0, 0.0)

    to_target = target_pos - root_pos
    dist = float(np.linalg.norm(to_target))

    max_reach = upper_length + lower_length
    min_reach = abs(upper_length - lower_length)

    # Clamp distance to reachable range
    reached = True
    if dist > max_reach - 1e-6:
        dist = max_reach - 1e-6
        reached = False
    elif dist < min_reach + 1e-6:
        dist = min_reach + 1e-6
        reached = False

    # --- Solve triangle: upper_length, lower_length, dist ---
    # Angle at the upper joint (shoulder/hip)
    cos_upper = _clamp(
        (upper_length * upper_length + dist * dist - lower_length * lower_length)
        / (2.0 * upper_length * dist + 1e-12),
        -1.0,
        1.0,
    )
    angle_upper = math.acos(cos_upper)

    # Angle at the lower joint (knee/hock) — interior angle
    cos_lower = _clamp(
        (upper_length * upper_length + lower_length * lower_length - dist * dist)
        / (2.0 * upper_length * lower_length + 1e-12),
        -1.0,
        1.0,
    )
    angle_lower = math.pi - math.acos(cos_lower)

    # --- Determine the bend plane ---
    # Direction from root to target (normalized)
    if dist > 1e-12:
        dir_to_target = to_target / dist
    else:
        dir_to_target = vec3(0.0, 0.0, -1.0)

    # Compute the bend plane normal
    if pole_target is not None:
        # Use pole target to define the plane
        to_pole = pole_target - root_pos
        # Project pole direction onto the plane perpendicular to dir_to_target
        pole_on_plane = to_pole - np.dot(to_pole, dir_to_target) * dir_to_target
        pole_norm = float(np.linalg.norm(pole_on_plane))
        if pole_norm > 1e-6:
            bend_dir = pole_on_plane / pole_norm
        else:
            bend_dir = _perpendicular(dir_to_target, bend_axis)
    else:
        bend_dir = _perpendicular(dir_to_target, bend_axis)

    # Plane normal = cross(dir_to_target, bend_dir)
    plane_normal = np.cross(dir_to_target, bend_dir)
    pn_norm = float(np.linalg.norm(plane_normal))
    if pn_norm > 1e-12:
        plane_normal = plane_normal / pn_norm
    else:
        plane_normal = vec3(1.0, 0.0, 0.0)

    # --- Build rotations ---
    # Upper joint: rotate from rest direction (down, -Z) toward target,
    # then offset by the triangle angle
    rest_dir = vec3(0.0, 0.0, -1.0)

    # Rotation to aim at the target
    aim_rotation = _rotation_between(rest_dir, dir_to_target)

    # Additional rotation in the bend plane for the triangle angle
    upper_offset = Quaternion.from_axis_angle(plane_normal, -angle_upper)
    upper_rotation = upper_offset * aim_rotation

    # Lower joint: bend by the knee angle around the plane normal
    lower_rotation = Quaternion.from_axis_angle(plane_normal, angle_lower)

    # Compute actual end position for verification
    mid_dir = upper_rotation.rotate_vector(vec3(0, 0, -upper_length))
    mid_pos = root_pos + mid_dir

    # Lower bone direction in world space
    combined = lower_rotation * upper_rotation
    end_dir = combined.rotate_vector(vec3(0, 0, -lower_length))
    end_pos = mid_pos + end_dir

    return IKResult(
        upper_rotation=upper_rotation,
        lower_rotation=lower_rotation,
        reached=reached,
        end_position=end_pos,
    )


def _perpendicular(direction: Vec3, hint: Vec3) -> Vec3:
    """Find a vector perpendicular to `direction`, biased toward `hint`."""
    perp = hint - np.dot(hint, direction) * direction
    norm = float(np.linalg.norm(perp))
    if norm > 1e-6:
        return perp / norm
    # hint is parallel to direction — pick an arbitrary perpendicular
    if abs(direction[0]) < 0.9:
        alt = vec3(1, 0, 0)
    else:
        alt = vec3(0, 1, 0)
    perp = alt - np.dot(alt, direction) * direction
    return perp / (float(np.linalg.norm(perp)) + 1e-12)


def _rotation_between(from_vec: Vec3, to_vec: Vec3) -> Quaternion:
    """Compute the shortest-arc quaternion rotation from one direction to another."""
    fn = from_vec / (float(np.linalg.norm(from_vec)) + 1e-12)
    tn = to_vec / (float(np.linalg.norm(to_vec)) + 1e-12)

    dot = float(np.dot(fn, tn))

    if dot > 0.99999:
        return Quaternion.identity()

    if dot < -0.99999:
        # Vectors are opposite — rotate 180 degrees around any perpendicular axis
        if abs(fn[0]) < 0.9:
            perp = np.cross(fn, vec3(1, 0, 0))
        else:
            perp = np.cross(fn, vec3(0, 1, 0))
        perp = perp / (float(np.linalg.norm(perp)) + 1e-12)
        return Quaternion.from_axis_angle(perp, math.pi)

    axis = np.cross(fn, tn)
    axis = axis / (float(np.linalg.norm(axis)) + 1e-12)
    angle = math.acos(_clamp(dot, -1.0, 1.0))
    return Quaternion.from_axis_angle(axis, angle)
