"""Tests for the high-level Deer animator API."""

import numpy as np
import pytest

from deer_me.api.deer import Deer
from deer_me.core.state_machine import LocoState
from deer_me.core.types import Pose


class TestDeerBasics:
    def test_initial_state(self):
        deer = Deer()
        assert deer.state == LocoState.IDLE
        assert deer.speed == 0.0
        assert deer.time == 0.0

    def test_walk(self):
        deer = Deer()
        assert deer.walk(speed=1.0) is True
        assert deer.is_transitioning is True

    def test_trot(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        assert deer.trot(speed=1.3) is True

    def test_gallop_from_idle_fails(self):
        deer = Deer()
        assert deer.gallop() is False

    def test_gallop_from_trot_succeeds(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        deer.trot()
        deer.update(0.5)
        assert deer.gallop() is True

    def test_idle_from_gallop_fails(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        deer.trot()
        deer.update(0.5)
        deer.gallop()
        deer.update(0.6)
        assert deer.can_idle() is False

    def test_turn(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        assert deer.turn_left() is True
        deer.update(0.3)
        assert deer.state == LocoState.TURN_LEFT


class TestDeerUpdate:
    def test_update_advances_time(self):
        deer = Deer()
        deer.update(1.0)
        assert deer.time == pytest.approx(1.0)

    def test_advance_frames(self):
        deer = Deer(fps=24.0)
        deer.advance_frames(24)
        assert deer.time == pytest.approx(1.0)

    def test_pose_returns_pose(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        p = deer.pose()
        assert isinstance(p, Pose)
        assert len(p.joints) > 0

    def test_poses_change_over_time(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)

        p1 = deer.pose()
        deer.update(0.3)
        p2 = deer.pose()

        any_differ = False
        for name in p1.joints:
            if name in p2.joints:
                a = p1.joints[name].rotation.to_array()
                b = p2.joints[name].rotation.to_array()
                if not np.allclose(a, b, atol=1e-6):
                    any_differ = True
                    break
        assert any_differ


class TestDeerReset:
    def test_reset_returns_to_idle(self):
        deer = Deer()
        deer.walk()
        deer.update(1.0)
        deer.reset()
        assert deer.state == LocoState.IDLE
        assert deer.time == 0.0
        assert deer.speed == 0.0


class TestDeerQueries:
    def test_can_gallop_from_idle(self):
        deer = Deer()
        assert deer.can_gallop() is False

    def test_can_gallop_from_trot(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        deer.trot()
        deer.update(0.5)
        assert deer.can_gallop() is True

    def test_can_idle_from_walk(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        assert deer.can_idle() is True

    def test_cycle_phase_in_range(self):
        deer = Deer()
        deer.walk()
        for _ in range(100):
            deer.update(0.05)
        assert 0.0 <= deer.cycle_phase < 1.0


class TestGenerateFrames:
    def test_returns_correct_count(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        frames = deer.generate_frames(48)
        assert len(frames) == 48

    def test_frame_numbers(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        frames = deer.generate_frames(10, start_frame=5)
        assert frames[0][0] == 5
        assert frames[-1][0] == 14

    def test_each_frame_is_a_pose(self):
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        frames = deer.generate_frames(10)
        for frame_num, pose in frames:
            assert isinstance(frame_num, int)
            assert isinstance(pose, Pose)
