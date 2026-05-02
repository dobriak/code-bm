import asyncio
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import select

from raidio import __version__
from raidio.api import admin_router, queue_router, tracks_router
from raidio.api.ws_now_playing import get_now_playing_manager, now_playing_router
from raidio.db.base import get_session_factory
from raidio.db.models import Setting
from raidio.db.settings import get_settings
from raidio.streaming.broadcaster import Broadcaster
from raidio.streaming.liquidsoap import LiquidsoapClient, LiquidsoapSettings


async def ensure_database():
    db_path = Path("database/raidio.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)


async def run_migrations():
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "alembic", "upgrade", "head",
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Migration failed: {stderr.decode()}")


async def bootstrap_settings():
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Setting).where(Setting.id == 1))
        existing = result.scalar_one_or_none()
        if not existing:
            setting = Setting(
                id=1,
                library_path=settings.library_path,
                jingles_path=settings.jingles_path,
            )
            session.add(setting)
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_database()
    await run_migrations()
    await bootstrap_settings()

    app.state.db_session_factory = get_session_factory()

    liquidsoap_settings = LiquidsoapSettings()
    client = LiquidsoapClient(liquidsoap_settings)
    await client.connect()
    app.state.liquidsoap = client

    broadcaster = Broadcaster(app.state.db_session_factory, client)
    broadcaster.set_ws_manager(get_now_playing_manager())
    broadcaster_task = asyncio.create_task(broadcaster.start())
    app.state.broadcaster = broadcaster

    yield

    await broadcaster.stop()
    broadcaster_task.cancel()
    try:
        await broadcaster_task
    except asyncio.CancelledError:
        pass
    await client.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(title="Raidio", version=__version__, lifespan=lifespan)

    app.include_router(tracks_router, prefix="/api/v1", tags=["tracks"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(queue_router, prefix="/api/v1", tags=["queue"])
    app.include_router(now_playing_router, prefix="/api/v1", tags=["now-playing"])

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
