"""Unit tests for the round-robin scheduler.

Tests cover: single playlist, multiple playlists, late-joiner,
exhaustion, empty case. Target ≥ 95% coverage on scheduler.py.
"""

from __future__ import annotations

from raidio.core.scheduler import (
    PlaylistItem,
    PlaylistState,
    scheduler_fill_queue,
    scheduler_step,
)


def _item(id: int, track_id: int | None = None) -> PlaylistItem:
    """Helper to create a PlaylistItem."""
    return PlaylistItem(id=id, track_id=track_id)


def _state(pid: int, items: list[PlaylistItem], cursor: int = 0) -> PlaylistState:
    """Helper to create a PlaylistState."""
    return PlaylistState(playlist_id=pid, items=items, cursor=cursor)


class TestSchedulerStep:
    """Tests for scheduler_step()."""

    def test_single_playlist_first_item(self):
        """First call on a single playlist returns its first item."""
        items = [_item(1), _item(2), _item(3)]
        playlists = [_state(pid=10, items=items)]

        result = scheduler_step(playlists)

        assert result.item is not None
        assert result.item.id == 1
        assert result.playlist_id == 10
        assert playlists[0].cursor == 1

    def test_single_playlist_advances_cursor(self):
        """Each call advances the cursor by one."""
        items = [_item(1), _item(2)]
        playlists = [_state(pid=10, items=items)]

        r1 = scheduler_step(playlists)
        assert r1.item.id == 1
        assert playlists[0].cursor == 1

        r2 = scheduler_step(playlists, r1.next_playlist_index)
        assert r2.item.id == 2
        assert playlists[0].cursor == 2

    def test_single_playlist_exhaustion(self):
        """Returns None when the single playlist is exhausted."""
        items = [_item(1)]
        playlists = [_state(pid=10, items=items)]

        scheduler_step(playlists)  # consume the only item

        result = scheduler_step(playlists, next_playlist_index=0)
        assert result.item is None
        assert result.playlist_id is None

    def test_multiple_playlists_round_robin(self):
        """Interleaves items across playlists: A1, B1, A2, B2."""
        a_items = [_item(101), _item(102)]
        b_items = [_item(201), _item(202)]
        playlists = [_state(pid=1, items=a_items), _state(pid=2, items=b_items)]

        results = []
        next_idx = 0
        for _ in range(4):
            r = scheduler_step(playlists, next_idx)
            if r.item:
                results.append(r.item.id)
                next_idx = r.next_playlist_index

        assert results == [101, 201, 102, 202]

    def test_multiple_playlists_uneven_lengths(self):
        """Shorter playlist drops out when exhausted."""
        a_items = [_item(101), _item(102), _item(103)]
        b_items = [_item(201)]
        playlists = [_state(pid=1, items=a_items), _state(pid=2, items=b_items)]

        results = []
        next_idx = 0
        for _ in range(5):
            r = scheduler_step(playlists, next_idx)
            if r.item:
                results.append(r.item.id)
                next_idx = r.next_playlist_index

        # A1, B1, A2, A3
        assert results == [101, 201, 102, 103]

    def test_late_joiner(self):
        """A new playlist entering mid-cycle joins the rotation.

        The scheduler starts with A only, takes A1, then B joins.
        A still has items so the next step may take from A again
        (since the index was set for a single-playlist rotation).
        Once the index reaches B, it joins the round-robin.
        """
        a_items = [_item(101), _item(102), _item(103)]
        b_items = [_item(201), _item(202)]
        playlists = [_state(pid=1, items=a_items)]

        # First cycle: only A
        r1 = scheduler_step(playlists)
        assert r1.item.id == 101

        # B joins
        playlists.append(_state(pid=2, items=b_items))

        # Continue scheduling — B enters the rotation
        results = []
        next_idx = r1.next_playlist_index
        for _ in range(4):
            r = scheduler_step(playlists, next_idx)
            if r.item:
                results.append((r.item.id, r.playlist_id))
                next_idx = r.next_playlist_index

        # Should get A2, B1, A3, B2
        item_ids = [i for i, _ in results]
        assert 201 in item_ids  # B's items appear
        assert 202 in item_ids
        # Both playlists are represented
        playlist_ids = [p for _, p in results]
        assert 1 in playlist_ids
        assert 2 in playlist_ids

    def test_empty_playlists(self):
        """Empty input returns None."""
        result = scheduler_step([])
        assert result.item is None

    def test_all_playlists_empty(self):
        """Playlists with no items return None."""
        playlists = [_state(pid=1, items=[]), _state(pid=2, items=[])]
        result = scheduler_step(playlists)
        assert result.item is None

    def test_playlist_with_partial_cursor(self):
        """Playlist starting mid-way (e.g. reconnection) resumes correctly."""
        items = [_item(1), _item(2), _item(3), _item(4)]
        playlists = [_state(pid=1, items=items, cursor=2)]

        result = scheduler_step(playlists)
        assert result.item.id == 3

    def test_three_playlists_round_robin(self):
        """Three playlists interleave: A1, B1, C1, A2, B2, C2."""
        a = [_item(101), _item(102)]
        b = [_item(201), _item(202)]
        c = [_item(301), _item(302)]
        playlists = [_state(1, a), _state(2, b), _state(3, c)]

        results = []
        next_idx = 0
        for _ in range(6):
            r = scheduler_step(playlists, next_idx)
            if r.item:
                results.append(r.item.id)
                next_idx = r.next_playlist_index

        assert results == [101, 201, 301, 102, 202, 302]


class TestSchedulerFillQueue:
    """Tests for scheduler_fill_queue()."""

    def test_fills_requested_count(self):
        """Fills exactly the requested number of items."""
        items = [_item(i) for i in range(10)]
        playlists = [_state(pid=1, items=items)]

        results = scheduler_fill_queue(playlists, 5)
        assert len(results) == 5
        assert [item.id for item, _ in results] == [0, 1, 2, 3, 4]

    def test_stops_when_exhausted(self):
        """Returns fewer items if playlists run out."""
        items = [_item(1), _item(2)]
        playlists = [_state(pid=1, items=items)]

        results = scheduler_fill_queue(playlists, 10)
        assert len(results) == 2

    def test_empty_playlists(self):
        """Returns empty list when no playlists."""
        results = scheduler_fill_queue([], 5)
        assert results == []

    def test_returns_playlist_ids(self):
        """Each result includes the playlist_id it came from."""
        a_items = [_item(101), _item(102)]
        b_items = [_item(201)]
        playlists = [_state(pid=1, items=a_items), _state(pid=2, items=b_items)]

        results = scheduler_fill_queue(playlists, 10)
        playlist_ids = [pid for _, pid in results]

        assert playlist_ids == [1, 2, 1]

    def test_round_robin_fill(self):
        """scheduler_fill_queue also does round-robin interleaving."""
        a_items = [_item(101), _item(102)]
        b_items = [_item(201), _item(202)]
        playlists = [_state(pid=1, items=a_items), _state(pid=2, items=b_items)]

        results = scheduler_fill_queue(playlists, 4)
        item_ids = [item.id for item, _ in results]

        assert item_ids == [101, 201, 102, 202]


class TestPlaylistState:
    """Tests for PlaylistState properties."""

    def test_remaining(self):
        items = [_item(1), _item(2), _item(3)]
        state = PlaylistState(playlist_id=1, items=items, cursor=1)
        assert state.remaining == 2

    def test_remaining_at_end(self):
        items = [_item(1)]
        state = PlaylistState(playlist_id=1, items=items, cursor=1)
        assert state.remaining == 0

    def test_exhausted(self):
        items = [_item(1)]
        state = PlaylistState(playlist_id=1, items=items, cursor=0)
        assert not state.exhausted
        state.cursor = 1
        assert state.exhausted

    def test_exhausted_empty_playlist(self):
        state = PlaylistState(playlist_id=1, items=[])
        assert state.exhausted
