"""Round-robin scheduler — pure logic, no I/O.

Given a list of playlists (each a list of items) and per-playlist cursors,
determines the next item to enqueue and advances cursors.

The scheduler takes one item per playlist in rotation order (A1, B1, A2, B2...).
A global cycle index tracks which playlist is next, ensuring fair interleaving.
When a playlist is exhausted, it is skipped.

Fully unit-testable — all data passed in, results returned out.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlaylistItem:
    """A single item within a playlist."""

    id: int
    track_id: int | None = None
    jingle_id: int | None = None
    overlay_at_ms: int | None = None


@dataclass
class PlaylistState:
    """A playlist with its current cursor position."""

    playlist_id: int
    items: list[PlaylistItem] = field(default_factory=list)
    cursor: int = 0  # index of next item to take

    @property
    def remaining(self) -> int:
        """Number of items not yet consumed."""
        return max(0, len(self.items) - self.cursor)

    @property
    def exhausted(self) -> bool:
        """True when all items have been consumed."""
        return self.cursor >= len(self.items)


@dataclass
class SchedulerResult:
    """Result from one scheduler step."""

    item: PlaylistItem | None  # None if nothing to play
    playlist_id: int | None
    playlists: list[PlaylistState]  # updated cursors
    next_playlist_index: int = 0  # which playlist to try next


def scheduler_step(
    playlists: list[PlaylistState],
    next_playlist_index: int = 0,
) -> SchedulerResult:
    """Run one round-robin scheduling step.

    Starting from ``next_playlist_index``, iterates through playlists
    in order (wrapping around) and takes one item from the first
    non-exhausted playlist.

    Args:
        playlists: List of playlist states with cursors.
        next_playlist_index: Index to start searching from (for rotation).

    Returns:
        SchedulerResult with the next item (or None if all exhausted).
    """
    if not playlists:
        return SchedulerResult(
            item=None, playlist_id=None, playlists=playlists, next_playlist_index=0
        )

    n = len(playlists)
    for offset in range(n):
        idx = (next_playlist_index + offset) % n
        pl = playlists[idx]
        if not pl.exhausted:
            item = pl.items[pl.cursor]
            pl.cursor += 1
            # Next time, start from the playlist after this one
            next_idx = (idx + 1) % n
            return SchedulerResult(
                item=item,
                playlist_id=pl.playlist_id,
                playlists=playlists,
                next_playlist_index=next_idx,
            )

    return SchedulerResult(item=None, playlist_id=None, playlists=playlists, next_playlist_index=0)


def scheduler_fill_queue(
    playlists: list[PlaylistState],
    count: int,
) -> list[tuple[PlaylistItem, int]]:
    """Run multiple scheduler steps to fill a queue.

    Args:
        playlists: List of playlist states.
        count: How many items to dequeue.

    Returns:
        List of (item, playlist_id) tuples in order.
    """
    results: list[tuple[PlaylistItem, int]] = []
    next_idx = 0
    for _ in range(count):
        step = scheduler_step(playlists, next_idx)
        if step.item is None:
            break
        results.append((step.item, step.playlist_id))  # type: ignore[arg-type]
        next_idx = step.next_playlist_index
    return results
