
from raidio.core.scheduler import (
    PlaylistItem,
    round_robin,
    single_playlist_round_robin,
)


def make_item(
    playlist_id: int,
    track_id: int | None = None,
    jingle_id: int | None = None,
) -> PlaylistItem:
    return PlaylistItem(playlist_id=playlist_id, track_id=track_id, jingle_id=jingle_id)


class TestRoundRobin:
    def test_empty_playlists(self):
        result, cycle = round_robin({}, {})
        assert result is None
        assert cycle == 0

    def test_single_playlist(self):
        playlists = {
            1: [
                make_item(1, track_id=10),
                make_item(1, track_id=11),
                make_item(1, track_id=12),
            ]
        }
        cursors = {1: 0}
        result, cycle = round_robin(playlists, cursors)
        assert result is not None
        assert result.item.track_id == 10
        assert result.next_cursors == {1: 1}

    def test_multiple_playlists_interleaved(self):
        playlists = {
            1: [make_item(1, track_id=10), make_item(1, track_id=11)],
            2: [make_item(2, track_id=20), make_item(2, track_id=21)],
        }
        cursors = {1: 0, 2: 0}

        result1, cycle1 = round_robin(playlists, cursors)
        assert result1 is not None
        assert result1.item.playlist_id == 1
        assert result1.item.track_id == 10
        assert result1.next_cursors == {1: 1, 2: 0}

        result2, cycle2 = round_robin(playlists, result1.next_cursors, cycle1)
        assert result2 is not None
        assert result2.item.playlist_id == 2
        assert result2.item.track_id == 20
        assert result2.next_cursors == {1: 1, 2: 1}

        result3, cycle3 = round_robin(playlists, result2.next_cursors, cycle2)
        assert result3 is not None
        assert result3.item.playlist_id == 1
        assert result3.item.track_id == 11
        assert result3.next_cursors == {1: 2, 2: 1}

        result4, cycle4 = round_robin(playlists, result3.next_cursors, cycle3)
        assert result4 is not None
        assert result4.item.playlist_id == 2
        assert result4.item.track_id == 21
        assert result4.next_cursors == {1: 2, 2: 2}

    def test_late_joiner(self):
        playlists = {1: [make_item(1, track_id=10)]}
        cursors = {1: 0}

        result1, cycle1 = round_robin(playlists, cursors)
        assert result1 is not None
        assert result1.next_cursors == {1: 1}

        playlists[2] = [make_item(2, track_id=20), make_item(2, track_id=21)]
        result2, cycle2 = round_robin(playlists, result1.next_cursors, cycle1)
        assert result2 is not None
        assert result2.item.playlist_id == 2
        assert result2.item.track_id == 20
        assert result2.next_cursors == {1: 1, 2: 1}

    def test_exhausted_playlist_dropped(self):
        playlists = {
            1: [make_item(1, track_id=10)],
            2: [make_item(2, track_id=20), make_item(2, track_id=21)],
        }
        cursors = {1: 0, 2: 0}

        result1, cycle1 = round_robin(playlists, cursors)
        assert result1 is not None
        assert result1.item.track_id == 10

        result2, cycle2 = round_robin(playlists, result1.next_cursors, cycle1)
        assert result2 is not None
        assert result2.item.track_id == 20

        result3, cycle3 = round_robin(playlists, result2.next_cursors, cycle2)
        assert result3 is not None
        assert result3.item.track_id == 21


class TestSinglePlaylistRoundRobin:
    def test_empty(self):
        item, cursor = single_playlist_round_robin([], 0)
        assert item is None
        assert cursor == 0

    def test_first_item(self):
        items = [make_item(1, track_id=10), make_item(1, track_id=11)]
        item, cursor = single_playlist_round_robin(items, 0)
        assert item is not None
        assert item.track_id == 10
        assert cursor == 1

    def test_advance(self):
        items = [make_item(1, track_id=10), make_item(1, track_id=11)]
        item, cursor = single_playlist_round_robin(items, 1)
        assert item is not None
        assert item.track_id == 11
        assert cursor == 2

    def test_exhausted(self):
        items = [make_item(1, track_id=10)]
        item, cursor = single_playlist_round_robin(items, 1)
        assert item is None
        assert cursor == 1

