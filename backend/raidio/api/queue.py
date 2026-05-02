"""Queue API — playlist submission, now-playing.

Public endpoints (no auth required).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from raidio.core.now_playing import QueueTrackInfo, get_now_playing
from raidio.db.models import (
    Jingle,
    LiveQueueItem,
    LiveQueueState,
    Playlist,
    PlaylistItem,
    PlaylistKind,
    Setting,
    Track,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["queue"])


# ── Schemas ────────────────────────────────────────────────────────


class PlaylistItemCreate(BaseModel):
    track_id: int | None = None
    jingle_id: int | None = None
    overlay_at_ms: int | None = None


class PlaylistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    notes: str | None = None
    items: list[PlaylistItemCreate] = Field(..., min_length=1)
    owner_label: str | None = None


class PlaylistResponse(BaseModel):
    id: int
    name: str
    notes: str | None
    owner_label: str | None
    estimated_time_to_play_ms: int | None


class QueueTrackSchema(BaseModel):
    id: int
    track_id: int | None
    jingle_id: int | None
    artist: str | None
    title: str | None
    album: str | None
    duration_ms: int | None
    cover_art_path: str | None
    state: str
    started_at: str | None
    ended_at: str | None
    owner_label: str | None


class NowPlayingResponse(BaseModel):
    current: QueueTrackSchema | None
    prev: list[QueueTrackSchema]
    next: list[QueueTrackSchema]
    buffer_offset_ms: int


# ── Dependencies ───────────────────────────────────────────────────


def _get_session():
    from raidio.db.session import get_session_factory

    return get_session_factory()


def _info_to_schema(info: QueueTrackInfo) -> QueueTrackSchema:
    return QueueTrackSchema(
        id=info.id,
        track_id=info.track_id,
        jingle_id=info.jingle_id,
        artist=info.artist,
        title=info.title,
        album=info.album,
        duration_ms=info.duration_ms,
        cover_art_path=info.cover_art_path,
        state=info.state,
        started_at=info.started_at,
        ended_at=info.ended_at,
        owner_label=info.owner_label,
    )


# ── POST /queue/playlists ─────────────────────────────────────────


@router.post("/queue/playlists", response_model=PlaylistResponse)
async def submit_playlist(
    body: PlaylistCreate,
    x_raidio_user: Annotated[str | None, Header()] = None,
):
    """Submit a user playlist for broadcast.

    Creates a user_session playlist with its items and registers it
    with the scheduler. Returns estimated time-to-play.
    """
    factory = _get_session()
    async with factory() as session:
        # Validate items
        for idx, item in enumerate(body.items):
            if item.track_id is None and item.jingle_id is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Item {idx}: must have track_id or jingle_id",
                )

            # Verify track exists
            if item.track_id is not None:
                track = await session.get(Track, item.track_id)
                if not track:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Track {item.track_id} not found",
                    )

            # Verify jingle exists
            if item.jingle_id is not None:
                jingle = await session.get(Jingle, item.jingle_id)
                if not jingle:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Jingle {item.jingle_id} not found",
                    )

        # Create playlist
        playlist = Playlist(
            name=body.name,
            notes=body.notes,
            kind=PlaylistKind.USER_SESSION,
            owner_label=x_raidio_user or body.owner_label,
        )
        session.add(playlist)
        await session.flush()

        # Create playlist items
        for idx, item in enumerate(body.items):
            pi = PlaylistItem(
                playlist_id=playlist.id,
                position=idx,
                track_id=item.track_id,
                jingle_id=item.jingle_id,
                overlay_at_ms=item.overlay_at_ms,
            )
            session.add(pi)

        await session.commit()
        await session.refresh(playlist)

        # Estimate time-to-play: count pending items ahead in live_queue
        # and multiply by average track duration
        pending_count_stmt = (
            select(func.count())
            .select_from(LiveQueueItem)
            .where(LiveQueueItem.state == LiveQueueState.PENDING)
        )
        pending_count = (await session.execute(pending_count_stmt)).scalar() or 0

        # Get average track duration from existing items
        avg_stmt = select(func.avg(Track.duration_ms)).where(Track.duration_ms.isnot(None))
        avg_duration = (await session.execute(avg_stmt)).scalar() or 200_000

        # Each pending item takes one slot, but we interleave with other playlists
        # Rough estimate: pending_count * avg_duration
        etp = int(pending_count * avg_duration) if pending_count > 0 else 0

        return PlaylistResponse(
            id=playlist.id,
            name=playlist.name,
            notes=playlist.notes,
            owner_label=playlist.owner_label,
            estimated_time_to_play_ms=etp,
        )


# ── GET /now-playing ──────────────────────────────────────────────


@router.get("/now-playing", response_model=NowPlayingResponse)
async def now_playing():
    """Get current track, prev 3, next 3."""
    factory = _get_session()
    async with factory() as session:
        # Get buffer offset from settings
        settings_row = await session.get(Setting, 1)
        offset = settings_row.icecast_buffer_offset_ms if settings_row else 3000

        result = await get_now_playing(session, offset)

        return NowPlayingResponse(
            current=_info_to_schema(result.current) if result.current else None,
            prev=[_info_to_schema(p) for p in result.prev],
            next=[_info_to_schema(n) for n in result.next],
            buffer_offset_ms=result.buffer_offset_ms,
        )


# ── WebSocket /ws/now-playing ────────────────────────────────────


@router.websocket("/ws/now-playing")
async def now_playing_ws(websocket: WebSocket):
    """WebSocket that pushes now-playing updates on every track change."""
    await websocket.accept()
    logger.info("Now-playing WebSocket connected")

    try:
        last_current_id: int | None = None

        while True:
            factory = _get_session()
            async with factory() as session:
                settings_row = await session.get(Setting, 1)
                offset = settings_row.icecast_buffer_offset_ms if settings_row else 3000
                result = await get_now_playing(session, offset)

            current_id = result.current.id if result.current else None

            # Only send when current track changes
            if current_id != last_current_id:
                payload = {
                    "current": (
                        _info_to_schema(result.current).model_dump() if result.current else None
                    ),
                    "prev": [_info_to_schema(p).model_dump() for p in result.prev],
                    "next": [_info_to_schema(n).model_dump() for n in result.next],
                    "buffer_offset_ms": result.buffer_offset_ms,
                }
                await websocket.send_json(payload)
                last_current_id = current_id

            await asyncio_sleep(2.0)
    except WebSocketDisconnect:
        logger.info("Now-playing WebSocket disconnected")
    except Exception:
        logger.exception("Now-playing WebSocket error")


async def asyncio_sleep(seconds: float) -> None:
    """Async sleep — avoids importing asyncio at module level in tests."""
    import asyncio

    await asyncio.sleep(seconds)
