"""Functional tests for the queue API endpoints."""

from __future__ import annotations

import asyncio
import contextlib

import pytest
from httpx import ASGITransport, AsyncClient

from raidio.db.models import (
    Jingle,
    LiveQueueState,
    Playlist,
    PlaylistItem,
    PlaylistKind,
    Track,
)
from raidio.db.session import get_engine, get_session_factory
from raidio.db.settings import Settings
from raidio.main import app

# Use an in-memory SQLite for tests
TEST_DB_PATH = ":memory:"


@pytest.fixture
async def session_factory():
    """Create a session factory backed by an in-memory SQLite database."""
    from raidio.db.base import Base

    engine = get_engine()
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory(engine=engine)
    yield factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(session_factory):
    """Create an httpx test client with the app."""
    # Monkey-patch the session factory used by the app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_with_tracks(session_factory):
    """Insert test tracks into the database."""
    async with session_factory() as session:
        tracks = []
        for i in range(5):
            track = Track(
                path=f"/music/track_{i}.mp3",
                file_hash=f"hash_{i}",
                artist=f"Artist {i}",
                album=f"Album {i}",
                title=f"Track {i}",
                genre="Rock",
                duration_ms=200_000 + i * 10_000,
            )
            session.add(track)
            tracks.append(track)
        await session.commit()
        for t in tracks:
            await session.refresh(t)
    return [t for t in tracks]


class TestNowPlayingEndpoint:
    """Tests for GET /api/v1/now-playing."""

    async def test_empty_queue(self, client, session_factory):
        """Returns empty structure when nothing is playing."""
        resp = await client.get("/api/v1/now-playing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current"] is None
        assert data["prev"] == []
        assert data["next"] == []
        assert data["buffer_offset_ms"] > 0


class TestRandomTrackEndpoint:
    """Tests for GET /api/v1/tracks/random."""

    async def test_no_tracks(self, client, session_factory):
        """Returns 404 when library is empty."""
        resp = await client.get("/api/v1/tracks/random")
        assert resp.status_code == 404

    async def test_returns_random_track(self, client, session_factory, db_with_tracks):
        """Returns a track when library has tracks."""
        resp = await client.get("/api/v1/tracks/random")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "title" in data


class TestSubmitPlaylistEndpoint:
    """Tests for POST /api/v1/queue/playlists."""

    async def test_submit_valid_playlist(self, client, session_factory, db_with_tracks):
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

    async def test_submit_empty_items_rejected(self, client, session_factory, db_with_tracks):
        """Rejects playlist with no items."""
        resp = await client.post(
            "/api/v1/queue/playlists",
            json={"name": "Empty", "items": []},
        )
        assert resp.status_code == 422

    async def test_submit_invalid_track_rejected(self, client, session_factory, db_with_tracks):
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
        self, client, session_factory, db_with_tracks
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

    async def test_submit_uses_header_label(self, client, session_factory, db_with_tracks):
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
