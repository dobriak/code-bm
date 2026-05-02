from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from raidio.core.now_playing import NowPlayingState
from raidio.db.models import LiveQueueItem, LiveQueueState, Setting, Track
from raidio.streaming.liquidsoap import LiquidsoapClient

if TYPE_CHECKING:
    from raidio.api.ws_now_playing import NowPlayingManager

logger = logging.getLogger(__name__)

QUEUE_DEPTH_THRESHOLD = 2


class Broadcaster:
    def __init__(self, session_factory, liquidsoap: LiquidsoapClient):
        self._session_factory = session_factory
        self._ls = liquidsoap
        self._state = NowPlayingState()
        self._ws_manager: NowPlayingManager | None = None
        self._stopping = False

    def set_ws_manager(self, manager: NowPlayingManager) -> None:
        self._ws_manager = manager

    async def start(self) -> None:
        logger.info("Broadcaster starting")
        while not self._stopping:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.exception("Broadcaster cycle error: %s", e)
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self._stopping = True

    async def _run_cycle(self) -> None:
        queue_depth = await self._ls.queue_size()
        if queue_depth >= QUEUE_DEPTH_THRESHOLD:
            await asyncio.sleep(2)
            return

        async with self._session_factory() as session:
            items = await self._get_pending_queue_items(session)
            if items:
                await self._advance_queue(session, items)
            else:
                await self._handle_idle(session)

        await asyncio.sleep(1)

    async def _get_pending_queue_items(self, session: AsyncSession) -> list[LiveQueueItem]:
        result = await session.execute(
            select(LiveQueueItem)
            .where(LiveQueueItem.state == LiveQueueState.PENDING)
            .order_by(LiveQueueItem.position)
            .limit(5)
        )
        return list(result.scalars().all())

    async def _advance_queue(
        self, session: AsyncSession, items: list[LiveQueueItem]
    ) -> None:
        if items:
            item = items[0]
            track = await session.get(Track, item.track_id) if item.track_id else None
            if track:
                await self._ls.push(f"file://{track.path}")
                item.state = LiveQueueState.PLAYING
                item.started_at = datetime.utcnow()
                self._state.current = item
                await session.commit()
                await self._broadcast_now_playing()

    async def _handle_idle(self, session: AsyncSession) -> None:
        settings = await session.get(Setting, 1)
        if not settings:
            return

        if settings.idle_behavior == "random":
            result = await session.execute(select(Track).order_by(func.random()).limit(1))
            track = result.scalar_one_or_none()
            if track:
                await self._ls.push(f"file://{track.path}")
        elif settings.idle_behavior == "auto_playlist" and settings.default_auto_playlist_id:
            pass

    async def _broadcast_now_playing(self) -> None:
        if self._ws_manager:
            await self._ws_manager.broadcast(self._state.to_dict())

    @property
    def state(self) -> NowPlayingState:
        return self._state

