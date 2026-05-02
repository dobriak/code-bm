"""Catalog read API — public endpoints for browsing and searching tracks.

All endpoints are unauthenticated (no auth until Phase 4).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select, text

from raidio.db.fts import fts_query
from raidio.db.models import Jingle, Track

router = APIRouter(prefix="/api/v1", tags=["catalog"])


# ── Schemas ────────────────────────────────────────────────────────


class TrackBrief(BaseModel):
    id: int
    artist: str | None
    album: str | None
    title: str | None
    genre: str | None
    year: int | None
    track_number: int | None
    duration_ms: int | None
    cover_art_path: str | None
    analysis_status: str


class TrackDetail(TrackBrief):
    path: str
    file_hash: str | None
    disc_number: int | None
    bitrate_kbps: int | None
    sample_rate_hz: int | None
    tags_scanned_at: str | None
    audio_analyzed_at: str | None
    analysis_error: str | None
    quiet_passages: list[dict]


class PaginatedTracks(BaseModel):
    items: list[TrackBrief]
    next_cursor: str | None
    total: int


class FacetItem(BaseModel):
    name: str
    count: int


class JingleBrief(BaseModel):
    id: int
    path: str
    title: str | None
    duration_ms: int | None
    cover_art_path: str | None


# ── Dependencies ───────────────────────────────────────────────────


def _get_session():
    from raidio.db.session import get_session_factory

    return get_session_factory()


# ── Track endpoints ────────────────────────────────────────────────


@router.get("/tracks", response_model=PaginatedTracks)
async def list_tracks(
    q: Annotated[str | None, Query(description="FTS5 search query")] = None,
    artist: Annotated[str | None, Query()] = None,
    album: Annotated[str | None, Query()] = None,
    genre: Annotated[str | None, Query()] = None,
    year_from: Annotated[int | None, Query()] = None,
    year_to: Annotated[int | None, Query()] = None,
    duration_min: Annotated[int | None, Query(description="Duration in ms")] = None,
    duration_max: Annotated[int | None, Query(description="Duration in ms")] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=100)] = 50,
):
    """Search and browse tracks with cursor-based pagination."""
    factory = _get_session()
    async with factory() as session:
        # Build WHERE clauses
        conditions = []
        params: dict = {}

        # FTS5 search — join with tracks_fts to get matching rowids
        fts_join = ""
        if q:
            fts_expr = fts_query(q)
            fts_join = " INNER JOIN tracks_fts ON tracks.id = tracks_fts.rowid "
            conditions.append("tracks_fts MATCH :fts_expr")
            params["fts_expr"] = fts_expr

        if artist:
            conditions.append("tracks.artist = :artist")
            params["artist"] = artist
        if album:
            conditions.append("tracks.album = :album")
            params["album"] = album
        if genre:
            conditions.append("tracks.genre = :genre")
            params["genre"] = genre
        if year_from is not None:
            conditions.append("tracks.year >= :year_from")
            params["year_from"] = year_from
        if year_to is not None:
            conditions.append("tracks.year <= :year_to")
            params["year_to"] = year_to
        if duration_min is not None:
            conditions.append("tracks.duration_ms >= :duration_min")
            params["duration_min"] = duration_min
        if duration_max is not None:
            conditions.append("tracks.duration_ms <= :duration_max")
            params["duration_max"] = duration_max

        # Cursor pagination
        if cursor:
            parts = cursor.split("|")
            if len(parts) == 4:
                c_artist, c_album, c_track_num, c_id = parts
                conditions.append(
                    "(tracks.artist > :c_artist"
                    " OR (tracks.artist = :c_artist AND tracks.album > :c_album)"
                    " OR (tracks.artist = :c_artist AND tracks.album = :c_album"
                    "     AND tracks.track_number > :c_track_num)"
                    " OR (tracks.artist = :c_artist AND tracks.album = :c_album"
                    "     AND tracks.track_number = :c_track_num"
                    "     AND tracks.id > :c_id))"
                )
                params.update(
                    c_artist=c_artist,
                    c_album=c_album,
                    c_track_num=int(c_track_num),
                    c_id=int(c_id),
                )

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_sql = f"SELECT COUNT(*) FROM tracks {fts_join} WHERE {where_clause}"
        total = (await session.execute(text(count_sql), params)).scalar() or 0

        # Fetch items (one extra for next-page detection)
        fetch_limit = limit + 1
        fetch_sql = (
            f"SELECT * FROM tracks {fts_join} WHERE {where_clause} "
            f"ORDER BY tracks.artist, tracks.album, tracks.track_number, tracks.id "
            f"LIMIT :fetch_limit"
        )
        params["fetch_limit"] = fetch_limit

        result = await session.execute(text(fetch_sql), params)
        rows = result.mappings().all()

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = (
                f"{last['artist'] or ''}|{last['album'] or ''}"
                f"|{last['track_number'] or 0}|{last['id']}"
            )

        return PaginatedTracks(
            items=[
                TrackBrief(
                    id=t["id"],
                    artist=t["artist"],
                    album=t["album"],
                    title=t["title"],
                    genre=t["genre"],
                    year=t["year"],
                    track_number=t["track_number"],
                    duration_ms=t["duration_ms"],
                    cover_art_path=t["cover_art_path"],
                    analysis_status=t["analysis_status"],
                )
                for t in items
            ],
            next_cursor=next_cursor,
            total=total,
        )


class RandomTrackSchema(BaseModel):
    id: int
    artist: str | None
    title: str | None
    album: str | None
    duration_ms: int | None
    cover_art_path: str | None


@router.get("/tracks/random", response_model=RandomTrackSchema)
async def random_track():
    """Return a uniformly random track from the library."""
    factory = _get_session()
    async with factory() as session:
        stmt = select(Track).order_by(func.random()).limit(1)
        result = await session.execute(stmt)
        track = result.scalar_one_or_none()
        if not track:
            raise HTTPException(status_code=404, detail="No tracks in library")

        return RandomTrackSchema(
            id=track.id,
            artist=track.artist,
            title=track.title,
            album=track.album,
            duration_ms=track.duration_ms,
            cover_art_path=track.cover_art_path,
        )


@router.get("/tracks/{track_id}", response_model=TrackDetail)
async def get_track(track_id: int):
    """Get full track detail including quiet passages."""
    factory = _get_session()
    async with factory() as session:
        result = await session.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        return TrackDetail(
            id=track.id,
            artist=track.artist,
            album=track.album,
            title=track.title,
            genre=track.genre,
            year=track.year,
            track_number=track.track_number,
            duration_ms=track.duration_ms,
            cover_art_path=track.cover_art_path,
            analysis_status=track.analysis_status.value,
            path=track.path,
            file_hash=track.file_hash,
            disc_number=track.disc_number,
            bitrate_kbps=track.bitrate_kbps,
            sample_rate_hz=track.sample_rate_hz,
            tags_scanned_at=track.tags_scanned_at.isoformat() if track.tags_scanned_at else None,
            audio_analyzed_at=(
                track.audio_analyzed_at.isoformat() if track.audio_analyzed_at else None
            ),
            analysis_error=track.analysis_error,
            quiet_passages=[
                {
                    "id": qp.id,
                    "start_ms": qp.start_ms,
                    "end_ms": qp.end_ms,
                    "duration_ms": qp.duration_ms,
                    "region": qp.region.value,
                }
                for qp in track.quiet_passages
            ],
        )


@router.get("/tracks/{track_id}/cover")
async def get_track_cover(track_id: int):
    """Stream cover art from the cache directory."""
    factory = _get_session()
    async with factory() as session:
        result = await session.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()
        if not track or not track.cover_art_path:
            raise HTTPException(status_code=404, detail="No cover art")

    from pathlib import Path

    cover = Path(track.cover_art_path)
    if not cover.is_file():
        raise HTTPException(status_code=404, detail="Cover file missing")

    return FileResponse(str(cover))


# ── Facet endpoints ────────────────────────────────────────────────


@router.get("/artists", response_model=list[FacetItem])
async def list_artists():
    """List all artists with track counts."""
    factory = _get_session()
    async with factory() as session:
        result = await session.execute(
            select(Track.artist, func.count().label("cnt"))
            .where(Track.artist.isnot(None))
            .group_by(Track.artist)
            .order_by(func.count().desc())
        )
        return [FacetItem(name=row[0], count=row[1]) for row in result.all()]


@router.get("/albums", response_model=list[FacetItem])
async def list_albums():
    """List all albums with track counts."""
    factory = _get_session()
    async with factory() as session:
        result = await session.execute(
            select(Track.album, func.count().label("cnt"))
            .where(Track.album.isnot(None))
            .group_by(Track.album)
            .order_by(func.count().desc())
        )
        return [FacetItem(name=row[0], count=row[1]) for row in result.all()]


@router.get("/genres", response_model=list[FacetItem])
async def list_genres():
    """List all genres with track counts."""
    factory = _get_session()
    async with factory() as session:
        result = await session.execute(
            select(Track.genre, func.count().label("cnt"))
            .where(Track.genre.isnot(None))
            .group_by(Track.genre)
            .order_by(func.count().desc())
        )
        return [FacetItem(name=row[0], count=row[1]) for row in result.all()]


# ── Jingles endpoint ───────────────────────────────────────────────


@router.get("/jingles", response_model=list[JingleBrief])
async def list_jingles():
    """List all jingles."""
    factory = _get_session()
    async with factory() as session:
        result = await session.execute(select(Jingle).order_by(Jingle.id))
        return [
            JingleBrief(
                id=j.id,
                path=j.path,
                title=j.title,
                duration_ms=j.duration_ms,
                cover_art_path=j.cover_art_path,
            )
            for j in result.scalars().all()
        ]
