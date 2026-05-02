"""Raidio — FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from raidio import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database directory exists, run migrations
    from raidio.db.session import run_migrations

    run_migrations()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Raidio",
    description="Self-hosted LAN-only personal radio station",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": __version__}
