"""Library scanner — orchestrator for Phase A (tag extraction).

Walks the library directory, reads tags, upserts Track rows,
detects removed files, and reports progress via ScanJob.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from raidio.db.models import AnalysisStatus, ScanJob, ScanKind, ScanStatus, Track
from raidio.scanner.cover_cache import store_cover
from raidio.scanner.tags import read_tags
from raidio.scanner.walker import scan_library

logger = logging.getLogger(__name__)

HASH_CHUNK_SIZE = 64 * 1024  # First 64 KiB


def compute_file_hash(path: str, file_size: int) -> str:
    """Compute SHA-1 of the first 64 KiB + file size for deduplication.

    This is much faster than hashing the entire file and is sufficient
    to detect moves vs. re-encodes.
    """
    h = hashlib.sha1()
    h.update(file_size.to_bytes(8, "little"))
    with open(path, "rb") as f:
        chunk = f.read(HASH_CHUNK_SIZE)
        h.update(chunk)
    return h.hexdigest()


async def run_library_scan(
    session: AsyncSession,
    library_path: str,
    cover_cache_path: str,
    kind: ScanKind = ScanKind.LIBRARY,
) -> ScanJob:
    """Run Phase A scan and return the ScanJob record.

    Walks the directory, reads tags, upserts rows, detects removed files.
    """
    job = ScanJob(
        kind=kind, started_at=datetime.now(tz=UTC).replace(tzinfo=None), status=ScanStatus.RUNNING
    )
    session.add(job)
    await session.flush()

    try:
        files = scan_library(library_path)
        # total files scanned
        added = 0
        updated = 0
        removed = 0

        # Build a set of all discovered paths for removal detection
        seen_paths: set[str] = set()

        # Build a lookup of existing tracks by path
        result = await session.execute(select(Track))
        existing_tracks = {t.path: t for t in result.scalars().all()}

        # Build a set of existing hashes for move detection
        hash_to_paths: dict[str, set[str]] = {}
        for t in existing_tracks.values():
            if t.file_hash:
                hash_to_paths.setdefault(t.file_hash, set()).add(t.path)

        for i, sf in enumerate(files):
            seen_paths.add(sf.path)

            try:
                file_hash = compute_file_hash(sf.path, sf.file_size)
                tags = read_tags(sf.path)

                # Store cover art
                cover_path = store_cover(
                    tags.cover_art_bytes, tags.cover_art_mime, cover_cache_path
                )

                existing = existing_tracks.get(sf.path)

                if existing is not None:
                    # Update if hash changed
                    if existing.file_hash != file_hash:
                        existing.file_hash = file_hash
                        existing.artist = tags.artist
                        existing.album = tags.album
                        existing.title = tags.title
                        existing.genre = tags.genre
                        existing.year = tags.year
                        existing.track_number = tags.track_number
                        existing.disc_number = tags.disc_number
                        existing.duration_ms = tags.duration_ms
                        existing.bitrate_kbps = tags.bitrate_kbps
                        existing.sample_rate_hz = tags.sample_rate_hz
                        existing.cover_art_path = cover_path
                        existing.tags_scanned_at = datetime.now(tz=UTC).replace(tzinfo=None)
                        existing.analysis_status = AnalysisStatus.PENDING
                        existing.analysis_error = None
                        updated += 1
                else:
                    # New file — check if it's a move (same hash, different path)
                    moved_from = None
                    if file_hash in hash_to_paths:
                        for old_path in hash_to_paths[file_hash]:
                            if old_path not in seen_paths:
                                moved_from = old_path
                                break

                    if moved_from and moved_from in existing_tracks:
                        # Update path on existing record
                        old_track = existing_tracks[moved_from]
                        old_track.path = sf.path
                        old_track.file_hash = file_hash
                        old_track.artist = tags.artist
                        old_track.album = tags.album
                        old_track.title = tags.title
                        old_track.genre = tags.genre
                        old_track.year = tags.year
                        old_track.track_number = tags.track_number
                        old_track.disc_number = tags.disc_number
                        old_track.duration_ms = tags.duration_ms
                        old_track.bitrate_kbps = tags.bitrate_kbps
                        old_track.sample_rate_hz = tags.sample_rate_hz
                        old_track.cover_art_path = cover_path
                        old_track.tags_scanned_at = datetime.now(tz=UTC).replace(tzinfo=None)
                        # Remove from hash_to_paths so we don't process it again
                        hash_to_paths[file_hash].discard(moved_from)
                        updated += 1
                    else:
                        # Truly new track
                        track = Track(
                            path=sf.path,
                            file_hash=file_hash,
                            artist=tags.artist,
                            album=tags.album,
                            title=tags.title,
                            genre=tags.genre,
                            year=tags.year,
                            track_number=tags.track_number,
                            disc_number=tags.disc_number,
                            duration_ms=tags.duration_ms,
                            bitrate_kbps=tags.bitrate_kbps,
                            sample_rate_hz=tags.sample_rate_hz,
                            cover_art_path=cover_path,
                            tags_scanned_at=datetime.now(tz=UTC).replace(tzinfo=None),
                            analysis_status=AnalysisStatus.PENDING,
                        )
                        session.add(track)
                        added += 1

                # Commit in batches for performance
                if (i + 1) % 500 == 0:
                    await session.commit()

            except Exception as exc:
                logger.warning("Failed to scan %s: %s", sf.path, exc)
                continue

        # Detect removed files
        for existing_path, track in existing_tracks.items():
            if existing_path not in seen_paths:
                # Check if hash is unique (not a move)
                hash_unique = True
                if track.file_hash and track.file_hash in hash_to_paths:
                    hash_unique = len(hash_to_paths[track.file_hash]) <= 1
                if hash_unique:
                    await session.delete(track)
                    removed += 1

        await session.commit()

        job.tracks_added = added
        job.tracks_updated = updated
        job.tracks_removed = removed
        job.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
        job.status = ScanStatus.DONE

    except Exception as exc:
        logger.error("Scan job %d failed: %s", job.id, exc)
        job.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
        job.status = ScanStatus.ERROR
        job.errors_json = str(exc)

    await session.commit()
    return job
