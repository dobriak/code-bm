from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from raidio.db.models import LiveQueueItem


class NowPlayingTrack(TypedDict):
    id: int
    title: str | None
    artist: str | None
    album: str | None
    duration_ms: int | None
    cover_art_path: str | None
    started_at: str
    queue_item_id: int | None


class NowPlayingDict(TypedDict):
    current: NowPlayingTrack | None
    prev3: list[NowPlayingTrack]
    next3: list[NowPlayingTrack]


@dataclass
class NowPlayingState:
    current: LiveQueueItem | None = None
    prev3: list[LiveQueueItem] | None = None
    next3: list[LiveQueueItem] | None = None

    def __post_init__(self):
        if self.prev3 is None:
            self.prev3 = []
        if self.next3 is None:
            self.next3 = []

    def to_dict(self, buffer_offset_ms: int = 3000) -> NowPlayingDict:
        now = datetime.now(UTC)
        adjusted = now - timedelta(milliseconds=buffer_offset_ms)

        def queue_item_to_track(
            item: LiveQueueItem | None, adj_time: datetime
        ) -> NowPlayingTrack | None:
            if item is None or item.track_id is None:
                return None
            return NowPlayingTrack(
                id=item.track_id,
                title=None,
                artist=None,
                album=None,
                duration_ms=None,
                cover_art_path=None,
                started_at=adj_time.isoformat(),
                queue_item_id=item.id if item else None,
            )

        return NowPlayingDict(
            current=queue_item_to_track(self.current, adjusted),
            prev3=[queue_item_to_track(item, adjusted) for item in self.prev3],
            next3=[queue_item_to_track(item, adjusted) for item in self.next3],
        )

