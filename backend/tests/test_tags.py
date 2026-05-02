"""Unit tests for the tag reader."""

import pytest

from raidio.scanner.tags import TrackTags, _parse_int, _parse_track_number, read_tags


class TestParseInt:
    def test_simple_int(self):
        assert _parse_int("2024") == 2024

    def test_none(self):
        assert _parse_int(None) is None

    def test_empty(self):
        assert _parse_int("") is None

    def test_iso_date(self):
        assert _parse_int("2024-01-15") == 2024

    def test_non_numeric(self):
        assert _parse_int("abc") is None


class TestParseTrackNumber:
    def test_simple(self):
        assert _parse_track_number("5") == 5

    def test_with_total(self):
        assert _parse_track_number("5/12") == 5

    def test_none(self):
        assert _parse_track_number(None) is None

    def test_empty(self):
        assert _parse_track_number("") is None

    def test_non_numeric(self):
        assert _parse_track_number("abc") is None


class TestReadTags:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_tags("/nonexistent/path/to/file.mp3")

    def test_invalid_file(self, tmp_path):
        """Non-MP3 file should raise an error from Mutagen."""
        fake = tmp_path / "not_an_mp3.mp3"
        fake.write_bytes(b"this is not an mp3 file at all")

        # Mutagen may raise various errors for invalid files
        with pytest.raises((OSError, ValueError, Exception)):
            read_tags(str(fake))


class TestTrackTags:
    def test_default_values(self):
        tags = TrackTags()
        assert tags.artist is None
        assert tags.album is None
        assert tags.title is None
        assert tags.duration_ms is None
        assert tags.cover_art_bytes is None

    def test_immutable(self):
        tags = TrackTags(artist="Test")
        # TrackTags is frozen, so assignment should fail
        with pytest.raises(AttributeError):
            tags.artist = "Changed"  # type: ignore[misc]
