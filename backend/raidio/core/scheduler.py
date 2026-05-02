from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PlaylistItem:
    playlist_id: int
    track_id: int | None = None
    jingle_id: int | None = None
    overlay_at_ms: int | None = None


@dataclass
class SchedulerResult:
    item: PlaylistItem
    next_cursors: dict[int, int]


class Scheduler(Protocol):
    def schedule(
        self,
        playlists: dict[int, list[PlaylistItem]],
        cursors: dict[int, int],
    ) -> SchedulerResult | None:
        ...


def round_robin(
    playlists: dict[int, list[PlaylistItem]],
    cursors: dict[int, int],
    cycle_start: int = 0,
) -> tuple[SchedulerResult | None, int]:
    active = [pid for pid, items in playlists.items() if cursors.get(pid, 0) < len(items)]
    if not active:
        return None, cycle_start

    cycle = cycle_start

    while True:
        pid = active[cycle % len(active)]
        cursor = cursors.get(pid, 0)
        items = playlists[pid]
        if cursor < len(items):
            new_cursors = dict(cursors)
            new_cursors[pid] = cursor + 1
            return SchedulerResult(
                item=items[cursor],
                next_cursors=new_cursors,
            ), (cycle + 1) % len(active)
        cycle += 1
        if cycle >= cycle_start + len(active):
            return None, cycle


def single_playlist_round_robin(
    playlist_items: list[PlaylistItem],
    cursor: int,
) -> tuple[PlaylistItem | None, int]:
    if cursor >= len(playlist_items):
        return None, cursor
    return playlist_items[cursor], cursor + 1

