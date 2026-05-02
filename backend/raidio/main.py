"""Raidio — FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from raidio import __version__
from raidio.db.settings import Settings
from raidio.streaming.liquidsoap import LiquidsoapClient, LiquidsoapError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database directory exists, run migrations
    from raidio.db.session import run_migrations

    run_migrations()

    # Create Liquidsoap client and attempt connection (non-fatal)
    settings = Settings()
    ls_client = LiquidsoapClient(
        host=settings.liquidsoap_host,
        port=settings.liquidsoap_telnet_port,
    )
    try:
        await ls_client.connect()
    except Exception as exc:
        logger.warning(
            "Could not connect to Liquidsoap at %s:%d — "
            "streaming commands will fail until Liquidsoap is started: %s",
            settings.liquidsoap_host,
            settings.liquidsoap_telnet_port,
            exc,
        )

    app.state.liquidsoap = ls_client
    yield

    # Shutdown: close Liquidsoap connection
    await ls_client.close()


app = FastAPI(
    title="Raidio",
    description="Self-hosted LAN-only personal radio station",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": __version__}


# ── Admin queue control (auth added in Phase 4) ────────────────────


@app.post("/api/v1/admin/queue/skip")
async def skip_current_track(request: Request):
    """Skip the currently playing track in Liquidsoap.

    TODO(phase4): require admin JWT
    """
    ls_client: LiquidsoapClient = request.app.state.liquidsoap
    try:
        await ls_client.skip()
        return {"status": "skipped"}
    except LiquidsoapError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})


# ── Liquidsoap error handler ──────────────────────────────────────


@app.exception_handler(LiquidsoapError)
async def liquidsoap_error_handler(request: Request, exc: LiquidsoapError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})
