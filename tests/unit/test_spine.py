"""Tests for procedural spine, neck, and tail dynamics."""

import math

import numpy as np
import pytest

from deer_me.core.spine import (
    NeckParams,
    SpineParams,
    TailParams,
    compute_neck_rotations,
    compute_spine_rotations,
    compute_tail_rotations,
)
from deer_me.core.types import Quaternion


class TestSpineRotations:
    def test_returns_correct_count(self):
        rots = compute_spine_rotations(0.0, speed=1.0, num_bones=3)
        assert len(rots) == 3

    def test_all_quaternions(self):
        rots = compute_spine_rotations(0.5, speed=1.0)
        for r in rots:
            assert isinstance(r, Quaternion)

    def test_identity_at_zero_speed(self):
        """At speed=0, spine should have no motion (identity rotations)."""
        rots = compute_spine_rotations(0.3, speed=0.0)
        for r in rots:
            np.testing.assert_allclose(r.to_array(), [1, 0, 0, 0], atol=1e-10)

    def test_motion_increases_with_speed(self):
        """Higher speed should produce larger rotations."""
        rots_slow = compute_spine_rotations(0.25, speed=0.5)
        rots_fast = compute_spine_rotations(0.25, speed=1.5)

        def _deviation(q: Quaternion) -> float:
            return float(np.linalg.norm(q.to_array() - np.array([1, 0, 0, 0])))

        for slow, fast in zip(rots_slow, rots_fast):
            assert _deviation(fast) >= _deviation(slow) - 1e-10

    def test_wave_propagation(self):
        """Successive bones should have phase-delayed rotations (not identical)."""
        rots = compute_spine_rotations(0.25, speed=1.0)
        # At least two adjacent bones should differ
        arrays = [r.to_array() for r in rots]
        any_differ = any(
            not np.allclose(arrays[i], arrays[i + 1], atol=1e-6)
            for i in range(len(arrays) - 1)
        )
        assert any_differ

    def test_custom_params(self):
        params = SpineParams(lateral_sway=0.1, vertical_undulation=0.0)
        rots = compute_spine_rotations(0.25, speed=1.0, params=params)
        assert len(rots) == 3


class TestNeckRotations:
    def test_returns_correct_count(self):
        rots = compute_neck_rotations(0.0, speed=1.0, num_bones=3)
        assert len(rots) == 3

    def test_pitch_compensation(self):
        """Neck should counter body pitch to stabilize the head."""
        # With body pitched down, neck should pitch up (negative compensation)
        rots_pitched = compute_neck_rotations(
            0.0, speed=1.0, body_pitch=0.1, num_bones=3
        )
        rots_neutral = compute_neck_rotations(
            0.0, speed=1.0, body_pitch=0.0, num_bones=3
        )
        # The rotations should differ when there's body pitch
        pitched_arr = [r.to_array() for r in rots_pitched]
        neutral_arr = [r.to_array() for r in rots_neutral]
        any_differ = any(
            not np.allclose(p, n, atol=1e-6)
            for p, n in zip(pitched_arr, neutral_arr)
        )
        assert any_differ

    def test_idle_minimal_motion(self):
        """At speed=0, neck motion should be minimal (only compensation)."""
        rots = compute_neck_rotations(0.3, speed=0.0, body_pitch=0.0)
        for r in rots:
            np.testing.assert_allclose(r.to_array(), [1, 0, 0, 0], atol=1e-6)

    def test_custom_params(self):
        params = NeckParams(head_stabilization=1.0, head_bob_amplitude=0.0)
        rots = compute_neck_rotations(0.0, speed=1.0, params=params)
        assert len(rots) == 3


class TestTailRotations:
    def test_returns_correct_count(self):
        rots = compute_tail_rotations(0.0, speed=1.0, num_bones=2)
        assert len(rots) == 2

    def test_identity_at_zero_speed(self):
        rots = compute_tail_rotations(0.3, speed=0.0)
        for r in rots:
            np.testing.assert_allclose(r.to_array(), [1, 0, 0, 0], atol=1e-10)

    def test_tip_sways_more_than_base(self):
        """Tail tip should have larger peak rotation deviation than base."""

        def _deviation(q: Quaternion) -> float:
            return float(np.linalg.norm(q.to_array() - np.array([1, 0, 0, 0])))

        # Sample across the full cycle and compare peak deviations
        base_peak = 0.0
        tip_peak = 0.0
        for i in range(100):
            phase = i / 100.0
            rots = compute_tail_rotations(phase, speed=1.0)
            base_peak = max(base_peak, _deviation(rots[0]))
            tip_peak = max(tip_peak, _deviation(rots[1]))

        assert tip_peak > base_peak

    def test_phase_lag(self):
        """Tail should have a different rotation than spine at the same cycle phase."""
        spine_rots = compute_spine_rotations(0.25, speed=1.0, num_bones=1)
        tail_rots = compute_tail_rotations(0.25, speed=1.0, num_bones=1)
        assert not np.allclose(
            spine_rots[0].to_array(), tail_rots[0].to_array(), atol=1e-6
        )

    def test_custom_params(self):
        params = TailParams(lateral_sway=0.2, vertical_sway=0.0)
        rots = compute_tail_rotations(0.0, speed=1.0, params=params)
        assert len(rots) == 2
