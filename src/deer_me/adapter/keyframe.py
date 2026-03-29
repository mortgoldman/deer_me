"""Blender keyframe adapter — writes Pose sequences to fcurves.

Converts a list of (frame, Pose) pairs into Blender keyframes on an
armature's pose bones. Supports batch insertion for performance.

All bpy access is lazy-imported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

from deer_me.core.types import Pose

if TYPE_CHECKING:
    import bpy


def _bpy():
    import bpy as _bpy

    return _bpy


def _mathutils():
    import mathutils as _mu

    return _mu


# ---------------------------------------------------------------------------
# Keyframe insertion
# ---------------------------------------------------------------------------


def insert_pose_keyframe(
    arm_obj: "bpy.types.Object",
    pose: Pose,
    frame: int,
) -> None:
    """Insert keyframes for all joints in a Pose at a given frame.

    Args:
        arm_obj: The Blender armature object.
        pose: The pose to keyframe.
        frame: The frame number to insert at.
    """
    bpy = _bpy()
    mu = _mathutils()

    scene = bpy.context.scene
    scene.frame_set(frame)

    if arm_obj.mode != "POSE":
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="POSE")

    for bone_name, joint in pose.joints.items():
        pose_bone = arm_obj.pose.bones.get(bone_name)
        if pose_bone is None:
            continue

        # Rotation
        pose_bone.rotation_mode = "QUATERNION"
        q = joint.rotation
        pose_bone.rotation_quaternion = mu.Quaternion((q.w, q.x, q.y, q.z))
        pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

        # Location offset — only for bones with explicitly set positions
        if pose.has_position_change(bone_name):
            pos = joint.position
            rest_pos = arm_obj.data.bones[bone_name].head_local
            offset = mu.Vector((float(pos[0]), float(pos[1]), float(pos[2]))) - rest_pos
            pose_bone.location = offset
            pose_bone.keyframe_insert(data_path="location", frame=frame)


def insert_pose_sequence(
    arm_obj: "bpy.types.Object",
    sequence: List[Tuple[int, Pose]],
) -> None:
    """Insert keyframes for an entire pose sequence.

    Args:
        arm_obj: The Blender armature object.
        sequence: List of (frame_number, Pose) pairs, sorted by frame.
    """
    for frame, pose in sequence:
        insert_pose_keyframe(arm_obj, pose, frame)


# ---------------------------------------------------------------------------
# Batch keyframe insertion (faster for long sequences)
# ---------------------------------------------------------------------------


def batch_insert_sequence(
    arm_obj: "bpy.types.Object",
    sequence: List[Tuple[int, Pose]],
) -> None:
    """Insert keyframes for an entire pose sequence.

    Uses keyframe_insert per bone per frame. This lets Blender manage
    its internal action format (layered in 5.x, legacy in 4.x) and
    keeps compatibility across versions.

    For very long sequences, consider insert_pose_sequence as an
    alternative — both use the same approach.

    Args:
        arm_obj: The Blender armature object.
        sequence: List of (frame_number, Pose) pairs.
    """
    bpy = _bpy()
    mu = _mathutils()

    if arm_obj.mode != "POSE":
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="POSE")

    # Ensure all pose bones use quaternion rotation
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "QUATERNION"

    for frame, pose in sequence:
        bpy.context.scene.frame_set(frame)

        for bone_name, joint in pose.joints.items():
            pose_bone = arm_obj.pose.bones.get(bone_name)
            if pose_bone is None:
                continue

            # Rotation
            q = joint.rotation
            pose_bone.rotation_quaternion = mu.Quaternion((q.w, q.x, q.y, q.z))
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

            # Location offset — only for bones with explicitly set positions
            if pose.has_position_change(bone_name):
                pos = joint.position
                rest_pos = arm_obj.data.bones[bone_name].head_local
                offset = mu.Vector(
                    (float(pos[0]) - rest_pos[0],
                     float(pos[1]) - rest_pos[1],
                     float(pos[2]) - rest_pos[2])
                )
                pose_bone.location = offset
                pose_bone.keyframe_insert(data_path="location", frame=frame)


def _get_action_fcurves(action) -> list:
    """Get fcurves from an action, handling both legacy (4.x) and layered (5.x) APIs."""
    # Blender 5.x: layered actions
    if hasattr(action, "is_action_layered") and action.is_action_layered:
        if action.layers and action.layers[0].strips:
            strip = action.layers[0].strips[0]
            if strip.channelbags:
                return list(strip.channelbags[0].fcurves)
        return []

    # Blender 4.x: legacy actions with direct fcurves
    if hasattr(action, "fcurves"):
        return list(action.fcurves)

    return []


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def clear_keyframes(arm_obj: "bpy.types.Object") -> None:
    """Remove all keyframes from the armature."""
    bpy = _bpy()

    if arm_obj.animation_data and arm_obj.animation_data.action:
        bpy.data.actions.remove(arm_obj.animation_data.action)

    arm_obj.animation_data_clear()


def set_frame_range(start: int, end: int) -> None:
    """Set the scene's playback frame range."""
    bpy = _bpy()
    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    scene.frame_set(start)
