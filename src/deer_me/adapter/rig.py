"""Blender armature adapter — maps the deer Skeleton to a Blender armature.

All bpy access is lazy-imported so this module can be imported and linted
without Blender installed. Functions will raise ImportError at call time
if bpy is unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from deer_me.core.skeleton import Skeleton
from deer_me.core.types import Pose, Quaternion

if TYPE_CHECKING:
    import bpy


def _bpy():
    """Lazy import of bpy."""
    import bpy as _bpy

    return _bpy


def _mathutils():
    """Lazy import of mathutils (ships with Blender)."""
    import mathutils as _mu

    return _mu


# ---------------------------------------------------------------------------
# Armature creation
# ---------------------------------------------------------------------------


def create_armature(
    skeleton: Skeleton,
    name: str = "DeerArmature",
    collection: Optional[str] = None,
) -> "bpy.types.Object":
    """Create a Blender armature object from a Skeleton definition.

    Args:
        skeleton: The deer skeleton definition.
        name: Name for the armature object and data block.
        collection: Optional collection name to link the object to.
                    If None, links to the active scene collection.

    Returns:
        The created Blender armature object.
    """
    bpy = _bpy()
    mu = _mathutils()

    # Create armature data block
    arm_data = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm_data)

    # Link to collection
    if collection and collection in bpy.data.collections:
        bpy.data.collections[collection].objects.link(arm_obj)
    else:
        bpy.context.scene.collection.objects.link(arm_obj)

    # Enter edit mode to add bones
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = arm_data.edit_bones

    for bone_name in skeleton.bone_names:
        bone_def = skeleton.bones[bone_name]
        eb = edit_bones.new(bone_name)

        # Position: head is the bone's rest position relative to parent
        pos = bone_def.rest_position
        eb.head = mu.Vector((float(pos[0]), float(pos[1]), float(pos[2])))

        # Tail extends along the bone's length (default direction: +Y in bone local)
        # For a quadruped, legs extend downward (-Z) and spine extends forward (+Y)
        if bone_def.length > 0:
            tail_offset = _bone_tail_direction(bone_name, bone_def.length)
            eb.tail = eb.head + mu.Vector(tail_offset)
        else:
            # Root or zero-length bone — give a small default
            eb.tail = eb.head + mu.Vector((0.0, 0.05, 0.0))

    # Set up parent relationships
    for bone_name in skeleton.bone_names:
        bone_def = skeleton.bones[bone_name]
        if bone_def.parent is not None and bone_def.parent in edit_bones:
            edit_bones[bone_name].parent = edit_bones[bone_def.parent]
            # Connect bones that are part of a continuous chain
            if _should_connect(bone_name):
                edit_bones[bone_name].use_connect = True

    bpy.ops.object.mode_set(mode="OBJECT")

    return arm_obj


def _bone_tail_direction(bone_name: str, length: float) -> tuple:
    """Determine the tail offset direction for a bone based on its role.

    Legs extend downward, spine extends forward, etc.
    Returns (x, y, z) offset from head to tail.
    """
    # Leg bones point downward
    if any(
        kw in bone_name
        for kw in ("upper_arm", "lower_arm", "front_hoof", "upper_leg", "lower_leg", "rear_hoof")
    ):
        return (0.0, 0.0, -length)

    # Hip and shoulder bones point slightly down and out
    if "shoulder" in bone_name or "hip" in bone_name:
        return (0.0, 0.0, -length)

    # Neck bones point up and forward
    if "neck" in bone_name:
        return (0.0, length * 0.5, length * 0.866)

    # Head points forward
    if bone_name == "head":
        return (0.0, length, 0.0)

    # Ears point up
    if "ear" in bone_name:
        return (0.0, 0.0, length)

    # Tail points backward
    if "tail" in bone_name:
        return (0.0, -length, 0.0)

    # Spine bones point forward
    return (0.0, length, 0.0)


def _should_connect(bone_name: str) -> bool:
    """Whether a bone should be connected to its parent (share head/tail)."""
    # Chain bones that form continuous limbs
    connected = {
        "upper_arm_l", "lower_arm_l", "front_hoof_l",
        "upper_arm_r", "lower_arm_r", "front_hoof_r",
        "upper_leg_l", "lower_leg_l", "rear_hoof_l",
        "upper_leg_r", "lower_leg_r", "rear_hoof_r",
        "spine_mid", "spine_upper",
        "neck_mid", "head",
        "tail_tip",
    }
    return bone_name in connected


# ---------------------------------------------------------------------------
# Armature binding (find existing)
# ---------------------------------------------------------------------------


def find_armature(name: str = "DeerArmature") -> Optional["bpy.types.Object"]:
    """Find an existing armature object by name.

    Returns None if not found.
    """
    bpy = _bpy()
    obj = bpy.data.objects.get(name)
    if obj is not None and obj.type == "ARMATURE":
        return obj
    return None


# ---------------------------------------------------------------------------
# Pose application
# ---------------------------------------------------------------------------


def apply_pose(
    arm_obj: "bpy.types.Object",
    pose: Pose,
) -> None:
    """Apply a Pose to a Blender armature's pose bones.

    Sets local rotation and location for each bone defined in the pose.
    The armature must be in POSE mode or OBJECT mode.

    Args:
        arm_obj: The Blender armature object.
        pose: The Pose to apply.
    """
    bpy = _bpy()
    mu = _mathutils()

    # Ensure we can access pose bones
    if arm_obj.mode != "POSE":
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="POSE")

    for bone_name, joint in pose.joints.items():
        pose_bone = arm_obj.pose.bones.get(bone_name)
        if pose_bone is None:
            continue

        # Set rotation (quaternion mode)
        pose_bone.rotation_mode = "QUATERNION"
        q = joint.rotation
        pose_bone.rotation_quaternion = mu.Quaternion((q.w, q.x, q.y, q.z))

        # Set location offset (relative to rest pose)
        pos = joint.position
        rest_pos = arm_obj.data.bones[bone_name].head_local
        offset = mu.Vector((float(pos[0]), float(pos[1]), float(pos[2]))) - rest_pos
        pose_bone.location = offset

    # Update the scene
    bpy.context.view_layer.update()


def reset_pose(arm_obj: "bpy.types.Object") -> None:
    """Reset all pose bones to their rest position."""
    bpy = _bpy()
    mu = _mathutils()

    if arm_obj.mode != "POSE":
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="POSE")

    for pose_bone in arm_obj.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.rotation_quaternion = mu.Quaternion((1, 0, 0, 0))
        pose_bone.location = mu.Vector((0, 0, 0))
        pose_bone.scale = mu.Vector((1, 1, 1))

    bpy.context.view_layer.update()
