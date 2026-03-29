"""Tests for the two-bone IK solver."""

import math

import numpy as np
import pytest

from deer_me.core.ik_solver import IKResult, solve_two_bone, _rotation_between
from deer_me.core.types import Quaternion, vec3


class TestSolveTwoBone:
    """Tests for the core two-bone IK solver."""

    def test_straight_down(self):
        """Target directly below root — legs fully extended."""
        result = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(0, 0, 0),
            upper_length=0.5,
            lower_length=0.5,
        )
        assert isinstance(result, IKResult)
        # End position should be near the target
        np.testing.assert_allclose(result.end_position[2], 0.0, atol=0.05)

    def test_reachable_target(self):
        """Target within reach should report reached=True."""
        result = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(0, 0, 0.3),
            upper_length=0.4,
            lower_length=0.4,
        )
        assert result.reached is True

    def test_unreachable_target(self):
        """Target beyond max reach should report reached=False."""
        result = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(0, 0, -5),  # Way below
            upper_length=0.3,
            lower_length=0.3,
        )
        assert result.reached is False

    def test_end_position_near_target(self):
        """When reachable, end position should be close to target."""
        target = vec3(0.1, 0.1, 0.3)
        result = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=target,
            upper_length=0.4,
            lower_length=0.4,
        )
        dist = float(np.linalg.norm(result.end_position - target))
        assert dist < 0.15  # Reasonable tolerance for the solver

    def test_returns_quaternions(self):
        result = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(0, 0, 0.2),
            upper_length=0.5,
            lower_length=0.4,
        )
        assert isinstance(result.upper_rotation, Quaternion)
        assert isinstance(result.lower_rotation, Quaternion)

    def test_symmetric_targets(self):
        """Left and right targets should produce mirrored results."""
        r_left = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(-0.2, 0, 0.2),
            upper_length=0.5,
            lower_length=0.4,
        )
        r_right = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(0.2, 0, 0.2),
            upper_length=0.5,
            lower_length=0.4,
        )
        # End positions should be mirrored in X
        assert r_left.end_position[0] == pytest.approx(-r_right.end_position[0], abs=0.05)

    def test_with_pole_target(self):
        """Pole target should influence the bend direction."""
        # Knee bending forward (+Y)
        r_forward = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(0, 0, 0.2),
            upper_length=0.5,
            lower_length=0.5,
            pole_target=vec3(0, 1, 0.5),
        )
        # Knee bending backward (-Y)
        r_backward = solve_two_bone(
            root_pos=vec3(0, 0, 1),
            target_pos=vec3(0, 0, 0.2),
            upper_length=0.5,
            lower_length=0.5,
            pole_target=vec3(0, -1, 0.5),
        )
        # The rotations should differ
        assert not np.allclose(
            r_forward.upper_rotation.to_array(),
            r_backward.upper_rotation.to_array(),
            atol=0.01,
        )

    def test_zero_distance(self):
        """Target at root position — degenerate but should not crash."""
        result = solve_two_bone(
            root_pos=vec3(0, 0, 0),
            target_pos=vec3(0, 0, 0),
            upper_length=0.3,
            lower_length=0.3,
        )
        assert isinstance(result, IKResult)


class TestRotationBetween:
    def test_same_vector(self):
        q = _rotation_between(vec3(0, 0, 1), vec3(0, 0, 1))
        np.testing.assert_allclose(q.to_array(), [1, 0, 0, 0], atol=1e-6)

    def test_opposite_vectors(self):
        q = _rotation_between(vec3(0, 0, 1), vec3(0, 0, -1))
        # Should be a 180-degree rotation
        v = q.rotate_vector(vec3(0, 0, 1))
        np.testing.assert_allclose(v, [0, 0, -1], atol=1e-6)

    def test_90_degree(self):
        q = _rotation_between(vec3(0, 0, 1), vec3(1, 0, 0))
        v = q.rotate_vector(vec3(0, 0, 1))
        np.testing.assert_allclose(v, [1, 0, 0], atol=1e-6)
