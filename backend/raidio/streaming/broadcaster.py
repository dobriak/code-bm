"""Broadcaster — long-running asyncio task that drives the live queue.

Watches the live_queue table and active user_session playlists.
Uses scheduler logic to determine next items and pushes URIs to Liquidsoap.
Handles idle behavior when nothing is queued.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select

from raidio.core.scheduler import PlaylistItem, PlaylistState, scheduler_step
from raidio.db.models import (
    IdleBehavior,
    LiveQueueItem,
    LiveQueueState,
    Playlist,
    PlaylistKind,
    Setting,
    Track,
)
from raidio.db.models import (
    PlaylistItem as PlaylistItemModel,
)
from raidio.db.session import async_sessionmaker
from raidio.streaming.liquidsoap import LiquidsoapClient, LiquidsoapError

logger = logging.getLogger(__name__)

# How often the broadcaster loop ticks (seconds)
TICK_INTERVAL = 2.0
# Minimum queue depth in Liquidsoap before pushing more
MIN_QUEUE_DEPTH = 2


class Broadcaster:
    """Async broadcaster that fills Liquidsoap's queue from the scheduler."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        ls_client: LiquidsoapClient,
    ) -> None:
        self._session_factory = session_factory
        self._ls = ls_client
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the broadcaster loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Broadcaster started")

    async def stop(self) -> None:
        """Stop the broadcaster loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib_suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("Broadcaster stopped")

    async def _loop(self) -> None:
        """Main loop: check queue depth, schedule next items."""
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Broadcaster tick failed")
            await asyncio.sleep(TICK_INTERVAL)

    async def _tick(self) -> None:
        """One scheduler tick."""
        # Check how many items Liquidsoap has queued
        try:
            queue_size = await self._ls.queue_size()
        except LiquidsoapError:
            logger.debug("Cannot read Liquidsoap queue size — skipping tick")
            return

        if queue_size >= MIN_QUEUE_DEPTH:
            return

        # Need more items — ask the scheduler
        needed = MIN_QUEUE_DEPTH - queue_size + 1
        async with self._session_factory() as session:
            playlists = await self._load_playlists(session)
            if not playlists:
                await self._handle_idle(session)
                return

            for _ in range(needed):
                result = scheduler_step(playlists)
                if result.item is None:
                    # All playlists exhausted
                    await self._handle_idle(session)
                    return

                await self._enqueue_item(session, result.item, result.playlist_id)

    async def _load_playlists(self, session: async_sessionmaker | object) -> list[PlaylistState]:
        """Load all active user_session playlists into scheduler state."""
        # Only playlists that still have un-enqueued items
        stmt = (
            select(Playlist)
            .where(Playlist.kind == PlaylistKind.USER_SESSION)
            .order_by(Playlist.created_at)
        )
        result = await session.execute(stmt)
        db_playlists = result.scalars().all()

        states: list[PlaylistState] = []
        for pl in db_playlists:
            # Count how many items from this playlist are already in live_queue
            count_stmt = (
                select(func.count())
                .select_from(LiveQueueItem)
                .where(LiveQueueItem.playlist_id == pl.id)
            )
            already_enqueued = (await session.execute(count_stmt)).scalar() or 0

            # Load playlist items in position order
            items_stmt = (
                select(PlaylistItemModel)
                .where(PlaylistItemModel.playlist_id == pl.id)
                .order_by(PlaylistItemModel.position)
            )
            items_result = await session.execute(items_stmt)
            db_items = items_result.scalars().all()

            scheduler_items = [
                PlaylistItem(
                    id=item.id,
                    track_id=item.track_id,
                    jingle_id=item.jingle_id,
                    overlay_at_ms=item.overlay_at_ms,
                )
                for item in db_items
            ]

            if already_enqueued < len(scheduler_items):
                state = PlaylistState(
                    playlist_id=pl.id,
                    items=scheduler_items,
                    cursor=already_enqueued,
                )
                states.append(state)

        return states

    async def _enqueue_item(
        self,
        session: object,
        item: PlaylistItem,
        playlist_id: int,
    ) -> None:
        """Create a live_queue row and push the URI to Liquidsoap."""
        uri = await self._resolve_uri(session, item)
        if not uri:
            logger.warning("Cannot resolve URI for item %d — skipping", item.id)
            return

        # Determine position (max existing + 1)
        max_pos_stmt = select(func.coalesce(func.max(LiveQueueItem.position), -1))
        max_pos = (await session.execute(max_pos_stmt)).scalar() or -1
        next_pos = max_pos + 1

        lq = LiveQueueItem(
            position=next_pos,
            playlist_id=playlist_id,
            track_id=item.track_id,
            jingle_id=item.jingle_id,
            state=LiveQueueState.PENDING,
            enqueued_at=datetime.now(tz=UTC).replace(tzinfo=None),
        )
        session.add(lq)
        await session.commit()
        await session.refresh(lq)

        # Push to Liquidsoap
        try:
            await self._ls.push(uri)
            logger.info("Enqueued item %d (live_queue %d): %s", item.id, lq.id, uri)
        except LiquidsoapError as exc:
            logger.error("Failed to push %s to Liquidsoap: %s", uri, exc)
            # Mark as skipped
            lq.state = LiveQueueState.SKIPPED
            lq.ended_at = datetime.now(tz=UTC).replace(tzinfo=None)
            await session.commit()

    async def _resolve_uri(self, session: object, item: PlaylistItem) -> str | None:
        """Get the file path for a track or jingle."""
        if item.track_id is not None:
            track = await session.get(Track, item.track_id)
            return track.path if track else None
        if item.jingle_id is not None:
            from raidio.db.models import Jingle

            jingle = await session.get(Jingle, item.jingle_id)
            return jingle.path if jingle else None
        return None

    async def _handle_idle(self, session: object) -> None:
        """Handle idle behavior when nothing is queued."""
        # Load settings
        settings_row = await session.get(Setting, 1)
        if not settings_row:
            return

        idle = settings_row.idle_behavior

        if idle == IdleBehavior.SILENCE:
            return  # Liquidsoap's mksafe already handles silence

        if idle == IdleBehavior.RANDOM:
            # Pick a random track
            track_stmt = select(Track).order_by(func.random()).limit(1)
            result = await session.execute(track_stmt)
            track = result.scalar_one_or_none()
            if track:
                try:
                    await self._ls.push(track.path)
                    logger.info("Idle: pushed random track %s", track.path)
                except LiquidsoapError as exc:
                    logger.error("Failed to push idle random track: %s", exc)
            return

        if idle == IdleBehavior.AUTO_PLAYLIST:
            if not settings_row.default_auto_playlist_id:
                return
            # Load auto-playlist items and push next unplayed one
            from raidio.db.models import PlaylistItem as PLItem

            items_stmt = (
                select(PLItem)
                .where(PLItem.playlist_id == settings_row.default_auto_playlist_id)
                .order_by(PLItem.position)
            )
            items_result = await session.execute(items_stmt)
            items = items_result.scalars().all()

            if not items:
                return

            # Simple round-robin on auto-playlist (track count as cycle)
            count_stmt = (
                select(func.count())
                .select_from(LiveQueueItem)
                .where(
                    LiveQueueItem.playlist_id == settings_row.default_auto_playlist_id,
                )
            )
            already = (await session.execute(count_stmt)).scalar() or 0
            idx = already % len(items)
            pl_item = items[idx]
            track = await session.get(Track, pl_item.track_id)
            if track:
                try:
                    await self._ls.push(track.path)
                    logger.info("Idle: pushed auto-playlist track %s", track.path)
                except LiquidsoapError as exc:
                    logger.error("Failed to push idle auto-playlist track: %s", exc)


def contextlib_suppress(*exceptions):
    """Inline contextlib.suppress to avoid import at module level."""
    from contextlib import suppress

    return suppress(*exceptions)
