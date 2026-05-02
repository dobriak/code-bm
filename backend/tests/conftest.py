"""Shared test fixtures for Raidio backend tests.

Patches Settings to use test database and JWT secret so all routes
work with a controlled temp-file SQLite database.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from raidio.db.base import Base
from raidio.db.session import get_session_factory
from raidio.db.settings import Settings

# Test constants
TEST_JWT_SECRET = "test-secret-key"
TEST_ADMIN_EMAIL = "admin@test.com"

# bcrypt hash of "password123" — generated with bcrypt 5.x
TEST_ADMIN_PASSWORD_HASH = "$2b$12$EkJqXUlEq1fRCA6oIdiqv.xb/ZDwYGX/3em/XMT6fcxg3m0qM6P1m"


def _make_test_settings(tmp_path: Path) -> Settings:
    """Create a Settings instance with test values."""
    return Settings(
        admin_email=TEST_ADMIN_EMAIL,
        admin_password_hash=TEST_ADMIN_PASSWORD_HASH,
        jwt_secret=TEST_JWT_SECRET,
        library_path=str(tmp_path / "music"),
        jingles_path=str(tmp_path / "jingles"),
        cover_cache_path=str(tmp_path / "covers"),
        database_path=str(tmp_path / "test.db"),
        liquidsoap_host="127.0.0.1",
        liquidsoap_telnet_port=1234,
    )


@pytest.fixture(autouse=True)
def _patch_settings(tmp_path, monkeypatch):
    """Patch Settings in all modules to use test database and JWT secret.

    This runs for every test so that routes using Settings() get test values.
    """
    test_settings = _make_test_settings(tmp_path)

    # Patch the Settings class in every module that imports it
    modules_to_patch = [
        "raidio.api.admin",
        "raidio.api.catalog",
        "raidio.api.queue",
        "raidio.api.scan",
        "raidio.core.auth",
        "raidio.db.session",
    ]
    for module_name in modules_to_patch:
        monkeypatch.setattr(
            f"{module_name}.Settings",
            lambda: test_settings,
        )


@pytest.fixture
async def engine(tmp_path):
    """Create a temp-file SQLite engine and create all tables."""
    db_path = tmp_path / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"autocommit": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create FTS5 virtual table
        from raidio.db.fts import create_fts_table

        await conn.run_sync(create_fts_table)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session_factory(engine):
    """Create a session factory bound to the test engine."""
    return get_session_factory(engine=engine)


@pytest.fixture
async def client(engine):
    """Create an httpx test client with the FastAPI app.

    Depends on engine to ensure database is created before the client starts.
    """
    from raidio.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def admin_token():
    """Create a valid admin JWT for testing."""
    from raidio.core.auth import create_access_token

    return create_access_token(TEST_JWT_SECRET, TEST_ADMIN_EMAIL)


@pytest.fixture
async def admin_headers(admin_token):
    """Create auth headers for admin requests."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def db_with_settings(session_factory):
    """Insert a default settings row."""
    from raidio.db.models import Setting

    async with session_factory() as session:
        setting = Setting(
            library_path="/music",
            jingles_path="/jingles",
            idle_behavior="random",
            crossfade_enabled=False,
            crossfade_duration_ms=4000,
            gapless_enabled=True,
            jingle_duck_db=-12.0,
            icecast_buffer_offset_ms=3000,
            min_quiet_duration_s=2.0,
        )
        session.add(setting)
        await session.commit()


@pytest.fixture
async def db_with_tracks(session_factory):
    """Insert test tracks."""
    from raidio.db.models import Track

    tracks = []
    async with session_factory() as session:
        for i in range(5):
            track = Track(
                path=f"/music/track_{i}.mp3",
                file_hash=f"hash_{i}",
                artist=f"Artist {i}",
                album=f"Album {i}",
                title=f"Track {i}",
                genre="Rock",
                duration_ms=300_000 + i * 10_000,
            )
            session.add(track)
            tracks.append(track)
        await session.commit()
        for t in tracks:
            await session.refresh(t)
    return tracks
