"""Tests for the motion presets."""

import pytest

from deer_me.api.deer import Deer
from deer_me.api.presets import (
    approach_and_graze,
    flee,
    graze,
    look_around,
    patrol,
    startle,
)
from deer_me.api.sequence import Sequence
from deer_me.core.types import Pose


class TestPresets:
    @pytest.fixture
    def seq(self):
        return Sequence(Deer())

    def test_graze_adds_commands(self, seq):
        seq.at(0)
        graze(seq, duration_frames=120)
        assert len(seq.commands) >= 2  # walk + idle at minimum

    def test_startle_adds_commands(self, seq):
        seq.at(0)
        startle(seq, pause_frames=18)
        assert len(seq.commands) >= 1

    def test_flee_adds_commands(self, seq):
        seq.at(0)
        flee(seq, duration_frames=96)
        assert len(seq.commands) >= 3  # walk + trot + gallop

    def test_look_around_adds_commands(self, seq):
        seq.at(0)
        look_around(seq, duration_frames=96)
        assert len(seq.commands) >= 3  # turn_left + turn_right + idle

    def test_patrol_adds_commands(self, seq):
        seq.at(0)
        patrol(seq, duration_frames=240)
        assert len(seq.commands) >= 4

    def test_approach_and_graze_adds_commands(self, seq):
        seq.at(0)
        approach_and_graze(seq, duration_frames=240)
        assert len(seq.commands) >= 4

    def test_graze_bakes_successfully(self, seq):
        seq.at(0)
        graze(seq, duration_frames=60)
        frames = seq.bake(extra_frames=12)
        assert len(frames) > 0
        for _, pose in frames:
            assert isinstance(pose, Pose)

    def test_flee_bakes_successfully(self, seq):
        seq.at(0)
        flee(seq, duration_frames=96)
        frames = seq.bake(extra_frames=12)
        assert len(frames) > 0

    def test_patrol_bakes_successfully(self, seq):
        seq.at(0)
        patrol(seq, duration_frames=120)
        frames = seq.bake(extra_frames=12)
        assert len(frames) > 0

    def test_presets_are_chainable(self, seq):
        """Presets should be chainable on a single sequence."""
        seq.at(0)
        graze(seq, duration_frames=60)
        startle(seq, pause_frames=12)
        flee(seq, duration_frames=48)
        frames = seq.bake(extra_frames=12)
        assert len(frames) > 0

    def test_presets_return_sequence(self, seq):
        """All presets should return the sequence for chaining."""
        result = graze(seq.at(0), duration_frames=60)
        assert result is seq
        result = startle(seq, pause_frames=12)
        assert result is seq
        result = flee(seq, duration_frames=48)
        assert result is seq
        result = look_around(seq, duration_frames=48)
        assert result is seq
        result = patrol(seq, duration_frames=120)
        assert result is seq
        result = approach_and_graze(seq, duration_frames=120)
        assert result is seq
