"""Tests for core data types — vectors, quaternions, poses."""

import math

import numpy as np
import pytest

from deer_me.core.types import (
    GaitPhase,
    GaitType,
    JointTransform,
    LegId,
    Pose,
    Quaternion,
    slerp,
    vec3,
)


# ---------------------------------------------------------------------------
# Vec3
# ---------------------------------------------------------------------------


class TestVec3:
    def test_default(self):
        v = vec3()
        np.testing.assert_array_equal(v, [0.0, 0.0, 0.0])

    def test_values(self):
        v = vec3(1.0, 2.0, 3.0)
        assert v[0] == 1.0
        assert v[1] == 2.0
        assert v[2] == 3.0

    def test_dtype(self):
        v = vec3(1, 2, 3)
        assert v.dtype == np.float64


# ---------------------------------------------------------------------------
# Quaternion
# ---------------------------------------------------------------------------


class TestQuaternion:
    def test_identity(self):
        q = Quaternion.identity()
        assert q.w == 1.0
        assert q.x == 0.0

    def test_from_axis_angle_zero(self):
        q = Quaternion.from_axis_angle(vec3(0, 0, 1), 0.0)
        assert abs(q.w - 1.0) < 1e-10

    def test_from_axis_angle_90_deg(self):
        q = Quaternion.from_axis_angle(vec3(0, 0, 1), math.pi / 2)
        assert abs(q.w - math.cos(math.pi / 4)) < 1e-10
        assert abs(q.z - math.sin(math.pi / 4)) < 1e-10

    def test_multiply_identity(self):
        q = Quaternion.from_axis_angle(vec3(1, 0, 0), 0.5)
        result = q * Quaternion.identity()
        np.testing.assert_allclose(result.to_array(), q.to_array(), atol=1e-10)

    def test_conjugate(self):
        q = Quaternion(0.5, 0.5, 0.5, 0.5)
        c = q.conjugate()
        assert c.w == q.w
        assert c.x == -q.x
        assert c.y == -q.y
        assert c.z == -q.z

    def test_normalize(self):
        q = Quaternion(2.0, 0.0, 0.0, 0.0)
        n = q.normalized()
        assert abs(n.w - 1.0) < 1e-10

    def test_rotate_vector_z_90(self):
        """Rotate X-axis 90 degrees around Z — should give Y-axis."""
        q = Quaternion.from_axis_angle(vec3(0, 0, 1), math.pi / 2)
        v = q.rotate_vector(vec3(1, 0, 0))
        np.testing.assert_allclose(v, [0, 1, 0], atol=1e-10)


# ---------------------------------------------------------------------------
# Slerp
# ---------------------------------------------------------------------------


class TestSlerp:
    def test_slerp_endpoints(self):
        q0 = Quaternion.identity()
        q1 = Quaternion.from_axis_angle(vec3(0, 0, 1), math.pi / 2)
        r0 = slerp(q0, q1, 0.0)
        r1 = slerp(q0, q1, 1.0)
        np.testing.assert_allclose(r0.to_array(), q0.to_array(), atol=1e-10)
        np.testing.assert_allclose(r1.to_array(), q1.to_array(), atol=1e-10)

    def test_slerp_midpoint(self):
        q0 = Quaternion.identity()
        q1 = Quaternion.from_axis_angle(vec3(0, 0, 1), math.pi / 2)
        mid = slerp(q0, q1, 0.5)
        expected = Quaternion.from_axis_angle(vec3(0, 0, 1), math.pi / 4)
        np.testing.assert_allclose(mid.to_array(), expected.to_array(), atol=1e-10)

    def test_slerp_same_quat(self):
        q = Quaternion.from_axis_angle(vec3(1, 0, 0), 1.0)
        result = slerp(q, q, 0.5)
        np.testing.assert_allclose(result.to_array(), q.to_array(), atol=1e-10)


# ---------------------------------------------------------------------------
# Pose
# ---------------------------------------------------------------------------


class TestPose:
    def test_empty_pose(self):
        p = Pose()
        assert len(p.joints) == 0

    def test_get_creates_default(self):
        p = Pose()
        jt = p.get("foo")
        assert isinstance(jt, JointTransform)
        assert "foo" in p.joints

    def test_set_rotation(self):
        p = Pose()
        q = Quaternion.from_axis_angle(vec3(1, 0, 0), 0.5)
        p.set_rotation("bone_a", q)
        assert p.joints["bone_a"].rotation.w == q.w

    def test_set_position(self):
        p = Pose()
        p.set_position("bone_a", vec3(1, 2, 3))
        np.testing.assert_array_equal(p.joints["bone_a"].position, [1, 2, 3])

    def test_set_position_is_copy(self):
        """Mutating the original vec should not affect the pose."""
        p = Pose()
        v = vec3(1, 2, 3)
        p.set_position("bone_a", v)
        v[0] = 999
        assert p.joints["bone_a"].position[0] == 1.0


# ---------------------------------------------------------------------------
# GaitPhase / enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_gait_types(self):
        assert GaitType.WALK != GaitType.TROT

    def test_leg_ids(self):
        assert len(LegId) == 4

    def test_gait_phase_defaults(self):
        gp = GaitPhase()
        assert gp.phase == 0.0
        assert gp.leg_phases == {}
