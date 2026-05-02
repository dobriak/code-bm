"""Cover art cache — deduplicated storage of extracted album art.

Writes to cache/covers/<sha1>.jpg|png. Returns the relative cache path.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def store_cover(
    data: bytes,
    mime: str | None,
    cache_dir: str | Path,
) -> str | None:
    """Write cover art bytes to the cache, deduplicated by SHA-1 hash.

    Args:
        data: Raw image bytes.
        mime: MIME type (e.g., 'image/jpeg', 'image/png').
        cache_dir: Path to the cache directory.

    Returns:
        Relative path like 'cache/covers/abc123.jpg', or None if data is empty.
    """
    if not data:
        return None

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    # Determine extension from MIME
    ext = _mime_to_ext(mime)
    sha1 = hashlib.sha1(data).hexdigest()
    filename = f"{sha1}{ext}"
    full_path = cache_path / filename

    # Only write if not already cached (dedup by hash)
    if not full_path.exists():
        full_path.write_bytes(data)

    return str(full_path)


def _mime_to_ext(mime: str | None) -> str:
    """Map a MIME type to a file extension."""
    if mime == "image/png":
        return ".png"
    if mime == "image/gif":
        return ".gif"
    if mime == "image/webp":
        return ".webp"
    return ".jpg"  # Default to JPEG
