from unittest.mock import MagicMock, patch

import pytest

from raidio.scanner.tags import TrackTags, read_tags


class TestReadTags:
    def test_read_tags_returns_empty_on_error(self):
        with patch("raidio.scanner.tags.MutagenFile") as mock_mutagen:
            mock_mutagen.side_effect = Exception("Cannot read file")
            result = read_tags("/nonexistent/file.mp3")
            assert isinstance(result, TrackTags)
            assert result.artist is None
            assert result.title is None

    def test_read_tags_with_mock_audio_not_mp3(self):
        mock_audio = MagicMock()
        mock_audio.tags = {"artist": ["Test Artist"], "title": ["Test Song"]}
        mock_audio.info = MagicMock()
        del mock_audio.info.length
        del mock_audio.info.bitrate
        del mock_audio.info.sample_rate

        with patch("raidio.scanner.tags.MutagenFile", return_value=mock_audio):
            result = read_tags("/fake/path.mp3")
            assert result.artist is not None
            assert result.title is not None


class TestTrackTags:
    def test_track_tags_dataclass(self):
        tags = TrackTags(
            artist="Queen",
            album="A Night at the Opera",
            title="Bohemian Rhapsody",
            genre="Rock",
            year=1975,
            track_number=11,
            disc_number=1,
            duration_ms=354000,
            bitrate_kbps=320,
            sample_rate_hz=44100,
            cover_art_bytes=None,
            cover_art_mime=None,
        )
        assert tags.artist == "Queen"
        assert tags.album == "A Night at the Opera"
        assert tags.title == "Bohemian Rhapsody"
        assert tags.year == 1975


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
