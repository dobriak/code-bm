import os
import tempfile

import pytest

from raidio.scanner.walker import scan_library


class TestScanLibrary:
    @pytest.fixture
    def temp_music_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mp3_file = os.path.join(tmpdir, "test.mp3")
            with open(mp3_file, "wb") as f:
                f.write(b"fake mp3 content")
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            with open(os.path.join(subdir, "nested.mp3"), "wb") as f:
                f.write(b"another fake mp3")
            yield tmpdir

    @pytest.mark.asyncio
    async def test_finds_mp3_files(self, temp_music_dir):
        files = [fi async for fi in scan_library(temp_music_dir)]
        assert len(files) == 2
        paths = [fi.absolute_path for fi in files]
        assert any("test.mp3" in p for p in paths)
        assert any("nested.mp3" in p for p in paths)

    @pytest.mark.asyncio
    async def test_yields_file_info(self, temp_music_dir):
        files = [fi async for fi in scan_library(temp_music_dir)]
        for fi in files:
            assert isinstance(fi.absolute_path, str)
            assert fi.file_size > 0
            assert fi.mtime > 0

    @pytest.mark.asyncio
    async def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = [fi async for fi in scan_library(tmpdir)]
            assert len(files) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
