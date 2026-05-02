"""Functional tests for the catalog API endpoints.

Uses a temp-file SQLite database via httpx.AsyncClient + ASGI transport.
"""

from __future__ import annotations

import httpx


class TestHealthEndpoint:
    async def test_health(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestTracksEndpoint:
    async def test_tracks_empty(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/tracks")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["next_cursor"] is None


class TestArtistsEndpoint:
    async def test_artists_empty(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/artists")
        assert response.status_code == 200
        assert response.json() == []


class TestAlbumsEndpoint:
    async def test_albums_empty(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/albums")
        assert response.status_code == 200
        assert response.json() == []


class TestGenresEndpoint:
    async def test_genres_empty(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/genres")
        assert response.status_code == 200
        assert response.json() == []


class TestJinglesEndpoint:
    async def test_jingles_empty(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/jingles")
        assert response.status_code == 200
        assert response.json() == []


class TestTrackNotFound:
    async def test_get_nonexistent_track(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/tracks/99999")
        assert response.status_code == 404

    async def test_get_nonexistent_cover(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/tracks/99999/cover")
        assert response.status_code == 404


class TestRandomTrackEndpoint:
    async def test_random_no_tracks(self, client: httpx.AsyncClient):
        """Returns 404 when no tracks in library."""
        resp = await client.get("/api/v1/tracks/random")
        assert resp.status_code == 404

    async def test_random_with_tracks(
        self, client: httpx.AsyncClient, session_factory, db_with_settings, db_with_tracks
    ):
        """Returns a track when library has tracks."""
        resp = await client.get("/api/v1/tracks/random")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["artist"] is not None
