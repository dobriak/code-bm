import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from raidio.db.models import (
    AnalysisStatus,
    Jingle,
    ScanJob,
    ScanKind,
    ScanStatus,
    Track,
)
from raidio.db.settings import get_settings
from raidio.scanner.cover_cache import store_cover
from raidio.scanner.tags import TrackTags, read_tags
from raidio.scanner.walker import FileInfo, scan_library


@dataclass
class ScanProgress:
    phase: str
    total: int
    done: int
    current_path: str
    errors: list[str] = field(default_factory=list)


ScanProgressCallback = AsyncGenerator[ScanProgress, None]


async def compute_file_hash(path: str, size: int) -> str:
    sha = hashlib.sha1()
    with open(path, "rb") as f:
        chunk = await asyncio.to_thread(f.read, 65536)
        sha.update(chunk)
    sha.update(str(size).encode())
    return sha.hexdigest()


async def scan_library_to_db(
    db: AsyncSession,
    path: str | None = None,
    progress_callback: ScanProgressCallback | None = None,
) -> ScanJob:
    settings = get_settings()
    scan_path = path or settings.library_path

    job = ScanJob(
        kind=ScanKind.LIBRARY,
        status=ScanStatus.RUNNING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    all_files: list[FileInfo] = []
    async for fi in scan_library(scan_path):
        all_files.append(fi)

    total = len(all_files)
    job.tracks_added = 0
    job.tracks_updated = 0
    job.tracks_removed = 0
    errors: list[str] = []

    existing_paths: dict[str, Track] = {}
    result = await db.execute(select(Track))
    for track in result.scalars():
        existing_paths[track.path] = track

    scanned_paths: dict[str, str] = {}
    added = 0
    updated = 0

    for i, fi in enumerate(all_files):
        try:
            file_hash = await compute_file_hash(fi.absolute_path, fi.file_size)
            scanned_paths[fi.absolute_path] = file_hash

            tags = await asyncio.to_thread(read_tags, fi.absolute_path)

            if fi.absolute_path in existing_paths:
                existing = existing_paths[fi.absolute_path]
                if existing.file_hash != file_hash:
                    await _update_track(db, existing, tags, file_hash, fi)
                    updated += 1
                else:
                    existing_paths.pop(fi.absolute_path, None)
            else:
                await _insert_track(db, tags, file_hash, fi)
                added += 1

            if i % 50 == 0 or i == total - 1:
                job.tracks_added = added
                job.tracks_updated = updated
                await db.commit()

            if progress_callback:
                await progress_callback.asend(ScanProgress(
                    phase="library",
                    total=total,
                    done=i + 1,
                    current_path=fi.absolute_path,
                    errors=errors[-10:] if len(errors) > 10 else errors,
                ))

        except Exception as e:
            errors.append(f"{fi.absolute_path}: {str(e)}")

    removed = 0
    for path, track in existing_paths.items():
        if track.file_hash not in scanned_paths.values():
            await db.delete(track)
            removed += 1

    job.tracks_added = added
    job.tracks_updated = updated
    job.tracks_removed = removed
    job.status = ScanStatus.COMPLETED
    job.finished_at = datetime.utcnow()
    if errors:
        job.errors_json = json.dumps(errors[-100:])
    await db.commit()

    return job


async def scan_jingles_to_db(
    db: AsyncSession,
    path: str | None = None,
    progress_callback: ScanProgressCallback | None = None,
) -> ScanJob:
    settings = get_settings()
    scan_path = path or settings.jingles_path

    job = ScanJob(
        kind=ScanKind.JINGLES,
        status=ScanStatus.RUNNING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    all_files: list[FileInfo] = []
    async for fi in scan_library(scan_path):
        all_files.append(fi)

    total = len(all_files)
    errors: list[str] = []
    added = 0

    for i, fi in enumerate(all_files):
        try:
            file_hash = await compute_file_hash(fi.absolute_path, fi.file_size)
            tags = await asyncio.to_thread(read_tags, fi.absolute_path)

            result = await db.execute(select(Jingle).where(Jingle.path == fi.absolute_path))
            existing = result.scalar_one_or_none()

            if existing:
                if existing.file_hash != file_hash:
                    await _update_jingle(db, existing, tags, file_hash, fi)
            else:
                await _insert_jingle(db, tags, file_hash, fi)
                added += 1

            if progress_callback:
                await progress_callback.asend(ScanProgress(
                    phase="jingles",
                    total=total,
                    done=i + 1,
                    current_path=fi.absolute_path,
                    errors=errors[-10:] if len(errors) > 10 else errors,
                ))

        except Exception as e:
            errors.append(f"{fi.absolute_path}: {str(e)}")

    job.tracks_added = added
    job.status = ScanStatus.COMPLETED
    job.finished_at = datetime.utcnow()
    if errors:
        job.errors_json = json.dumps(errors[-100:])
    await db.commit()

    return job


async def _insert_track(
    db: AsyncSession,
    tags: TrackTags,
    file_hash: str,
    fi: FileInfo,
) -> Track:
    cover_path = None
    if tags.cover_art_bytes and tags.cover_art_mime:
        cover_path = await asyncio.to_thread(store_cover, tags.cover_art_bytes, tags.cover_art_mime)
        cover_path = str(cover_path)

    track = Track(
        path=fi.absolute_path,
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
        tags_scanned_at=datetime.utcnow(),
        analysis_status=AnalysisStatus.PENDING,
    )
    db.add(track)
    await db.flush()
    return track


async def _update_track(
    db: AsyncSession,
    track: Track,
    tags: TrackTags,
    file_hash: str,
    fi: FileInfo,
) -> Track:
    track.file_hash = file_hash
    track.artist = tags.artist
    track.album = tags.album
    track.title = tags.title
    track.genre = tags.genre
    track.year = tags.year
    track.track_number = tags.track_number
    track.disc_number = tags.disc_number
    track.duration_ms = tags.duration_ms
    track.bitrate_kbps = tags.bitrate_kbps
    track.sample_rate_hz = tags.sample_rate_hz
    track.tags_scanned_at = datetime.utcnow()

    if tags.cover_art_bytes and tags.cover_art_mime:
        cover_path = await asyncio.to_thread(store_cover, tags.cover_art_bytes, tags.cover_art_mime)
        track.cover_art_path = str(cover_path)

    if track.analysis_status == AnalysisStatus.DONE:
        track.analysis_status = AnalysisStatus.PENDING

    await db.flush()
    return track


async def _insert_jingle(
    db: AsyncSession,
    tags: TrackTags,
    file_hash: str,
    fi: FileInfo,
) -> Jingle:
    cover_path = None
    if tags.cover_art_bytes and tags.cover_art_mime:
        cover_path = await asyncio.to_thread(store_cover, tags.cover_art_bytes, tags.cover_art_mime)
        cover_path = str(cover_path)

    jingle = Jingle(
        path=fi.absolute_path,
        file_hash=file_hash,
        title=tags.title or Path(fi.absolute_path).stem,
        duration_ms=tags.duration_ms,
        cover_art_path=cover_path,
    )
    db.add(jingle)
    await db.flush()
    return jingle


async def _update_jingle(
    db: AsyncSession,
    jingle: Jingle,
    tags: TrackTags,
    file_hash: str,
    fi: FileInfo,
) -> Jingle:
    jingle.file_hash = file_hash
    jingle.title = tags.title or Path(fi.absolute_path).stem
    jingle.duration_ms = tags.duration_ms

    if tags.cover_art_bytes and tags.cover_art_mime:
        cover_path = await asyncio.to_thread(store_cover, tags.cover_art_bytes, tags.cover_art_mime)
        jingle.cover_art_path = str(cover_path)

    await db.flush()
    return jingle
