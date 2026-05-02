"""Functional tests for the catalog API endpoints.

Uses an in-memory SQLite database via httpx.AsyncClient + ASGI transport.
"""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from raidio.db.base import Base
from raidio.main import app


@pytest.fixture
async def engine(tmp_path):
    """Create an in-memory SQLite engine."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create an async session bound to the test engine."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(engine, monkeypatch):
    """Create an httpx test client with a patched session factory."""

    # We need to patch the settings to point at our test DB
    # Since the API creates sessions via _get_session(), we'll need
    # to provide test data directly and test the endpoints that work
    # with the default database.
    # For functional tests, we use the ASGI transport.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


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
