import asyncio
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.requests import Request

from raidio import __version__
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_database()
    await run_migrations()

    settings = LiquidsoapSettings()
    client = LiquidsoapClient(settings)
    await client.connect()
    app.state.liquidsoap = client

    yield

    await client.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(title="Raidio", version=__version__, lifespan=lifespan)

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.post("/api/v1/admin/queue/skip")
    async def skip_track(request: Request):
        liquidsoap: LiquidsoapClient = request.app.state.liquidsoap
        try:
            await liquidsoap.skip()
            return {"status": "ok", "action": "skip"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return app


app = create_app()
