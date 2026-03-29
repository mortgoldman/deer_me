"""Integration tests — full animation sequence end-to-end.

Tests the complete pipeline: scene setup → armature → animation → verify.
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


class TestFullSequence:
    def test_scene_setup(self, clean_scene):
        from deer_me.adapter.scene import setup_deer_scene

        result = setup_deer_scene(fps=24, frame_end=120)

        assert result["ground"] is not None
        assert len(result["lights"]) == 3
        assert result["camera"] is not None
        assert bpy.context.scene.camera is not None

    def test_walk_cycle_animation(self, clean_scene, skeleton):
        """Full pipeline: create scene, armature, animate walk, verify frames."""
        from deer_me.adapter.keyframe import batch_insert_sequence
        from deer_me.adapter.rig import create_armature
        from deer_me.adapter.scene import setup_deer_scene
        from deer_me.core.state_machine import LocoState, LocomotionStateMachine

        # Setup
        setup_deer_scene(fps=24, frame_end=48)
        arm_obj = create_armature(skeleton)

        # Generate 2 seconds of walk
        sm = LocomotionStateMachine()
        sm.request_transition(LocoState.WALK, speed=1.0)
        sm.update(0.5)  # Complete transition

        sequence = []
        for frame in range(1, 49):
            sm.update(1.0 / 24.0)
            pose = sm.evaluate(skeleton)
            sequence.append((frame, pose))

        batch_insert_sequence(arm_obj, sequence)

        # Verify
        action = arm_obj.animation_data.action
        from deer_me.adapter.keyframe import _get_action_fcurves
        fcurves = _get_action_fcurves(action)
        assert len(fcurves) > 0

        # Check that keyframes span the expected range
        all_frames = set()
        for fc in fcurves:
            for kp in fc.keyframe_points:
                all_frames.add(int(kp.co[0]))
        assert min(all_frames) == 1
        assert max(all_frames) == 48

    def test_gait_transition_animation(self, clean_scene, skeleton):
        """Animate idle → walk → trot → walk → idle with transitions."""
        from deer_me.adapter.keyframe import batch_insert_sequence
        from deer_me.adapter.rig import create_armature
        from deer_me.core.state_machine import LocoState, LocomotionStateMachine

        arm_obj = create_armature(skeleton)
        sm = LocomotionStateMachine()

        transitions = [
            (1, LocoState.WALK, 1.0),
            (49, LocoState.TROT, 1.5),
            (97, LocoState.WALK, 1.0),
            (145, LocoState.IDLE, 0.0),
        ]

        sequence = []
        trans_idx = 0

        for frame in range(1, 193):
            if trans_idx < len(transitions) and frame == transitions[trans_idx][0]:
                _, state, speed = transitions[trans_idx]
                sm.request_transition(state, speed=speed)
                trans_idx += 1

            sm.update(1.0 / 24.0)
            pose = sm.evaluate(skeleton)
            sequence.append((frame, pose))

        batch_insert_sequence(arm_obj, sequence)

        action = arm_obj.animation_data.action
        from deer_me.adapter.keyframe import _get_action_fcurves
        assert len(_get_action_fcurves(action)) > 0

    def test_proxy_mesh_binding(self, clean_scene, skeleton):
        """Create armature, proxy mesh, and verify binding."""
        from deer_me.adapter.rig import create_armature
        from deer_me.adapter.skin import create_proxy_mesh

        arm_obj = create_armature(skeleton)
        mesh_obj = create_proxy_mesh(arm_obj, bind=True)

        assert mesh_obj is not None
        assert mesh_obj.parent == arm_obj
        # Should have an armature modifier
        arm_mods = [m for m in mesh_obj.modifiers if m.type == "ARMATURE"]
        assert len(arm_mods) > 0
