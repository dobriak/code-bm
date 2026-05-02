"""Raidio — FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from raidio import __version__
from raidio.api.admin import router as admin_router
from raidio.api.catalog import router as catalog_router
from raidio.api.queue import router as queue_router
from raidio.api.scan import router as scan_router
from raidio.db.settings import Settings
from raidio.streaming.broadcaster import Broadcaster
from raidio.streaming.liquidsoap import LiquidsoapClient, LiquidsoapError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database directory exists, run migrations
    from raidio.db.bootstrap import ensure_default_settings
    from raidio.db.session import get_session_factory, run_migrations

    run_migrations()

    settings = Settings()

    # Bootstrap default settings row
    session_factory = get_session_factory(settings=settings)
    async with session_factory() as session:
        await ensure_default_settings(session, settings)

    # Create Liquidsoap client and attempt connection (non-fatal)
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

    # Start the broadcaster (long-running scheduler task)
    broadcaster = Broadcaster(
        session_factory=session_factory,
        ls_client=ls_client,
    )
    await broadcaster.start()
    app.state.broadcaster = broadcaster

    yield

    # Shutdown: stop broadcaster, analysis pool, close Liquidsoap connection
    await broadcaster.stop()

    # Stop the analysis worker pool if it was started
    try:
        from raidio.api.admin import get_analysis_pool

        pool = get_analysis_pool()
        if pool._running:
            await pool.stop()
    except Exception:
        pass

    await ls_client.close()


app = FastAPI(
    title="Raidio",
    description="Self-hosted LAN-only personal radio station",
    version=__version__,
    lifespan=lifespan,
)


# Include API routers
app.include_router(catalog_router)
app.include_router(scan_router)
app.include_router(queue_router)
app.include_router(admin_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": __version__}


# ── Liquidsoap error handler ──────────────────────────────────────


@app.exception_handler(LiquidsoapError)
async def liquidsoap_error_handler(request: Request, exc: LiquidsoapError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})
