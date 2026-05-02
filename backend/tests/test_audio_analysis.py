"""Unit tests for the silencedetect output parser."""

from __future__ import annotations

import pytest

from raidio.scanner.audio_analysis import (
    filter_quiet_passages,
    parse_silencedetect_output,
)


class TestParseSilencedetectOutput:
    """Tests for parsing ffmpeg silencedetect stderr."""

    def test_basic_silence_regions(self):
        """Parses standard silence_start/silence_end pairs."""
        stderr = """[silencedetect @ 0x55a1b2c3d4e0] silence_start: 0.5
[silencedetect @ 0x55a1b2c3d4e0] silence_end: 3.2 | silence_duration: 2.7
[silencedetect @ 0x55a1b2c3d4e0] silence_start: 240.0
[silencedetect @ 0x55a1b2c3d4e0] silence_end: 243.0 | silence_duration: 3.0
"""
        result = parse_silencedetect_output(stderr)
        assert len(result) == 2
        assert result[0] == {"start": 0.5, "end": 3.2}
        assert result[1] == {"start": 240.0, "end": 243.0}

    def test_no_silence(self):
        """Returns empty list when no silence detected."""
        stderr = "[info] Processing finished\n"
        result = parse_silencedetect_output(stderr)
        assert result == []

    def test_empty_output(self):
        """Returns empty list for empty string."""
        assert parse_silencedetect_output("") == []

    def test_silence_start_without_end(self):
        """Ignores silence_start that has no matching silence_end."""
        stderr = "[silencedetect @ 0x55a1b2c3d4e0] silence_start: 0.5\n"
        result = parse_silencedetect_output(stderr)
        assert result == []

    def test_multiple_silences(self):
        """Parses many silence regions correctly."""
        stderr = ""
        for i in range(5):
            start = i * 10.0
            end = start + 2.5
            stderr += (
                f"[silencedetect @ 0x55a1b2c3d4e0] silence_start: {start}\n"
                f"[silencedetect @ 0x55a1b2c3d4e0] silence_end: {end} "
                f"| silence_duration: 2.5\n"
            )

        result = parse_silencedetect_output(stderr)
        assert len(result) == 5
        for i, silence in enumerate(result):
            assert silence["start"] == pytest.approx(i * 10.0)
            assert silence["end"] == pytest.approx(i * 10.0 + 2.5)


class TestFilterQuietPassages:
    """Tests for filtering silence regions to intro/outro."""

    def test_intro_silence_kept(self):
        """Silence in the first 60s is kept as intro."""
        silences = [{"start": 0.5, "end": 3.5}]
        result = filter_quiet_passages(silences, track_duration_s=300, min_duration_s=2.0)
        assert len(result) == 1
        assert result[0]["region"] == "intro"
        assert result[0]["start_ms"] == 500
        assert result[0]["end_ms"] == 3500
        assert result[0]["duration_ms"] == 3000

    def test_outro_silence_kept(self):
        """Silence in the last 120s is kept as outro."""
        silences = [{"start": 190.0, "end": 195.0}]
        result = filter_quiet_passages(silences, track_duration_s=300, min_duration_s=2.0)
        assert len(result) == 1
        assert result[0]["region"] == "outro"

    def test_middle_silence_discarded(self):
        """Silence in the middle of the track is discarded."""
        silences = [{"start": 100.0, "end": 105.0}]
        result = filter_quiet_passages(silences, track_duration_s=300, min_duration_s=2.0)
        assert len(result) == 0

    def test_short_silence_discarded(self):
        """Silence shorter than min_duration is discarded."""
        silences = [{"start": 0.5, "end": 1.0}]
        result = filter_quiet_passages(silences, track_duration_s=300, min_duration_s=2.0)
        assert len(result) == 0

    def test_exact_min_duration_kept(self):
        """Silence exactly at min_duration is kept."""
        silences = [{"start": 0.5, "end": 2.5}]
        result = filter_quiet_passages(silences, track_duration_s=300, min_duration_s=2.0)
        assert len(result) == 1

    def test_both_intro_and_outro(self):
        """Both intro and outro passages are kept."""
        silences = [
            {"start": 0.5, "end": 3.5},
            {"start": 190.0, "end": 195.0},
        ]
        result = filter_quiet_passages(silences, track_duration_s=300, min_duration_s=2.0)
        assert len(result) == 2
        assert result[0]["region"] == "intro"
        assert result[1]["region"] == "outro"

    def test_empty_silences(self):
        """Empty list returns empty."""
        result = filter_quiet_passages([], 300, 2.0)
        assert result == []
