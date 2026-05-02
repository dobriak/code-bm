"""Functional tests for admin API endpoints with authentication."""

from __future__ import annotations

import pytest

# Test constants (must match conftest.py patched values)
TEST_JWT_SECRET = "test-secret-key"
TEST_ADMIN_EMAIL = "admin@test.com"
TEST_ADMIN_PASSWORD_HASH = "$2b$12$EkJqXUlEq1fRCA6oIdiqv.xb/ZDwYGX/3em/XMT6fcxg3m0qM6P1m"


class TestAdminLoginEndpoint:
    """Tests for POST /api/v1/admin/login."""

    async def test_login_success(self, client):
        """Returns access_token for valid credentials."""
        resp = await client.post(
            "/api/v1/admin/login",
            json={"email": TEST_ADMIN_EMAIL, "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        """Returns 401 for wrong password."""
        resp = await client.post(
            "/api/v1/admin/login",
            json={"email": TEST_ADMIN_EMAIL, "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    async def test_login_wrong_email(self, client):
        """Returns 401 for wrong email."""
        resp = await client.post(
            "/api/v1/admin/login",
            json={"email": "wrong@test.com", "password": "password123"},
        )
        assert resp.status_code == 401


class TestAdminEndpointsRequireAuth:
    """Tests that admin endpoints return 401 without JWT."""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/admin/stats"),
            ("GET", "/api/v1/admin/settings"),
            ("PUT", "/api/v1/admin/settings"),
            ("GET", "/api/v1/admin/queue"),
            ("POST", "/api/v1/admin/queue/skip"),
            ("POST", "/api/v1/admin/scan/library"),
            ("GET", "/api/v1/admin/scan/status"),
        ],
    )
    async def test_unauthenticated_returns_401(self, client, method, path):
        """All admin endpoints require JWT."""
        if method == "GET":
            resp = await client.get(path)
        elif method == "PUT":
            resp = await client.put(path, json={})
        else:
            resp = await client.post(path)

        assert resp.status_code == 401


class TestAdminStatsEndpoint:
    """Tests for GET /api/v1/admin/stats."""

    async def test_stats_empty_db(self, client, admin_headers, session_factory, db_with_settings):
        """Returns zero counts for empty database."""
        resp = await client.get("/api/v1/admin/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["track_count"] == 0
        assert data["artist_count"] == 0
        assert data["broadcast_status"] == "idle"

    async def test_stats_with_tracks(
        self, client, admin_headers, session_factory, db_with_settings, db_with_tracks
    ):
        """Returns correct counts with tracks."""
        resp = await client.get("/api/v1/admin/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["track_count"] == 5
        assert data["artist_count"] == 5
        assert data["total_playtime_ms"] > 0


class TestAdminSettingsEndpoint:
    """Tests for GET/PUT /api/v1/admin/settings."""

    async def test_get_settings(self, client, admin_headers, session_factory, db_with_settings):
        """Returns current settings."""
        resp = await client.get("/api/v1/admin/settings", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["crossfade_enabled"] is False
        assert data["crossfade_duration_ms"] == 4000
        assert data["jingle_duck_db"] == -12.0

    async def test_update_settings(self, client, admin_headers, session_factory, db_with_settings):
        """Updates settings and returns new values."""
        resp = await client.put(
            "/api/v1/admin/settings",
            headers=admin_headers,
            json={
                "crossfade_enabled": True,
                "crossfade_duration_ms": 5000,
                "jingle_duck_db": -18.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["crossfade_enabled"] is True
        assert data["crossfade_duration_ms"] == 5000
        assert data["jingle_duck_db"] == -18.0

    async def test_update_settings_validation(
        self, client, admin_headers, session_factory, db_with_settings
    ):
        """Rejects out-of-range values."""
        resp = await client.put(
            "/api/v1/admin/settings",
            headers=admin_headers,
            json={"crossfade_duration_ms": 20000},  # max is 10000
        )
        assert resp.status_code == 422


class TestReanalyzeEndpoint:
    """Tests for POST /api/v1/admin/tracks/{id}/reanalyze."""

    async def test_reanalyze_nonexistent_track(self, client, admin_headers):
        """Returns 404 for non-existent track."""
        resp = await client.post(
            "/api/v1/admin/tracks/99999/reanalyze",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    async def test_reanalyze_existing_track(
        self, client, admin_headers, session_factory, db_with_tracks
    ):
        """Clears analysis and enqueues for re-analysis."""
        track = db_with_tracks[0]
        resp = await client.post(
            f"/api/v1/admin/tracks/{track.id}/reanalyze",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "enqueued"


class TestAutoPlaylistsCrud:
    """Tests for auto-playlist CRUD endpoints."""

    async def test_list_empty(self, client, admin_headers, session_factory, db_with_settings):
        """Returns empty list when no auto-playlists exist."""
        resp = await client.get("/api/v1/admin/auto-playlists", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_auto_playlist(
        self, client, admin_headers, session_factory, db_with_settings, db_with_tracks
    ):
        """Creates an auto-playlist with items."""
        tracks = db_with_tracks
        resp = await client.post(
            "/api/v1/admin/auto-playlists",
            headers=admin_headers,
            json={
                "name": "My Auto",
                "items": [
                    {"track_id": tracks[0].id},
                    {"track_id": tracks[1].id},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Auto"
        assert data["item_count"] == 2

    async def test_delete_auto_playlist(
        self, client, admin_headers, session_factory, db_with_settings, db_with_tracks
    ):
        """Deletes an auto-playlist."""
        tracks = db_with_tracks
        # Create first
        create_resp = await client.post(
            "/api/v1/admin/auto-playlists",
            headers=admin_headers,
            json={
                "name": "To Delete",
                "items": [{"track_id": tracks[0].id}],
            },
        )
        pl_id = create_resp.json()["id"]

        # Delete it
        resp = await client.delete(
            f"/api/v1/admin/auto-playlists/{pl_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

        # Verify it's gone
        list_resp = await client.get(
            "/api/v1/admin/auto-playlists",
            headers=admin_headers,
        )
        assert len(list_resp.json()) == 0

    async def test_set_default_auto_playlist(
        self, client, admin_headers, session_factory, db_with_settings, db_with_tracks
    ):
        """Sets and unsets default auto-playlist."""
        tracks = db_with_tracks
        create_resp = await client.post(
            "/api/v1/admin/auto-playlists",
            headers=admin_headers,
            json={
                "name": "Default PL",
                "items": [{"track_id": tracks[0].id}],
            },
        )
        pl_id = create_resp.json()["id"]

        # Set as default
        resp = await client.put(
            f"/api/v1/admin/auto-playlists/{pl_id}",
            headers=admin_headers,
            json={"is_default": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_default"] is True
