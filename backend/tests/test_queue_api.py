"""Functional tests for the queue API endpoints."""

from __future__ import annotations


class TestNowPlayingEndpoint:
    """Tests for GET /api/v1/now-playing."""

    async def test_empty_queue(self, client, session_factory, db_with_settings):
        """Returns empty structure when nothing is playing."""
        resp = await client.get("/api/v1/now-playing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current"] is None
        assert data["prev"] == []
        assert data["next"] == []
        assert data["buffer_offset_ms"] > 0


class TestSubmitPlaylistEndpoint:
    """Tests for POST /api/v1/queue/playlists."""

    async def test_submit_valid_playlist(
        self, client, session_factory, db_with_settings, db_with_tracks
    ):
        """Valid playlist submission creates playlist and items."""
        tracks = db_with_tracks
        resp = await client.post(
            "/api/v1/queue/playlists",
            json={
                "name": "My Playlist",
                "notes": "Test notes",
                "owner_label": "brave_Curie",
                "items": [
                    {"track_id": tracks[0].id},
                    {"track_id": tracks[1].id},
                ],
            },
            headers={"X-Raidio-User": "brave_Curie"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Playlist"
        assert data["owner_label"] == "brave_Curie"
        assert data["id"] > 0
        assert data["estimated_time_to_play_ms"] is not None

    async def test_submit_empty_items_rejected(
        self, client, session_factory, db_with_settings, db_with_tracks
    ):
        """Rejects playlist with no items."""
        resp = await client.post(
            "/api/v1/queue/playlists",
            json={"name": "Empty", "items": []},
        )
        assert resp.status_code == 422

    async def test_submit_invalid_track_rejected(
        self, client, session_factory, db_with_settings, db_with_tracks
    ):
        """Rejects playlist with non-existent track ID."""
        resp = await client.post(
            "/api/v1/queue/playlists",
            json={
                "name": "Bad Track",
                "items": [{"track_id": 99999}],
            },
        )
        assert resp.status_code == 404

    async def test_submit_item_without_track_or_jingle_rejected(
        self, client, session_factory, db_with_settings, db_with_tracks
    ):
        """Rejects item with neither track_id nor jingle_id."""
        resp = await client.post(
            "/api/v1/queue/playlists",
            json={
                "name": "No Content",
                "items": [{"track_id": None, "jingle_id": None}],
            },
        )
        assert resp.status_code == 422

    async def test_submit_uses_header_label(
        self, client, session_factory, db_with_settings, db_with_tracks
    ):
        """X-Raidio-User header is used as owner_label."""
        resp = await client.post(
            "/api/v1/queue/playlists",
            json={
                "name": "Header Test",
                "items": [{"track_id": db_with_tracks[0].id}],
            },
            headers={"X-Raidio-User": "cosmic_Tesla"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["owner_label"] == "cosmic_Tesla"
