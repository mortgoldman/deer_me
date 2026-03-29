"""Tests for the deer skeleton definition."""

import numpy as np
import pytest

from deer_me.core.skeleton import (
    ALL_BONE_NAMES,
    FRONT_HOOF_L,
    HEAD,
    ROOT,
    SPINE_BASE,
    SPINE_UPPER,
    Skeleton,
    build_bone_defs,
)
from deer_me.core.types import Pose


class TestBoneDefs:
    def test_bone_count(self):
        bones = build_bone_defs()
        assert len(bones) == 27

    def test_all_names_present(self):
        bones = build_bone_defs()
        for name in ALL_BONE_NAMES:
            assert name in bones, f"Missing bone: {name}"

    def test_root_has_no_parent(self):
        bones = build_bone_defs()
        assert bones[ROOT].parent is None

    def test_all_non_root_have_parent(self):
        bones = build_bone_defs()
        for name, bone in bones.items():
            if name != ROOT:
                assert bone.parent is not None, f"{name} should have a parent"
                assert bone.parent in bones, f"{name}'s parent '{bone.parent}' not found"

    def test_no_self_parenting(self):
        bones = build_bone_defs()
        for name, bone in bones.items():
            assert bone.parent != name


class TestSkeleton:
    @pytest.fixture
    def skel(self):
        return Skeleton()

    def test_bone_names(self, skel):
        assert len(skel.bone_names) == 27

    def test_children_of_root(self, skel):
        # Root's only child is spine_base
        children = skel.children(ROOT)
        assert SPINE_BASE in children

    def test_parent(self, skel):
        assert skel.parent(SPINE_BASE) == ROOT
        assert skel.parent(ROOT) is None

    def test_chain_spine_to_head(self, skel):
        chain = skel.chain(SPINE_BASE, HEAD)
        assert chain[0] == SPINE_BASE
        assert chain[-1] == HEAD
        # Every element's parent should be the previous element
        for i in range(1, len(chain)):
            assert skel.parent(chain[i]) == chain[i - 1]

    def test_chain_invalid(self, skel):
        with pytest.raises(ValueError):
            skel.chain(HEAD, FRONT_HOOF_L)  # No path (hoof is not a child of head)

    def test_rest_pose(self, skel):
        pose = skel.rest_pose()
        assert isinstance(pose, Pose)
        assert len(pose.joints) == 27
        # Root should be at origin
        np.testing.assert_array_equal(pose.joints[ROOT].position, [0, 0, 0])

    def test_rest_pose_spine_above_ground(self, skel):
        pose = skel.rest_pose()
        # Spine base Z should be positive (above ground)
        assert pose.joints[SPINE_BASE].position[2] > 0.5

    def test_symmetry_shoulders(self, skel):
        """Left and right shoulders should be symmetric across X."""
        bones = skel.bones
        l_pos = bones["shoulder_l"].rest_position
        r_pos = bones["shoulder_r"].rest_position
        assert l_pos[0] == pytest.approx(-r_pos[0])  # X mirrored
        assert l_pos[1] == pytest.approx(r_pos[1])    # Y same
        assert l_pos[2] == pytest.approx(r_pos[2])    # Z same

    def test_symmetry_hips(self, skel):
        bones = skel.bones
        l_pos = bones["hip_l"].rest_position
        r_pos = bones["hip_r"].rest_position
        assert l_pos[0] == pytest.approx(-r_pos[0])
        assert l_pos[1] == pytest.approx(r_pos[1])
        assert l_pos[2] == pytest.approx(r_pos[2])
