"""Tag reader — extract audio metadata from MP3 files using Mutagen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mutagen.mp3 import MP3, EasyMP3


@dataclass(frozen=True, slots=True)
class TrackTags:
    """Extracted metadata from an audio file."""

    artist: str | None = None
    album: str | None = None
    title: str | None = None
    genre: str | None = None
    year: int | None = None
    track_number: int | None = None
    disc_number: int | None = None
    duration_ms: int | None = None
    bitrate_kbps: int | None = None
    sample_rate_hz: int | None = None
    cover_art_bytes: bytes | None = None
    cover_art_mime: str | None = None


def read_tags(path: str) -> TrackTags:
    """Read ID3 tags and stream info from an MP3 file.

    Args:
        path: Absolute path to the MP3 file.

    Returns:
        TrackTags with all extracted metadata.

    Raises:
        MutagenError: If the file cannot be parsed.
        FileNotFoundError: If the file does not exist.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    audio = MP3(str(p))
    info = audio.info

    # Stream info
    duration_ms = int(info.length * 1000) if info.length else None
    bitrate_kbps = info.bitrate // 1000 if info.bitrate else None
    sample_rate_hz = info.sample_rate if info.sample_rate else None

    # Use EasyID3 for simplified tag access
    tags: TrackTags = TrackTags(
        duration_ms=duration_ms,
        bitrate_kbps=bitrate_kbps,
        sample_rate_hz=sample_rate_hz,
    )

    try:
        easy = EasyMP3(str(p))

        # Simple text tags
        if "artist" in easy:
            tags = _replace(tags, artist=_first(easy["artist"]))
        if "album" in easy:
            tags = _replace(tags, album=_first(easy["album"]))
        if "title" in easy:
            tags = _replace(tags, title=_first(easy["title"]))
        if "genre" in easy:
            tags = _replace(tags, genre=_first(easy["genre"]))
        if "date" in easy:
            tags = _replace(tags, year=_parse_int(_first(easy["date"])))
        if "tracknumber" in easy:
            tags = _replace(tags, track_number=_parse_track_number(_first(easy["tracknumber"])))
        if "discnumber" in easy:
            tags = _replace(tags, disc_number=_parse_int(_first(easy["discnumber"])))
    except Exception:
        # If EasyMP3 fails, we still have stream info from MP3()
        pass

    # Cover art — extract from full ID3 tags
    cover_bytes, cover_mime = _extract_cover_art(audio)
    if cover_bytes:
        tags = _replace(tags, cover_art_bytes=cover_bytes, cover_art_mime=cover_mime)

    return tags


def _replace(tags: TrackTags, **kwargs) -> TrackTags:
    """Create a new TrackTags with some fields replaced."""
    return TrackTags(
        artist=kwargs.get("artist", tags.artist),
        album=kwargs.get("album", tags.album),
        title=kwargs.get("title", tags.title),
        genre=kwargs.get("genre", tags.genre),
        year=kwargs.get("year", tags.year),
        track_number=kwargs.get("track_number", tags.track_number),
        disc_number=kwargs.get("disc_number", tags.disc_number),
        duration_ms=kwargs.get("duration_ms", tags.duration_ms),
        bitrate_kbps=kwargs.get("bitrate_kbps", tags.bitrate_kbps),
        sample_rate_hz=kwargs.get("sample_rate_hz", tags.sample_rate_hz),
        cover_art_bytes=kwargs.get("cover_art_bytes", tags.cover_art_bytes),
        cover_art_mime=kwargs.get("cover_art_mime", tags.cover_art_mime),
    )


def _first(values: list[str]) -> str | None:
    """Return the first value in a list, or None."""
    return values[0] if values else None


def _parse_int(value: str | None) -> int | None:
    """Parse a string to int, returning None on failure."""
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        # Try extracting just the first digits (e.g., "2024-01-15")
        import re

        match = re.match(r"(\d+)", value)
        return int(match.group(1)) if match else None


def _parse_track_number(value: str | None) -> int | None:
    """Parse track number, handling formats like '1/12'."""
    if not value:
        return None
    try:
        return int(value.split("/")[0])
    except (ValueError, TypeError, IndexError):
        return None


def _extract_cover_art(audio: MP3) -> tuple[bytes | None, str | None]:
    """Extract cover art from ID3 APIC frames.

    Returns (bytes, mime_type) or (None, None) if no cover art found.
    """
    from mutagen.id3 import APIC

    for tag in audio.tags.values():
        if isinstance(tag, APIC):
            return tag.data, tag.mime

    return None, None
