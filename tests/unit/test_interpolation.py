"""Tests for interpolation and easing utilities."""

import math

import numpy as np
import pytest

from deer_me.core.interpolation import (
    blend_pose,
    catmull_rom,
    cubic_hermite,
    ease_in_out_cubic,
    ease_in_out_quad,
    ease_in_out_sine,
    ease_in_quad,
    ease_out_quad,
    lerp_float,
    lerp_vec3,
    linear,
    smoothstep,
)
from deer_me.core.types import JointTransform, Pose, Quaternion, vec3


# ---------------------------------------------------------------------------
# Easing functions
# ---------------------------------------------------------------------------


class TestEasing:
    """All easing functions should satisfy f(0)=0, f(1)=1, and be monotonic."""

    EASINGS = [
        linear,
        ease_in_quad,
        ease_out_quad,
        ease_in_out_quad,
        ease_in_out_cubic,
        ease_in_out_sine,
        smoothstep,
    ]

    @pytest.mark.parametrize("fn", EASINGS)
    def test_endpoints(self, fn):
        assert fn(0.0) == pytest.approx(0.0, abs=1e-10)
        assert fn(1.0) == pytest.approx(1.0, abs=1e-10)

    @pytest.mark.parametrize("fn", EASINGS)
    def test_monotonic(self, fn):
        """Check that the function is non-decreasing over [0, 1]."""
        prev = fn(0.0)
        for i in range(1, 101):
            t = i / 100.0
            val = fn(t)
            assert val >= prev - 1e-10, f"{fn.__name__} not monotonic at t={t}"
            prev = val

    def test_smoothstep_flat_at_endpoints(self):
        """Smoothstep should have near-zero derivative at 0 and 1."""
        eps = 1e-5
        d0 = (smoothstep(eps) - smoothstep(0.0)) / eps
        d1 = (smoothstep(1.0) - smoothstep(1.0 - eps)) / eps
        assert abs(d0) < 0.01
        assert abs(d1) < 0.01


# ---------------------------------------------------------------------------
# Lerp
# ---------------------------------------------------------------------------


class TestLerp:
    def test_lerp_float_endpoints(self):
        assert lerp_float(0.0, 10.0, 0.0) == 0.0
        assert lerp_float(0.0, 10.0, 1.0) == 10.0

    def test_lerp_float_midpoint(self):
        assert lerp_float(2.0, 8.0, 0.5) == 5.0

    def test_lerp_vec3(self):
        a = vec3(0, 0, 0)
        b = vec3(10, 20, 30)
        mid = lerp_vec3(a, b, 0.5)
        np.testing.assert_allclose(mid, [5, 10, 15])


# ---------------------------------------------------------------------------
# Pose blending
# ---------------------------------------------------------------------------


class TestBlendPose:
    def test_blend_at_zero(self):
        pa = Pose()
        pa.set_position("bone", vec3(0, 0, 0))
        pb = Pose()
        pb.set_position("bone", vec3(10, 0, 0))

        result = blend_pose(pa, pb, 0.0)
        np.testing.assert_allclose(result.joints["bone"].position, [0, 0, 0])

    def test_blend_at_one(self):
        pa = Pose()
        pa.set_position("bone", vec3(0, 0, 0))
        pb = Pose()
        pb.set_position("bone", vec3(10, 0, 0))

        result = blend_pose(pa, pb, 1.0)
        np.testing.assert_allclose(result.joints["bone"].position, [10, 0, 0])

    def test_blend_midpoint(self):
        pa = Pose()
        pa.set_position("bone", vec3(0, 0, 0))
        pb = Pose()
        pb.set_position("bone", vec3(10, 0, 0))

        result = blend_pose(pa, pb, 0.5)
        np.testing.assert_allclose(result.joints["bone"].position, [5, 0, 0])

    def test_blend_with_easing(self):
        pa = Pose()
        pa.set_position("bone", vec3(0, 0, 0))
        pb = Pose()
        pb.set_position("bone", vec3(10, 0, 0))

        # ease_in_quad at t=0.5 → 0.25
        result = blend_pose(pa, pb, 0.5, easing=ease_in_quad)
        np.testing.assert_allclose(result.joints["bone"].position, [2.5, 0, 0])

    def test_blend_clamps_t(self):
        pa = Pose()
        pa.set_position("bone", vec3(0, 0, 0))
        pb = Pose()
        pb.set_position("bone", vec3(10, 0, 0))

        # t > 1 should clamp
        result = blend_pose(pa, pb, 5.0)
        np.testing.assert_allclose(result.joints["bone"].position, [10, 0, 0])

    def test_blend_disjoint_joints(self):
        pa = Pose()
        pa.set_position("bone_a", vec3(1, 0, 0))
        pb = Pose()
        pb.set_position("bone_b", vec3(0, 1, 0))

        result = blend_pose(pa, pb, 0.5)
        assert "bone_a" in result.joints
        assert "bone_b" in result.joints


# ---------------------------------------------------------------------------
# Cubic Hermite / Catmull-Rom
# ---------------------------------------------------------------------------


class TestSplines:
    def test_cubic_hermite_endpoints(self):
        assert cubic_hermite(0.0, 1.0, 1.0, 1.0, 0.0) == pytest.approx(0.0)
        assert cubic_hermite(0.0, 1.0, 1.0, 1.0, 1.0) == pytest.approx(1.0)

    def test_catmull_rom_passes_through_points(self):
        points = [0.0, 1.0, 0.5, 0.8]
        assert catmull_rom(points, 0.0) == pytest.approx(0.0, abs=1e-10)
        assert catmull_rom(points, 1.0) == pytest.approx(0.8, abs=1e-10)
        # t=1/3 should be approximately at points[1]
        assert catmull_rom(points, 1.0 / 3.0) == pytest.approx(1.0, abs=1e-10)

    def test_catmull_rom_single_point(self):
        assert catmull_rom([5.0], 0.5) == 5.0

    def test_catmull_rom_two_points(self):
        result = catmull_rom([0.0, 1.0], 0.5)
        assert 0.0 <= result <= 1.0
