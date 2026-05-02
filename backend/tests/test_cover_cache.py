"""Unit tests for cover art cache."""

import os
from pathlib import Path

from raidio.scanner.cover_cache import _mime_to_ext, store_cover


class TestMimeToExt:
    def test_jpeg(self):
        assert _mime_to_ext("image/jpeg") == ".jpg"

    def test_jpg(self):
        assert _mime_to_ext("image/jpg") == ".jpg"

    def test_png(self):
        assert _mime_to_ext("image/png") == ".png"

    def test_gif(self):
        assert _mime_to_ext("image/gif") == ".gif"

    def test_webp(self):
        assert _mime_to_ext("image/webp") == ".webp"

    def test_none(self):
        assert _mime_to_ext(None) == ".jpg"

    def test_unknown(self):
        assert _mime_to_ext("image/svg+xml") == ".jpg"


class TestStoreCover:
    def test_store_and_retrieve(self, tmp_path):
        data = b"fake cover art data"
        result = store_cover(data, "image/jpeg", tmp_path)

        assert result is not None
        assert os.path.exists(result)
        assert Path(result).read_bytes() == data

    def test_deduplication(self, tmp_path):
        """Same data should not create a duplicate file."""
        data = b"identical cover data"

        result1 = store_cover(data, "image/jpeg", tmp_path)
        result2 = store_cover(data, "image/jpeg", tmp_path)

        assert result1 == result2

    def test_different_mime_same_data(self, tmp_path):
        """Different MIME types with same data get different files."""
        data = b"same data different mime"

        result1 = store_cover(data, "image/jpeg", tmp_path)
        result2 = store_cover(data, "image/png", tmp_path)

        # Extensions differ but content is the same (both written)
        assert result1.endswith(".jpg")
        assert result2.endswith(".png")

    def test_empty_data(self, tmp_path):
        result = store_cover(b"", "image/jpeg", tmp_path)
        assert result is None

    def test_creates_directory(self, tmp_path):
        nested = tmp_path / "nested" / "dir"
        data = b"test data"
        result = store_cover(data, "image/png", nested)
        assert result is not None
        assert os.path.exists(result)
