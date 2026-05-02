"""Now-playing state — tracks current/prev3/next3 from live_queue.

Computes the "current track" aligned to the Icecast buffer offset so
that listener UIs match what they actually hear.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select

from raidio.db.models import (
    Jingle,
    LiveQueueItem,
    LiveQueueState,
    Track,
)

logger = logging.getLogger(__name__)


@dataclass
class QueueTrackInfo:
    """A track/jingle in the queue with display metadata."""

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


@dataclass
class NowPlayingResult:
    """Structured now-playing response."""

    current: QueueTrackInfo | None
    prev: list[QueueTrackInfo]
    next: list[QueueTrackInfo]
    buffer_offset_ms: int


async def get_now_playing(session: object, buffer_offset_ms: int = 3000) -> NowPlayingResult:
    """Fetch current/prev/next from live_queue.

    Args:
        session: SQLAlchemy async session.
        buffer_offset_ms: Icecast buffer offset in ms (default 3000).

    Returns:
        NowPlayingResult with current, prev (up to 3), next (up to 3).
    """
    # Find the currently playing item
    current_stmt = (
        select(LiveQueueItem)
        .where(LiveQueueItem.state == LiveQueueState.PLAYING)
        .order_by(LiveQueueItem.position)
        .limit(1)
    )
    result = await session.execute(current_stmt)
    current_lq = result.scalar_one_or_none()

    current: QueueTrackInfo | None = None
    current_position = -1

    if current_lq:
        current_position = current_lq.position
        current = await _lq_to_info(session, current_lq)

    # Prev: up to 3 most recent played/skipped items before current
    prev_items: list[QueueTrackInfo] = []
    if current_position >= 0:
        prev_stmt = (
            select(LiveQueueItem)
            .where(
                LiveQueueItem.state.in_([LiveQueueState.PLAYED, LiveQueueState.SKIPPED]),
                LiveQueueItem.position < current_position,
            )
            .order_by(LiveQueueItem.position.desc())
            .limit(3)
        )
        prev_result = await session.execute(prev_stmt)
        prev_lqs = list(reversed(prev_result.scalars().all()))
        for lq in prev_lqs:
            prev_items.append(await _lq_to_info(session, lq))

    # Next: up to 3 pending items after current
    next_items: list[QueueTrackInfo] = []
    if current_position >= 0:
        next_stmt = (
            select(LiveQueueItem)
            .where(
                LiveQueueItem.state == LiveQueueState.PENDING,
                LiveQueueItem.position > current_position,
            )
            .order_by(LiveQueueItem.position)
            .limit(3)
        )
    else:
        # Nothing playing yet — show first pending items
        next_stmt = (
            select(LiveQueueItem)
            .where(LiveQueueItem.state == LiveQueueState.PENDING)
            .order_by(LiveQueueItem.position)
            .limit(3)
        )

    next_result = await session.execute(next_stmt)
    for lq in next_result.scalars().all():
        next_items.append(await _lq_to_info(session, lq))

    return NowPlayingResult(
        current=current,
        prev=prev_items,
        next=next_items,
        buffer_offset_ms=buffer_offset_ms,
    )


async def _lq_to_info(session: object, lq: LiveQueueItem) -> QueueTrackInfo:
    """Convert a LiveQueueItem to QueueTrackInfo with joined metadata."""
    artist: str | None = None
    title: str | None = None
    album: str | None = None
    duration_ms: int | None = None
    cover_art_path: str | None = None
    owner_label: str | None = None

    if lq.track_id is not None:
        track = await session.get(Track, lq.track_id)
        if track:
            artist = track.artist
            title = track.title
            album = track.album
            duration_ms = track.duration_ms
            cover_art_path = track.cover_art_path
    elif lq.jingle_id is not None:
        jingle = await session.get(Jingle, lq.jingle_id)
        if jingle:
            title = jingle.title
            duration_ms = jingle.duration_ms
            cover_art_path = jingle.cover_art_path

    # Get owner_label from playlist
    if lq.playlist_id is not None:
        from raidio.db.models import Playlist

        pl = await session.get(Playlist, lq.playlist_id)
        if pl:
            owner_label = pl.owner_label

    return QueueTrackInfo(
        id=lq.id,
        track_id=lq.track_id,
        jingle_id=lq.jingle_id,
        artist=artist,
        title=title,
        album=album,
        duration_ms=duration_ms,
        cover_art_path=cover_art_path,
        state=lq.state.value,
        started_at=lq.started_at.isoformat() if lq.started_at else None,
        ended_at=lq.ended_at.isoformat() if lq.ended_at else None,
        owner_label=owner_label,
    )
