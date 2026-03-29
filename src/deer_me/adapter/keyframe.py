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

        # Location offset
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
    """Insert keyframes using direct fcurve access for better performance.

    This bypasses the operator-based keyframe insertion and writes directly
    to fcurves, which is significantly faster for long animations.

    Args:
        arm_obj: The Blender armature object.
        sequence: List of (frame_number, Pose) pairs.
    """
    bpy = _bpy()

    if arm_obj.mode != "POSE":
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="POSE")

    # Ensure the armature has an animation action
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    if arm_obj.animation_data.action is None:
        arm_obj.animation_data.action = bpy.data.actions.new(
            name=f"{arm_obj.name}_Action"
        )

    action = arm_obj.animation_data.action

    # Collect all bone names that appear in any pose
    all_bone_names = set()
    for _, pose in sequence:
        all_bone_names.update(pose.joints.keys())

    # Pre-create fcurves for each bone's channels
    fcurve_map = {}  # (bone_name, channel, index) -> fcurve

    for bone_name in all_bone_names:
        pose_bone = arm_obj.pose.bones.get(bone_name)
        if pose_bone is None:
            continue

        pose_bone.rotation_mode = "QUATERNION"
        data_path_rot = f'pose.bones["{bone_name}"].rotation_quaternion'
        data_path_loc = f'pose.bones["{bone_name}"].location'

        # Rotation: 4 channels (W, X, Y, Z)
        for i in range(4):
            fc = _find_or_create_fcurve(action, data_path_rot, i)
            fcurve_map[(bone_name, "rot", i)] = fc

        # Location: 3 channels (X, Y, Z)
        for i in range(3):
            fc = _find_or_create_fcurve(action, data_path_loc, i)
            fcurve_map[(bone_name, "loc", i)] = fc

    # Insert keyframe points in bulk
    for frame, pose in sequence:
        for bone_name, joint in pose.joints.items():
            if arm_obj.pose.bones.get(bone_name) is None:
                continue

            # Rotation quaternion values
            q = joint.rotation
            quat_vals = [q.w, q.x, q.y, q.z]
            for i, val in enumerate(quat_vals):
                key = (bone_name, "rot", i)
                if key in fcurve_map:
                    fcurve_map[key].keyframe_points.insert(
                        frame, val, options={"FAST"}
                    )

            # Location offset values
            pos = joint.position
            rest_pos = arm_obj.data.bones[bone_name].head_local
            offset = [
                float(pos[0]) - rest_pos[0],
                float(pos[1]) - rest_pos[1],
                float(pos[2]) - rest_pos[2],
            ]
            for i, val in enumerate(offset):
                key = (bone_name, "loc", i)
                if key in fcurve_map:
                    fcurve_map[key].keyframe_points.insert(
                        frame, val, options={"FAST"}
                    )

    # Update all fcurves after bulk insertion
    for fc in fcurve_map.values():
        fc.update()


def _find_or_create_fcurve(action, data_path: str, index: int):
    """Find an existing fcurve or create a new one."""
    for fc in action.fcurves:
        if fc.data_path == data_path and fc.array_index == index:
            return fc
    return action.fcurves.new(data_path=data_path, index=index)


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
