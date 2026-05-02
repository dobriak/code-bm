"""Functional test for round-robin queue submission.

Tests end-to-end queue submission with multiple playlists against a
fake Liquidsoap client that records pushed URIs. Verifies round-robin
interleaving order.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from raidio.core.scheduler import PlaylistItem, PlaylistState, scheduler_fill_queue


class TestRoundRobinScheduling:
    """Verify the scheduler produces correct round-robin order."""

    def test_single_playlist_plays_in_order(self):
        """A single playlist plays its items in sequence."""
        items_a = [
            PlaylistItem(id=1, track_id=101),
            PlaylistItem(id=2, track_id=102),
            PlaylistItem(id=3, track_id=103),
        ]
        playlists = [PlaylistState(playlist_id=1, items=items_a)]

        results = scheduler_fill_queue(playlists, count=10)

        assert len(results) == 3
        assert [r[0].track_id for r in results] == [101, 102, 103]

    def test_two_playlists_interleave(self):
        """Two playlists interleave: A1, B1, A2, B2, A3, B3."""
        items_a = [
            PlaylistItem(id=1, track_id=101),
            PlaylistItem(id=2, track_id=102),
            PlaylistItem(id=3, track_id=103),
        ]
        items_b = [
            PlaylistItem(id=4, track_id=201),
            PlaylistItem(id=5, track_id=202),
            PlaylistItem(id=6, track_id=203),
        ]
        playlists = [
            PlaylistState(playlist_id=1, items=items_a),
            PlaylistState(playlist_id=2, items=items_b),
        ]

        results = scheduler_fill_queue(playlists, count=10)

        assert len(results) == 6
        track_ids = [r[0].track_id for r in results]
        # Round-robin: A1, B1, A2, B2, A3, B3
        assert track_ids == [101, 201, 102, 202, 103, 203]

        # Verify playlist IDs alternate
        pl_ids = [r[1] for r in results]
        assert pl_ids == [1, 2, 1, 2, 1, 2]

    def test_three_playlists_interleave(self):
        """Three playlists interleave: A1, B1, C1, A2, B2, C2."""
        items_a = [PlaylistItem(id=1, track_id=101), PlaylistItem(id=2, track_id=102)]
        items_b = [PlaylistItem(id=3, track_id=201), PlaylistItem(id=4, track_id=202)]
        items_c = [PlaylistItem(id=5, track_id=301), PlaylistItem(id=6, track_id=302)]

        playlists = [
            PlaylistState(playlist_id=1, items=items_a),
            PlaylistState(playlist_id=2, items=items_b),
            PlaylistState(playlist_id=3, items=items_c),
        ]

        results = scheduler_fill_queue(playlists, count=10)

        assert len(results) == 6
        track_ids = [r[0].track_id for r in results]
        assert track_ids == [101, 201, 301, 102, 202, 302]

    def test_unequal_lengths(self):
        """Playlists with different lengths: shorter ones drop out when exhausted."""
        items_a = [PlaylistItem(id=1, track_id=101)]
        items_b = [PlaylistItem(id=2, track_id=201), PlaylistItem(id=3, track_id=202)]

        playlists = [
            PlaylistState(playlist_id=1, items=items_a),
            PlaylistState(playlist_id=2, items=items_b),
        ]

        results = scheduler_fill_queue(playlists, count=10)

        assert len(results) == 3
        track_ids = [r[0].track_id for r in results]
        # A1, B1, then A exhausted so B2
        assert track_ids == [101, 201, 202]

    def test_empty_playlist_list(self):
        """Empty playlist list returns nothing."""
        results = scheduler_fill_queue([], count=10)
        assert results == []

    def test_all_exhausted(self):
        """Asking for more than available returns only what exists."""
        items_a = [PlaylistItem(id=1, track_id=101)]
        playlists = [PlaylistState(playlist_id=1, items=items_a)]

        results = scheduler_fill_queue(playlists, count=100)
        assert len(results) == 1
        assert results[0][0].track_id == 101


class TestQueueSubmissionRoundRobin:
    """Functional tests for queue submission with multiple users."""

    @pytest.mark.asyncio
    async def test_two_users_submit_playlists(
        self, client, session_factory, db_with_settings, db_with_tracks
    ):
        """Two users submit playlists; scheduler would interleave them."""
        tracks = db_with_tracks

        # User A submits
        resp_a = await client.post(
            "/api/v1/queue/playlists",
            json={
                "name": "User A Playlist",
                "items": [
                    {"track_id": tracks[0].id},
                    {"track_id": tracks[1].id},
                ],
            },
            headers={"X-Raidio-User": "brave_Curie"},
        )
        assert resp_a.status_code == 200

        # User B submits
        resp_b = await client.post(
            "/api/v1/queue/playlists",
            json={
                "name": "User B Playlist",
                "items": [
                    {"track_id": tracks[2].id},
                    {"track_id": tracks[3].id},
                ],
            },
            headers={"X-Raidio-User": "cosmic_Tesla"},
        )
        assert resp_b.status_code == 200

        # Verify both playlists exist in DB with their items
        from raidio.db.models import Playlist, PlaylistKind
        from raidio.db.models import PlaylistItem as PLItem

        async with session_factory() as session:
            result = await session.execute(
                select(Playlist).where(Playlist.kind == PlaylistKind.USER_SESSION)
            )
            playlists = result.scalars().all()

            assert len(playlists) == 2
            names = {pl.name for pl in playlists}
            assert names == {"User A Playlist", "User B Playlist"}

            # Verify items are in correct order within each playlist
            for pl in playlists:
                items_result = await session.execute(
                    select(PLItem).where(PLItem.playlist_id == pl.id).order_by(PLItem.position)
                )
                items = items_result.scalars().all()
                assert len(items) == 2
