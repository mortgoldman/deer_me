"""Tests for the timeline sequencer."""

import pytest

from deer_me.api.deer import Deer
from deer_me.api.sequence import Sequence
from deer_me.core.state_machine import LocoState
from deer_me.core.types import Pose


class TestSequenceBuilder:
    def test_empty_sequence(self):
        seq = Sequence(Deer())
        assert seq.end_frame == 0
        assert len(seq.commands) == 0

    def test_at_sets_cursor(self):
        seq = Sequence(Deer())
        result = seq.at(100)
        assert result is seq  # Returns self for chaining

    def test_walk_command(self):
        seq = Sequence(Deer())
        seq.at(0).walk(speed=1.0)
        assert len(seq.commands) == 1
        assert seq.commands[0].frame == 0

    def test_chaining(self):
        seq = Sequence(Deer())
        seq.at(0).walk().at(120).trot().at(240).idle()
        assert len(seq.commands) == 3
        frames = [c.frame for c in seq.commands]
        assert frames == [0, 120, 240]

    def test_hold_advances_cursor(self):
        seq = Sequence(Deer())
        seq.at(0).walk().hold(60).trot()
        cmds = seq.commands
        assert cmds[0].frame == 0    # walk
        assert cmds[1].frame == 60   # trot

    def test_end_frame(self):
        seq = Sequence(Deer())
        seq.at(0).walk().at(120).trot().at(240).idle()
        assert seq.end_frame == 240

    def test_all_command_types(self):
        seq = Sequence(Deer())
        seq.at(0).walk()
        seq.at(24).trot()
        seq.at(48).gallop()
        seq.at(72).turn_left()
        seq.at(96).turn_right()
        seq.at(120).idle()
        assert len(seq.commands) == 6


class TestSequenceBake:
    def test_bake_empty(self):
        seq = Sequence(Deer())
        frames = seq.bake(extra_frames=0)
        assert frames == []

    def test_bake_walk(self):
        seq = Sequence(Deer())
        seq.at(1).walk()
        frames = seq.bake(extra_frames=24)
        assert len(frames) == 25  # frame 1 + 24 extra
        for frame_num, pose in frames:
            assert isinstance(pose, Pose)

    def test_bake_resets_deer(self):
        deer = Deer()
        deer.walk()
        deer.update(5.0)

        seq = Sequence(deer)
        seq.at(1).walk()
        seq.bake(extra_frames=10)

        # After bake, deer should have been reset and replayed
        assert deer.time > 0  # Advanced through the baked frames

    def test_bake_multi_command(self):
        seq = Sequence(Deer())
        seq.at(1).walk(speed=1.0)
        seq.at(49).trot(speed=1.5)
        seq.at(97).idle()
        frames = seq.bake(extra_frames=24)

        # Should have frames from 1 through 97+24=121
        assert len(frames) == 121
        assert frames[0][0] == 1
        assert frames[-1][0] == 121

    def test_bake_gait_changes_visible(self):
        """Verify that gait transitions produce different poses over time."""
        seq = Sequence(Deer())
        seq.at(1).walk(speed=1.0)
        seq.at(49).trot(speed=1.5)
        frames = seq.bake(extra_frames=48)

        # Compare a frame during walk vs during trot
        _, walk_pose = frames[10]   # Frame 11, during walk
        _, trot_pose = frames[70]   # Frame 71, during trot

        # They should differ in some joint rotations
        any_differ = False
        for name in walk_pose.joints:
            if name in trot_pose.joints:
                a = walk_pose.joints[name].rotation.to_array()
                b = trot_pose.joints[name].rotation.to_array()
                import numpy as np
                if not np.allclose(a, b, atol=1e-4):
                    any_differ = True
                    break
        assert any_differ


class TestSequenceDescribe:
    def test_describe_returns_string(self):
        seq = Sequence(Deer())
        seq.at(0).walk().at(120).idle()
        desc = seq.describe()
        assert isinstance(desc, str)
        assert "walk" in desc
        assert "idle" in desc
        assert "frame" in desc

    def test_describe_empty(self):
        seq = Sequence(Deer())
        desc = seq.describe()
        assert "0 commands" in desc
