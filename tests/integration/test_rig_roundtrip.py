"""Integration tests — armature creation and pose roundtrip.

These tests run inside Blender's Python environment and verify that:
1. A Skeleton can be converted to a Blender armature
2. Poses can be applied and read back
3. Keyframes can be inserted and the timeline works

Skipped automatically if bpy is not available.
"""

from __future__ import annotations

import pytest

try:
    import bpy

    HAS_BPY = True
except ImportError:
    HAS_BPY = False

pytestmark = pytest.mark.skipif(not HAS_BPY, reason="Blender (bpy) not available")


class TestArmatureCreation:
    def test_create_armature(self, clean_scene, skeleton):
        from deer_me.adapter.rig import create_armature

        arm_obj = create_armature(skeleton)

        assert arm_obj is not None
        assert arm_obj.type == "ARMATURE"
        assert len(arm_obj.data.bones) == len(skeleton.bone_names)

    def test_bone_names_match(self, clean_scene, skeleton):
        from deer_me.adapter.rig import create_armature

        arm_obj = create_armature(skeleton)
        blender_names = {b.name for b in arm_obj.data.bones}
        expected_names = set(skeleton.bone_names)

        assert blender_names == expected_names

    def test_parent_relationships(self, clean_scene, skeleton):
        from deer_me.adapter.rig import create_armature

        arm_obj = create_armature(skeleton)

        for bone in arm_obj.data.bones:
            expected_parent = skeleton.parent(bone.name)
            if expected_parent is None:
                assert bone.parent is None
            else:
                assert bone.parent is not None
                assert bone.parent.name == expected_parent

    def test_find_armature(self, clean_scene, skeleton):
        from deer_me.adapter.rig import create_armature, find_armature

        create_armature(skeleton, name="TestDeer")
        found = find_armature("TestDeer")

        assert found is not None
        assert found.name == "TestDeer"

    def test_find_armature_missing(self, clean_scene):
        from deer_me.adapter.rig import find_armature

        assert find_armature("NonExistent") is None


class TestPoseApplication:
    def test_apply_rest_pose(self, clean_scene, skeleton):
        from deer_me.adapter.rig import apply_pose, create_armature

        arm_obj = create_armature(skeleton)
        rest = skeleton.rest_pose()
        apply_pose(arm_obj, rest)

        # Should not raise
        assert arm_obj.mode == "POSE"

    def test_apply_and_reset(self, clean_scene, skeleton):
        from deer_me.adapter.rig import (
            apply_pose,
            create_armature,
            reset_pose,
        )

        arm_obj = create_armature(skeleton)
        rest = skeleton.rest_pose()
        apply_pose(arm_obj, rest)
        reset_pose(arm_obj)

        # All pose bones should be at identity rotation
        for pb in arm_obj.pose.bones:
            q = pb.rotation_quaternion
            assert abs(q.w - 1.0) < 1e-4
            assert abs(q.x) < 1e-4


class TestKeyframeInsertion:
    def test_insert_single_keyframe(self, clean_scene, skeleton):
        from deer_me.adapter.keyframe import insert_pose_keyframe
        from deer_me.adapter.rig import create_armature

        arm_obj = create_armature(skeleton)
        rest = skeleton.rest_pose()
        insert_pose_keyframe(arm_obj, rest, frame=1)

        assert arm_obj.animation_data is not None
        assert arm_obj.animation_data.action is not None

    def test_insert_sequence(self, clean_scene, skeleton):
        from deer_me.adapter.keyframe import insert_pose_sequence
        from deer_me.adapter.rig import create_armature
        from deer_me.core.state_machine import LocoState, LocomotionStateMachine

        arm_obj = create_armature(skeleton)
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)

        sequence = []
        for frame in range(1, 25):
            sm.update(1.0 / 24.0)
            pose = sm.evaluate(skeleton)
            sequence.append((frame, pose))

        insert_pose_sequence(arm_obj, sequence)

        action = arm_obj.animation_data.action
        from deer_me.adapter.keyframe import _get_action_fcurves
        assert len(_get_action_fcurves(action)) > 0

    def test_batch_insert(self, clean_scene, skeleton):
        from deer_me.adapter.keyframe import batch_insert_sequence
        from deer_me.adapter.rig import create_armature
        from deer_me.core.state_machine import LocoState, LocomotionStateMachine

        arm_obj = create_armature(skeleton)
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)

        sequence = []
        for frame in range(1, 49):
            sm.update(1.0 / 24.0)
            pose = sm.evaluate(skeleton)
            sequence.append((frame, pose))

        batch_insert_sequence(arm_obj, sequence)

        action = arm_obj.animation_data.action
        from deer_me.adapter.keyframe import _get_action_fcurves
        assert len(_get_action_fcurves(action)) > 0

    def test_clear_keyframes(self, clean_scene, skeleton):
        from deer_me.adapter.keyframe import (
            clear_keyframes,
            insert_pose_keyframe,
        )
        from deer_me.adapter.rig import create_armature

        arm_obj = create_armature(skeleton)
        rest = skeleton.rest_pose()
        insert_pose_keyframe(arm_obj, rest, frame=1)

        clear_keyframes(arm_obj)
        assert arm_obj.animation_data is None or arm_obj.animation_data.action is None
