
from raidio.scanner.audio_analysis import filter_passages, parse_silencedetect_output


class TestSilencedetectParser:
    def test_parse_empty(self):
        result = parse_silencedetect_output("")
        assert result == []

    def test_parse_single_silence(self):
        stderr = """
[silencedetect @ 0x7f9a8c] silence_start: 10.5
[silencedetect @ 0x7f9a8c] silence_end: 12.3
"""
        result = parse_silencedetect_output(stderr)
        assert len(result) == 1
        assert result[0]["start_s"] == 10.5
        assert result[0]["end_s"] == 12.3
        assert abs(result[0]["duration_s"] - 1.8) < 0.001

    def test_parse_multiple_silences(self):
        stderr = """
[silencedetect @ 0x7f9a8c] silence_start: 5.0
[silencedetect @ 0x7f9a8c] silence_end: 7.0
[silencedetect @ 0x7f9a8c] silence_start: 30.0
[silencedetect @ 0x7f9a8c] silence_end: 32.0
"""
        result = parse_silencedetect_output(stderr)
        assert len(result) == 2
        assert result[0]["start_s"] == 5.0
        assert result[1]["start_s"] == 30.0

    def test_filter_intro_passage(self):
        passages = [
            {"start_s": 5.0, "end_s": 7.0, "duration_s": 2.0},
        ]
        filtered = filter_passages(passages, 300.0, 1.0)
        assert len(filtered) == 1
        assert filtered[0]["region"] == "intro"

    def test_filter_outro_passage(self):
        passages = [
            {"start_s": 295.0, "end_s": 300.0, "duration_s": 5.0},
        ]
        filtered = filter_passages(passages, 300.0, 1.0)
        assert len(filtered) == 1
        assert filtered[0]["region"] == "outro"

    def test_filter_middle_passage_rejected(self):
        passages = [
            {"start_s": 100.0, "end_s": 110.0, "duration_s": 10.0},
        ]
        filtered = filter_passages(passages, 300.0, 1.0)
        assert len(filtered) == 0

    def test_filter_short_passage_rejected(self):
        passages = [
            {"start_s": 5.0, "end_s": 5.5, "duration_s": 0.5},
        ]
        filtered = filter_passages(passages, 300.0, 1.0)
        assert len(filtered) == 0

    def test_filter_multiple_passages(self):
        passages = [
            {"start_s": 5.0, "end_s": 7.0, "duration_s": 2.0},
            {"start_s": 295.0, "end_s": 300.0, "duration_s": 5.0},
            {"start_s": 100.0, "end_s": 110.0, "duration_s": 10.0},
        ]
        filtered = filter_passages(passages, 300.0, 1.0)
        assert len(filtered) == 2
