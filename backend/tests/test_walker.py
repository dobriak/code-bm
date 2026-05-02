"""Unit tests for the scanner walker."""

import os

import pytest

from raidio.scanner.walker import ScannedFile, _is_mp3, scan_library


class TestIsMp3:
    def test_mp3_extension(self):
        assert _is_mp3("song.mp3")

    def test_mpeg_extension(self):
        assert _is_mp3("song.mpeg")

    def test_mpga_extension(self):
        assert _is_mp3("song.mpga")

    def test_uppercase_extension(self):
        assert _is_mp3("SONG.MP3")

    def test_non_mp3(self):
        assert not _is_mp3("song.flac")
        assert not _is_mp3("song.wav")
        assert not _is_mp3("song.txt")


class TestScanLibrary:
    @pytest.fixture
    def music_dir(self, tmp_path):
        """Create a temporary directory with some MP3 files."""
        (tmp_path / "album1").mkdir()
        (tmp_path / "album1" / "track1.mp3").write_bytes(b"fake mp3 data")
        (tmp_path / "album1" / "track2.mp3").write_bytes(b"fake mp3 data 2")
        (tmp_path / "album2").mkdir()
        (tmp_path / "album2" / "song.mp3").write_bytes(b"fake mp3 data 3")
        # Non-MP3 file should be ignored
        (tmp_path / "album1" / "cover.jpg").write_bytes(b"fake image")
        return tmp_path

    async def test_finds_all_mp3s(self, music_dir):
        files = await scan_library(str(music_dir))
        paths = [f.path for f in files]
        assert len(files) == 3
        assert any("track1.mp3" in p for p in paths)
        assert any("track2.mp3" in p for p in paths)
        assert any("song.mp3" in p for p in paths)

    async def test_ignores_non_mp3s(self, music_dir):
        files = await scan_library(str(music_dir))
        paths = [f.path for f in files]
        assert not any("cover.jpg" in p for p in paths)

    async def test_returns_correct_metadata(self, music_dir):
        files = await scan_library(str(music_dir))
        for f in files:
            assert isinstance(f, ScannedFile)
            assert f.file_size > 0
            assert f.mtime > 0
            assert os.path.isabs(f.path)

    async def test_nonexistent_directory(self):
        with pytest.raises(FileNotFoundError):
            await scan_library("/nonexistent/directory/path")

    async def test_empty_directory(self, tmp_path):
        files = await scan_library(str(tmp_path))
        assert files == []
