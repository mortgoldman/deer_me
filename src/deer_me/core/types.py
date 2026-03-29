"""Core data types for the deer animation system.

All types are pure Python / numpy — no Blender dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Vector / rotation primitives
# ---------------------------------------------------------------------------

Vec3 = NDArray[np.float64]  # shape (3,)


def vec3(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Vec3:
    """Create a 3D vector."""
    return np.array([x, y, z], dtype=np.float64)


@dataclass(slots=True)
class Quaternion:
    """Unit quaternion for rotation (w, x, y, z convention)."""

    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @staticmethod
    def from_axis_angle(axis: Vec3, angle_rad: float) -> Quaternion:
        """Create quaternion from axis and angle (radians)."""
        axis = axis / (np.linalg.norm(axis) + 1e-12)
        half = angle_rad * 0.5
        s = math.sin(half)
        return Quaternion(
            w=math.cos(half),
            x=float(axis[0] * s),
            y=float(axis[1] * s),
            z=float(axis[2] * s),
        )

    @staticmethod
    def identity() -> Quaternion:
        return Quaternion(1.0, 0.0, 0.0, 0.0)

    def to_array(self) -> NDArray[np.float64]:
        return np.array([self.w, self.x, self.y, self.z], dtype=np.float64)

    def normalized(self) -> Quaternion:
        a = self.to_array()
        a /= np.linalg.norm(a) + 1e-12
        return Quaternion(float(a[0]), float(a[1]), float(a[2]), float(a[3]))

    def conjugate(self) -> Quaternion:
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def __mul__(self, other: Quaternion) -> Quaternion:
        """Hamilton product."""
        w1, x1, y1, z1 = self.w, self.x, self.y, self.z
        w2, x2, y2, z2 = other.w, other.x, other.y, other.z
        return Quaternion(
            w=w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            x=w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            y=w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            z=w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )

    def rotate_vector(self, v: Vec3) -> Vec3:
        """Rotate a 3D vector by this quaternion."""
        qv = Quaternion(0.0, float(v[0]), float(v[1]), float(v[2]))
        result = self * qv * self.conjugate()
        return vec3(result.x, result.y, result.z)


def slerp(q0: Quaternion, q1: Quaternion, t: float) -> Quaternion:
    """Spherical linear interpolation between two quaternions."""
    a = q0.to_array()
    b = q1.to_array()
    dot = float(np.dot(a, b))

    # Ensure shortest path
    if dot < 0.0:
        b = -b
        dot = -dot

    dot = min(dot, 1.0)

    if dot > 0.9995:
        # Very close — use linear interpolation to avoid division by zero
        result = a + t * (b - a)
        result /= np.linalg.norm(result)
    else:
        theta = math.acos(dot)
        sin_theta = math.sin(theta)
        result = (math.sin((1 - t) * theta) * a + math.sin(t * theta) * b) / sin_theta

    return Quaternion(
        float(result[0]), float(result[1]), float(result[2]), float(result[3])
    )


# ---------------------------------------------------------------------------
# Joint / bone types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class JointLimit:
    """Angular limits for a joint axis (radians)."""

    min_angle: float = -math.pi
    max_angle: float = math.pi

    def clamp(self, angle: float) -> float:
        return max(self.min_angle, min(self.max_angle, angle))


@dataclass(slots=True)
class BoneDef:
    """Definition of a single bone in the skeleton."""

    name: str
    parent: Optional[str]
    rest_position: Vec3 = field(default_factory=lambda: vec3())
    rest_rotation: Quaternion = field(default_factory=Quaternion.identity)
    length: float = 0.1
    limit_x: JointLimit = field(default_factory=JointLimit)
    limit_y: JointLimit = field(default_factory=JointLimit)
    limit_z: JointLimit = field(default_factory=JointLimit)


@dataclass(slots=True)
class JointTransform:
    """Runtime transform of a single joint: position + rotation."""

    position: Vec3 = field(default_factory=lambda: vec3())
    rotation: Quaternion = field(default_factory=Quaternion.identity)


# ---------------------------------------------------------------------------
# Pose: a snapshot of every joint at one moment in time
# ---------------------------------------------------------------------------


@dataclass
class Pose:
    """Complete pose of the skeleton at a single point in time.

    Maps bone name → JointTransform (local-space, relative to parent).
    Tracks which bones had positions explicitly set (vs rest defaults)
    so the adapter layer knows which bones need location keyframes.
    """

    joints: Dict[str, JointTransform] = field(default_factory=dict)
    _dirty_positions: set = field(default_factory=set)

    def get(self, bone_name: str) -> JointTransform:
        if bone_name not in self.joints:
            self.joints[bone_name] = JointTransform()
        return self.joints[bone_name]

    def set_rotation(self, bone_name: str, rotation: Quaternion) -> None:
        self.get(bone_name).rotation = rotation

    def set_position(self, bone_name: str, position: Vec3) -> None:
        self.get(bone_name).position = position.copy()
        self._dirty_positions.add(bone_name)

    def has_position_change(self, bone_name: str) -> bool:
        """True if set_position was explicitly called for this bone."""
        return bone_name in self._dirty_positions


# ---------------------------------------------------------------------------
# Gait / locomotion enums
# ---------------------------------------------------------------------------


class GaitType(Enum):
    """Locomotion gait types for a quadruped."""

    IDLE = auto()
    WALK = auto()
    TROT = auto()
    GALLOP = auto()


class LegId(Enum):
    """Identifies each leg."""

    FRONT_LEFT = auto()
    FRONT_RIGHT = auto()
    REAR_LEFT = auto()
    REAR_RIGHT = auto()


@dataclass(slots=True)
class GaitPhase:
    """Phase information for a gait cycle.

    phase: 0.0–1.0 normalized cycle position
    leg_phases: per-leg phase offsets within the cycle
    """

    phase: float = 0.0
    leg_phases: Dict[LegId, float] = field(default_factory=dict)
