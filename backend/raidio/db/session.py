"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

import subprocess
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from raidio.db.settings import Settings, get_settings


_cached_engine = None
_cached_factory = None


def get_engine(settings: Settings | None = None):
    """Get or create the cached async SQLAlchemy engine for SQLite."""
    global _cached_engine
    if _cached_engine is not None:
        return _cached_engine
    if settings is None:
        settings = get_settings()

    db_path = settings.database_abs_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"sqlite+aiosqlite:///{db_path}"
    _cached_engine = create_async_engine(
        url,
        connect_args={"autocommit": False},
        echo=False,
    )
    return _cached_engine


def get_session_factory(engine=None, settings: Settings | None = None):
    """Get or create the cached async_sessionmaker bound to the engine."""
    global _cached_factory
    if engine is None:
        if _cached_factory is not None:
            return _cached_factory
        engine = get_engine(settings)
        _cached_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return _cached_factory
    # Explicit engine (e.g. tests) — don't cache
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def reset_session_cache():
    """Reset cached engine and session factory. For use in tests."""
    global _cached_engine, _cached_factory
    _cached_engine = None
    _cached_factory = None


def run_migrations():
    """Run Alembic migrations on startup.

    Uses subprocess to avoid event loop conflicts when called from
    an async context (e.g. FastAPI lifespan inside uvicorn).
    """
    settings = get_settings()
    db_path = settings.database_abs_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    alembic_dir = Path(__file__).resolve().parents[3] / "backend"
    ini_path = alembic_dir / "alembic.ini"

    subprocess.run(
        ["alembic", "-c", str(ini_path), "upgrade", "head"],
        cwd=str(alembic_dir),
        check=True,
        capture_output=True,
    )
