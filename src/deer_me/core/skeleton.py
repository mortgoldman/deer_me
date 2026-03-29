"""Deer skeleton definition — 27-bone quadruped rig.

All measurements are in Blender units (~meters). A white-tailed deer is
roughly 1.0m at the shoulder and 1.5m nose-to-tail, which gives us our
reference scale.

Bone hierarchy (simplified):

    root
    └── spine_base
        ├── spine_mid
        │   └── spine_upper
        │       ├── neck_base
        │       │   └── neck_mid
        │       │       └── head
        │       │           ├── ear_l
        │       │           └── ear_r
        │       ├── shoulder_l → upper_arm_l → lower_arm_l → front_hoof_l
        │       └── shoulder_r → upper_arm_r → lower_arm_r → front_hoof_r
        ├── tail_base
        │   └── tail_tip
        ├── hip_l → upper_leg_l → lower_leg_l → rear_hoof_l
        └── hip_r → upper_leg_r → lower_leg_r → rear_hoof_r
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .types import BoneDef, JointLimit, JointTransform, Pose, Quaternion, vec3


# ---------------------------------------------------------------------------
# Bone name constants
# ---------------------------------------------------------------------------

ROOT = "root"

SPINE_BASE = "spine_base"
SPINE_MID = "spine_mid"
SPINE_UPPER = "spine_upper"

NECK_BASE = "neck_base"
NECK_MID = "neck_mid"
HEAD = "head"
EAR_L = "ear_l"
EAR_R = "ear_r"

SHOULDER_L = "shoulder_l"
UPPER_ARM_L = "upper_arm_l"
LOWER_ARM_L = "lower_arm_l"
FRONT_HOOF_L = "front_hoof_l"

SHOULDER_R = "shoulder_r"
UPPER_ARM_R = "upper_arm_r"
LOWER_ARM_R = "lower_arm_r"
FRONT_HOOF_R = "front_hoof_r"

HIP_L = "hip_l"
UPPER_LEG_L = "upper_leg_l"
LOWER_LEG_L = "lower_leg_l"
REAR_HOOF_L = "rear_hoof_l"

HIP_R = "hip_r"
UPPER_LEG_R = "upper_leg_r"
LOWER_LEG_R = "lower_leg_r"
REAR_HOOF_R = "rear_hoof_r"

TAIL_BASE = "tail_base"
TAIL_TIP = "tail_tip"

ALL_BONE_NAMES: List[str] = [
    ROOT,
    SPINE_BASE, SPINE_MID, SPINE_UPPER,
    NECK_BASE, NECK_MID, HEAD, EAR_L, EAR_R,
    SHOULDER_L, UPPER_ARM_L, LOWER_ARM_L, FRONT_HOOF_L,
    SHOULDER_R, UPPER_ARM_R, LOWER_ARM_R, FRONT_HOOF_R,
    HIP_L, UPPER_LEG_L, LOWER_LEG_L, REAR_HOOF_L,
    HIP_R, UPPER_LEG_R, LOWER_LEG_R, REAR_HOOF_R,
    TAIL_BASE, TAIL_TIP,
]

# Convenience groups for the API layer
FRONT_LEG_L = [SHOULDER_L, UPPER_ARM_L, LOWER_ARM_L, FRONT_HOOF_L]
FRONT_LEG_R = [SHOULDER_R, UPPER_ARM_R, LOWER_ARM_R, FRONT_HOOF_R]
REAR_LEG_L = [HIP_L, UPPER_LEG_L, LOWER_LEG_L, REAR_HOOF_L]
REAR_LEG_R = [HIP_R, UPPER_LEG_R, LOWER_LEG_R, REAR_HOOF_R]
SPINE_CHAIN = [SPINE_BASE, SPINE_MID, SPINE_UPPER]
NECK_CHAIN = [NECK_BASE, NECK_MID, HEAD]


# ---------------------------------------------------------------------------
# Skeleton definition
# ---------------------------------------------------------------------------


def _leg_limit() -> JointLimit:
    """Typical leg-joint swing range."""
    return JointLimit(-math.radians(60), math.radians(60))


def _knee_limit() -> JointLimit:
    """Knee/hock — bends backward only."""
    return JointLimit(-math.radians(5), math.radians(120))


def _spine_limit() -> JointLimit:
    return JointLimit(-math.radians(15), math.radians(15))


def _neck_limit() -> JointLimit:
    return JointLimit(-math.radians(40), math.radians(40))


def build_bone_defs() -> Dict[str, BoneDef]:
    """Return the complete deer skeleton as a dict of BoneDef keyed by name.

    Coordinate convention (Blender default):
        +X = right,  +Y = forward,  +Z = up
    """
    bones: List[BoneDef] = [
        # -- Root (world-space anchor) --
        BoneDef(ROOT, parent=None,
                rest_position=vec3(0, 0, 0), length=0.0),

        # -- Spine --
        BoneDef(SPINE_BASE, parent=ROOT,
                rest_position=vec3(0, -0.35, 0.95), length=0.30,
                limit_x=_spine_limit(), limit_z=_spine_limit()),
        BoneDef(SPINE_MID, parent=SPINE_BASE,
                rest_position=vec3(0, 0.30, 0.02), length=0.30,
                limit_x=_spine_limit(), limit_z=_spine_limit()),
        BoneDef(SPINE_UPPER, parent=SPINE_MID,
                rest_position=vec3(0, 0.30, 0.03), length=0.25,
                limit_x=_spine_limit(), limit_z=_spine_limit()),

        # -- Neck & head --
        BoneDef(NECK_BASE, parent=SPINE_UPPER,
                rest_position=vec3(0, 0.12, 0.10), length=0.18,
                limit_x=_neck_limit(), limit_y=_neck_limit()),
        BoneDef(NECK_MID, parent=NECK_BASE,
                rest_position=vec3(0, 0.08, 0.15), length=0.18,
                limit_x=_neck_limit(), limit_y=_neck_limit()),
        BoneDef(HEAD, parent=NECK_MID,
                rest_position=vec3(0, 0.06, 0.14), length=0.22,
                limit_x=_neck_limit(), limit_y=_neck_limit()),
        BoneDef(EAR_L, parent=HEAD,
                rest_position=vec3(-0.06, -0.02, 0.10), length=0.08),
        BoneDef(EAR_R, parent=HEAD,
                rest_position=vec3(0.06, -0.02, 0.10), length=0.08),

        # -- Front left leg --
        BoneDef(SHOULDER_L, parent=SPINE_UPPER,
                rest_position=vec3(-0.12, 0.05, -0.08), length=0.08,
                limit_x=_leg_limit()),
        BoneDef(UPPER_ARM_L, parent=SHOULDER_L,
                rest_position=vec3(0, 0.02, -0.08), length=0.30,
                limit_x=_leg_limit()),
        BoneDef(LOWER_ARM_L, parent=UPPER_ARM_L,
                rest_position=vec3(0, -0.01, -0.30), length=0.28,
                limit_x=_knee_limit()),
        BoneDef(FRONT_HOOF_L, parent=LOWER_ARM_L,
                rest_position=vec3(0, 0, -0.28), length=0.06),

        # -- Front right leg --
        BoneDef(SHOULDER_R, parent=SPINE_UPPER,
                rest_position=vec3(0.12, 0.05, -0.08), length=0.08,
                limit_x=_leg_limit()),
        BoneDef(UPPER_ARM_R, parent=SHOULDER_R,
                rest_position=vec3(0, 0.02, -0.08), length=0.30,
                limit_x=_leg_limit()),
        BoneDef(LOWER_ARM_R, parent=UPPER_ARM_R,
                rest_position=vec3(0, -0.01, -0.30), length=0.28,
                limit_x=_knee_limit()),
        BoneDef(FRONT_HOOF_R, parent=LOWER_ARM_R,
                rest_position=vec3(0, 0, -0.28), length=0.06),

        # -- Rear left leg --
        BoneDef(HIP_L, parent=SPINE_BASE,
                rest_position=vec3(-0.12, -0.05, -0.05), length=0.10,
                limit_x=_leg_limit()),
        BoneDef(UPPER_LEG_L, parent=HIP_L,
                rest_position=vec3(0, -0.02, -0.10), length=0.32,
                limit_x=_leg_limit()),
        BoneDef(LOWER_LEG_L, parent=UPPER_LEG_L,
                rest_position=vec3(0, 0.02, -0.32), length=0.30,
                limit_x=_knee_limit()),
        BoneDef(REAR_HOOF_L, parent=LOWER_LEG_L,
                rest_position=vec3(0, 0, -0.30), length=0.06),

        # -- Rear right leg --
        BoneDef(HIP_R, parent=SPINE_BASE,
                rest_position=vec3(0.12, -0.05, -0.05), length=0.10,
                limit_x=_leg_limit()),
        BoneDef(UPPER_LEG_R, parent=HIP_R,
                rest_position=vec3(0, -0.02, -0.10), length=0.32,
                limit_x=_leg_limit()),
        BoneDef(LOWER_LEG_R, parent=UPPER_LEG_R,
                rest_position=vec3(0, 0.02, -0.32), length=0.30,
                limit_x=_knee_limit()),
        BoneDef(REAR_HOOF_R, parent=LOWER_LEG_R,
                rest_position=vec3(0, 0, -0.30), length=0.06),

        # -- Tail --
        BoneDef(TAIL_BASE, parent=SPINE_BASE,
                rest_position=vec3(0, -0.15, 0.05), length=0.10,
                limit_x=JointLimit(-math.radians(30), math.radians(45))),
        BoneDef(TAIL_TIP, parent=TAIL_BASE,
                rest_position=vec3(0, -0.10, 0.02), length=0.08),
    ]

    return {b.name: b for b in bones}


# ---------------------------------------------------------------------------
# Skeleton class
# ---------------------------------------------------------------------------


@dataclass
class Skeleton:
    """Immutable skeleton definition + helpers for creating poses."""

    bones: Dict[str, BoneDef] = field(default_factory=build_bone_defs)

    def __post_init__(self) -> None:
        self._children: Dict[str, List[str]] = {name: [] for name in self.bones}
        for name, bone in self.bones.items():
            if bone.parent is not None:
                self._children[bone.parent].append(name)

    @property
    def bone_names(self) -> List[str]:
        return list(self.bones.keys())

    def children(self, bone_name: str) -> List[str]:
        return self._children[bone_name]

    def parent(self, bone_name: str) -> Optional[str]:
        return self.bones[bone_name].parent

    def chain(self, from_bone: str, to_bone: str) -> List[str]:
        """Return the bone chain from `from_bone` down to `to_bone` (inclusive)."""
        path: List[str] = []
        current: Optional[str] = to_bone
        while current is not None:
            path.append(current)
            if current == from_bone:
                path.reverse()
                return path
            current = self.bones[current].parent
        raise ValueError(f"No chain from {from_bone} to {to_bone}")

    def world_position(self, bone_name: str) -> "Vec3":
        """Compute the world-space position of a bone by accumulating parent offsets."""
        chain = []
        current: Optional[str] = bone_name
        while current is not None:
            chain.append(current)
            current = self.bones[current].parent
        chain.reverse()

        pos = vec3(0.0, 0.0, 0.0)
        for name in chain:
            pos = pos + self.bones[name].rest_position
        return pos

    def rest_pose(self) -> Pose:
        """Return the rest/bind pose (all joints at their default transforms)."""
        pose = Pose()
        for name, bone in self.bones.items():
            pose.joints[name] = JointTransform(
                position=bone.rest_position.copy(),
                rotation=Quaternion(
                    bone.rest_rotation.w,
                    bone.rest_rotation.x,
                    bone.rest_rotation.y,
                    bone.rest_rotation.z,
                ),
            )
        return pose
