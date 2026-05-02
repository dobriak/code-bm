"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

import subprocess
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from raidio.db.settings import Settings


def get_engine(settings: Settings | None = None):
    """Create the async SQLAlchemy engine for SQLite."""
    if settings is None:
        settings = Settings()

    db_path = settings.database_abs_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"sqlite+aiosqlite:///{db_path}"
    return create_async_engine(
        url,
        connect_args={"autocommit": False},
        echo=False,
    )


def get_session_factory(engine=None, settings: Settings | None = None):
    """Create an async_sessionmaker bound to the engine."""
    if engine is None:
        engine = get_engine(settings)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def run_migrations():
    """Run Alembic migrations on startup.

    Uses subprocess to avoid event loop conflicts when called from
    an async context (e.g. FastAPI lifespan inside uvicorn).
    """
    settings = Settings()
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
