"""Tests for gait cycle definitions and evaluation."""

import math

import numpy as np
import pytest

from deer_me.core.gaits import (
    GAIT_PRESETS,
    GALLOP_PARAMS,
    TROT_PARAMS,
    WALK_PARAMS,
    body_bob,
    body_pitch,
    compute_foot_target,
    foot_height,
    foot_stride_offset,
    is_stance,
    leg_phase,
    swing_progress,
)
from deer_me.core.types import GaitType, LegId, vec3


class TestGaitPresets:
    def test_all_gait_types_have_presets(self):
        for gt in [GaitType.WALK, GaitType.TROT, GaitType.GALLOP]:
            assert gt in GAIT_PRESETS

    def test_all_legs_have_offsets(self):
        for params in GAIT_PRESETS.values():
            for leg in LegId:
                assert leg in params.leg_offsets

    def test_offsets_in_range(self):
        for params in GAIT_PRESETS.values():
            for offset in params.leg_offsets.values():
                assert 0.0 <= offset < 1.0

    def test_walk_lateral_sequence(self):
        """Walk: no two legs on the same side lift at the same time."""
        offsets = WALK_PARAMS.leg_offsets
        # Front left and rear left should not have the same phase
        assert offsets[LegId.FRONT_LEFT] != offsets[LegId.REAR_LEFT]
        # Front right and rear right should not have the same phase
        assert offsets[LegId.FRONT_RIGHT] != offsets[LegId.REAR_RIGHT]

    def test_trot_diagonal_pairs(self):
        """Trot: diagonal legs move together."""
        offsets = TROT_PARAMS.leg_offsets
        assert offsets[LegId.FRONT_LEFT] == offsets[LegId.REAR_RIGHT]
        assert offsets[LegId.FRONT_RIGHT] == offsets[LegId.REAR_LEFT]

    def test_duty_factor_ordering(self):
        """Walk has highest duty factor, gallop has lowest."""
        assert WALK_PARAMS.duty_factor > TROT_PARAMS.duty_factor
        assert TROT_PARAMS.duty_factor > GALLOP_PARAMS.duty_factor


class TestLegPhase:
    def test_zero_offset(self):
        assert leg_phase(0.3, LegId.FRONT_LEFT, WALK_PARAMS) == pytest.approx(0.3)

    def test_wraps_around(self):
        # FRONT_RIGHT has offset 0.5 in walk
        lp = leg_phase(0.7, LegId.FRONT_RIGHT, WALK_PARAMS)
        assert lp == pytest.approx(0.2, abs=1e-10)

    def test_always_in_range(self):
        for phase in [0.0, 0.25, 0.5, 0.75, 0.99]:
            for leg in LegId:
                lp = leg_phase(phase, leg, WALK_PARAMS)
                assert 0.0 <= lp < 1.0


class TestStanceSwing:
    def test_stance_at_zero(self):
        assert is_stance(0.0, 0.6) is True

    def test_stance_just_before_duty(self):
        assert is_stance(0.59, 0.6) is True

    def test_swing_at_duty(self):
        assert is_stance(0.6, 0.6) is False

    def test_swing_progress_during_stance(self):
        assert swing_progress(0.3, 0.6) == -1.0

    def test_swing_progress_at_start(self):
        assert swing_progress(0.6, 0.6) == pytest.approx(0.0)

    def test_swing_progress_at_end(self):
        # Just before phase wraps
        assert swing_progress(0.99, 0.6) == pytest.approx(0.975, abs=0.01)


class TestFootHeight:
    def test_zero_during_stance(self):
        for phase in [0.0, 0.1, 0.3, 0.5]:
            assert foot_height(phase, WALK_PARAMS) == 0.0

    def test_peak_at_mid_swing(self):
        """Peak height should occur at the midpoint of swing."""
        duty = WALK_PARAMS.duty_factor
        mid_swing = duty + (1.0 - duty) * 0.5
        h = foot_height(mid_swing, WALK_PARAMS)
        assert h == pytest.approx(WALK_PARAMS.swing_height, abs=1e-6)

    def test_positive_during_swing(self):
        duty = WALK_PARAMS.duty_factor
        for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
            swing_phase = duty + t * (1.0 - duty)
            if swing_phase < 1.0:
                assert foot_height(swing_phase, WALK_PARAMS) > 0.0

    def test_smooth_arc(self):
        """Height should increase then decrease (single peak)."""
        duty = WALK_PARAMS.duty_factor
        heights = []
        for i in range(20):
            t = duty + (i / 19.0) * (1.0 - duty) * 0.999
            heights.append(foot_height(t, WALK_PARAMS))
        peak_idx = heights.index(max(heights))
        # Peak should be roughly in the middle
        assert 5 < peak_idx < 15


class TestFootStrideOffset:
    def test_stance_starts_forward(self):
        """At start of stance, foot is at +half_stride."""
        offset = foot_stride_offset(0.0, WALK_PARAMS, speed=1.0)
        half = WALK_PARAMS.stride_length * 0.5
        assert offset == pytest.approx(half, abs=1e-6)

    def test_stance_ends_backward(self):
        """At end of stance, foot is at -half_stride."""
        duty = WALK_PARAMS.duty_factor
        offset = foot_stride_offset(duty - 0.001, WALK_PARAMS, speed=1.0)
        half = WALK_PARAMS.stride_length * 0.5
        assert offset == pytest.approx(-half, abs=0.01)

    def test_swing_returns_to_forward(self):
        """At end of swing, foot should be back at +half_stride."""
        offset = foot_stride_offset(0.999, WALK_PARAMS, speed=1.0)
        half = WALK_PARAMS.stride_length * 0.5
        assert offset == pytest.approx(half, abs=0.02)

    def test_speed_scales_stride(self):
        o1 = foot_stride_offset(0.0, WALK_PARAMS, speed=1.0)
        o2 = foot_stride_offset(0.0, WALK_PARAMS, speed=2.0)
        assert o2 == pytest.approx(o1 * 2.0)


class TestBodyMotion:
    def test_bob_is_bounded(self):
        for phase in [0.0, 0.25, 0.5, 0.75]:
            for params in GAIT_PRESETS.values():
                b = body_bob(phase, params)
                assert abs(b) <= params.body_bob_amplitude + 1e-10

    def test_pitch_is_bounded(self):
        for phase in [0.0, 0.25, 0.5, 0.75]:
            for params in GAIT_PRESETS.values():
                p = body_pitch(phase, params)
                assert abs(p) <= params.body_pitch_amplitude + 1e-10

    def test_gallop_bob_frequency(self):
        """Gallop should have one bob per cycle (sin at 1x freq)."""
        # Bob at phase 0 and 0.5 should have opposite signs
        b0 = body_bob(0.0, GALLOP_PARAMS)
        b25 = body_bob(0.25, GALLOP_PARAMS)
        # sin(0)=0, sin(pi/2)=1 — peak at 0.25
        assert abs(b0) < abs(b25)


class TestComputeFootTarget:
    def test_returns_vec3(self):
        rest = vec3(0, 0, 0)
        target = compute_foot_target(0.0, LegId.FRONT_LEFT, WALK_PARAMS, rest)
        assert target.shape == (3,)

    def test_rest_position_preserved_at_stance_mid(self):
        """At mid-stance, the foot should be near the rest X and Z positions."""
        rest = vec3(-0.12, 0.0, 0.0)
        duty = WALK_PARAMS.duty_factor
        target = compute_foot_target(duty * 0.5, LegId.FRONT_LEFT, WALK_PARAMS, rest)
        assert target[0] == pytest.approx(-0.12)  # X unchanged
        assert target[2] == pytest.approx(0.0)     # On ground during stance

    def test_foot_lifts_during_swing(self):
        rest = vec3(0, 0, 0)
        duty = WALK_PARAMS.duty_factor
        swing_mid = duty + (1.0 - duty) * 0.5
        target = compute_foot_target(swing_mid, LegId.FRONT_LEFT, WALK_PARAMS, rest)
        assert target[2] > 0.0  # Lifted off ground
