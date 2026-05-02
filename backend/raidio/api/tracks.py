from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from raidio.db.fts import fts_query
from raidio.db.models import Jingle, Track

router = APIRouter()


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        yield session


@router.get("/tracks")
async def list_tracks(
    request: Request,
    q: str | None = Query(None, description="Search query"),
    artist: str | None = Query(None),
    album: str | None = Query(None),
    genre: str | None = Query(None),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    duration_min: int | None = Query(None),
    duration_max: int | None = Query(None),
    cursor: str | None = Query(None, description="Base64 encoded cursor"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(Track)
    count_query = select(func.count(Track.id))

    if q:
        fts = fts_query(q)
        fts_where = f"id IN (SELECT rowid FROM tracks_fts WHERE tracks_fts MATCH '{fts}')"
        query = query.where(text(fts_where))
        count_query = count_query.where(text(fts_where))

    if artist:
        query = query.where(Track.artist == artist)
        count_query = count_query.where(Track.artist == artist)
    if album:
        query = query.where(Track.album == album)
        count_query = count_query.where(Track.album == album)
    if genre:
        query = query.where(Track.genre == genre)
        count_query = count_query.where(Track.genre == genre)
    if year_from is not None:
        query = query.where(Track.year >= year_from)
        count_query = count_query.where(Track.year >= year_from)
    if year_to is not None:
        query = query.where(Track.year <= year_to)
        count_query = count_query.where(Track.year <= year_to)
    if duration_min is not None:
        query = query.where(Track.duration_ms >= duration_min * 1000)
        count_query = count_query.where(Track.duration_ms >= duration_min * 1000)
    if duration_max is not None:
        query = query.where(Track.duration_ms <= duration_max * 1000)
        count_query = count_query.where(Track.duration_ms <= duration_max * 1000)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    if cursor:
        cursor_data = _decode_cursor(cursor)
        if cursor_data:
            query = query.where(
                (Track.artist, Track.album, Track.track_number, Track.id) > cursor_data
            )

    query = query.order_by(Track.artist, Track.album, Track.track_number, Track.id)
    query = query.limit(limit)

    result = await db.execute(query)
    tracks = result.scalars().all()

    return {
        "tracks": [_track_to_dict(t) for t in tracks],
        "total": total,
        "next_cursor": _encode_cursor(tracks[-1]) if len(tracks) == limit else None,
    }


def _track_to_dict(track: Track) -> dict[str, Any]:
    return {
        "id": track.id,
        "path": track.path,
        "artist": track.artist,
        "album": track.album,
        "title": track.title,
        "genre": track.genre,
        "year": track.year,
        "track_number": track.track_number,
        "disc_number": track.disc_number,
        "duration_ms": track.duration_ms,
        "bitrate_kbps": track.bitrate_kbps,
        "sample_rate_hz": track.sample_rate_hz,
        "analysis_status": track.analysis_status.value if track.analysis_status else None,
        "cover_art_path": track.cover_art_path,
    }


def _encode_cursor(track: Track) -> str | None:
    import base64
    import json

    data = [track.artist, track.album, track.track_number, track.id]
    return base64.b64encode(json.dumps(data).encode()).decode()


def _decode_cursor(cursor: str) -> tuple | None:
    import base64
    import json

    try:
        data = json.loads(base64.b64decode(cursor.encode()).decode())
        return tuple(data)
    except Exception:
        return None


@router.get("/tracks/{track_id}")
async def get_track(
    track_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Track)
        .options(selectinload(Track.quiet_passages))
        .where(Track.id == track_id)
    )
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    return {
        **_track_to_dict(track),
        "quiet_passages": [
            {
                "id": qp.id,
                "start_ms": qp.start_ms,
                "end_ms": qp.end_ms,
                "duration_ms": qp.duration_ms,
                "region": qp.region.value if qp.region else None,
            }
            for qp in track.quiet_passages
        ],
    }


@router.get("/tracks/{track_id}/cover")
async def get_track_cover(
    track_id: int,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if not track.cover_art_path:
        raise HTTPException(status_code=404, detail="No cover art")

    return FileResponse(track.cover_art_path)


@router.get("/artists")
async def list_artists(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Track.artist, func.count(Track.id))
        .where(Track.artist.isnot(None))
        .group_by(Track.artist)
        .order_by(Track.artist)
    )
    rows = result.all()
    return {"artists": [{"name": r[0], "track_count": r[1]} for r in rows]}


@router.get("/albums")
async def list_albums(
    artist: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(
        Track.album,
        Track.artist,
        func.count(Track.id).label("track_count"),
    ).where(Track.album.isnot(None))

    if artist:
        query = query.where(Track.artist == artist)

    query = query.group_by(Track.album, Track.artist).order_by(Track.artist, Track.album)

    result = await db.execute(query)
    rows = result.all()
    return {"albums": [{"album": r[0], "artist": r[1], "track_count": r[2]} for r in rows]}


@router.get("/genres")
async def list_genres(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Track.genre, func.count(Track.id))
        .where(Track.genre.isnot(None))
        .group_by(Track.genre)
        .order_by(Track.genre)
    )
    rows = result.all()
    return {"genres": [{"name": r[0], "track_count": r[1]} for r in rows]}


@router.get("/jingles")
async def list_jingles(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Jingle).order_by(Jingle.title))
    jingles = result.scalars().all()
    return {
        "jingles": [
            {
                "id": j.id,
                "path": j.path,
                "title": j.title,
                "duration_ms": j.duration_ms,
                "cover_art_path": j.cover_art_path,
            }
            for j in jingles
        ]
    }


@router.get("/tracks/random")
async def random_track(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Track).order_by(func.random()).limit(1))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="No tracks found")
    return _track_to_dict(track)
