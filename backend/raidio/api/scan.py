"""Admin scan API — trigger and monitor library/jingle scans.

All endpoints require admin JWT (Phase 4).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select

from raidio.core.auth import require_admin
from raidio.db.models import AnalysisStatus, ScanJob, ScanKind, ScanStatus, Track
from raidio.db.session import get_session_factory
from raidio.db.settings import Settings
from raidio.scanner.library_scanner import run_library_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin/scan", tags=["admin-scan"])

# Track active scan state for WebSocket reporting
_scan_progress: dict[int, dict] = {}


class ScanResponse(BaseModel):
    scan_job_id: int
    status: str


class ScanStatusResponse(BaseModel):
    id: int
    kind: str
    started_at: datetime | None
    finished_at: datetime | None
    status: str
    tracks_added: int
    tracks_updated: int
    tracks_removed: int


async def _run_scan_background(
    scan_kind: ScanKind,
    scan_path: str,
    cover_cache_path: str,
    scan_job_id: int,
) -> None:
    """Run the scan in a background task with its own session.

    After Phase A completes, enqueues changed tracks for Phase B analysis.
    """
    settings = Settings()
    session_factory = get_session_factory(settings=settings)
    async with session_factory() as session:
        try:
            # Remember which tracks were already analyzed before scan
            pre_scan_analyzed = {
                t.id for t in (
                    await session.execute(
                        select(Track.id).where(
                            Track.analysis_status == AnalysisStatus.DONE
                        )
                    )
                ).scalars().all()
            }

            job = await run_library_scan(
                session=session,
                library_path=scan_path,
                cover_cache_path=cover_cache_path,
                kind=scan_kind,
            )
            _scan_progress[scan_job_id] = {
                "phase": "done",
                "total": job.tracks_added + job.tracks_updated,
                "done": job.tracks_added + job.tracks_updated,
                "current_path": "",
            }

            # Enqueue newly added/updated tracks for Phase B analysis
            if job.tracks_added > 0 or job.tracks_updated > 0:
                post_scan_tracks = (
                    await session.execute(
                        select(Track.id).where(
                            Track.analysis_status == AnalysisStatus.PENDING
                        )
                    )
                ).scalars().all()

                # Filter out tracks that were already analyzed
                new_for_analysis = [
                    tid for tid in post_scan_tracks if tid not in pre_scan_analyzed
                ]

                if new_for_analysis:

                    # Get or create the pool and enqueue
                    from raidio.api.admin import get_analysis_pool

                    pool = get_analysis_pool()
                    pool.enqueue_many(new_for_analysis)
                    logger.info(
                        "Enqueued %d tracks for Phase B analysis", len(new_for_analysis)
                    )

                    # Start pool if not running
                    if not pool._running:
                        await pool.start()

                    _scan_progress[scan_job_id]["phase"] = "analyzing"

        except Exception as exc:
            logger.error("Background scan failed: %s", exc)
            _scan_progress[scan_job_id] = {
                "phase": "error",
                "total": 0,
                "done": 0,
                "current_path": str(exc),
            }


@router.post("/library", response_model=ScanResponse)
async def scan_library(
    background_tasks: BackgroundTasks,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Kick off a library scan (Phase A). Returns scan_job_id."""
    settings = Settings()

    session_factory = get_session_factory(settings=settings)
    async with session_factory() as session:
        job = ScanJob(
            kind=ScanKind.LIBRARY,
            started_at=datetime.now(tz=UTC).replace(tzinfo=None),
            status=ScanStatus.RUNNING,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        scan_job_id = job.id

    _scan_progress[scan_job_id] = {
        "phase": "scanning",
        "total": 0,
        "done": 0,
        "current_path": "",
    }

    background_tasks.add_task(
        _run_scan_background,
        ScanKind.LIBRARY,
        settings.library_path,
        settings.cover_cache_abs_path,
        scan_job_id,
    )

    return ScanResponse(scan_job_id=scan_job_id, status="running")


@router.post("/jingles", response_model=ScanResponse)
async def scan_jingles(
    background_tasks: BackgroundTasks,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Kick off a jingles directory scan. Returns scan_job_id."""
    settings = Settings()

    session_factory = get_session_factory(settings=settings)
    async with session_factory() as session:
        job = ScanJob(
            kind=ScanKind.JINGLES,
            started_at=datetime.now(tz=UTC).replace(tzinfo=None),
            status=ScanStatus.RUNNING,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        scan_job_id = job.id

    _scan_progress[scan_job_id] = {
        "phase": "scanning",
        "total": 0,
        "done": 0,
        "current_path": "",
    }

    background_tasks.add_task(
        _run_scan_background,
        ScanKind.JINGLES,
        settings.jingles_path,
        settings.cover_cache_abs_path,
        scan_job_id,
    )

    return ScanResponse(scan_job_id=scan_job_id, status="running")


@router.get("/status")
async def scan_status(admin_email: Annotated[str, Depends(require_admin)]):
    """Return the most recent scan jobs."""
    settings = Settings()
    session_factory = get_session_factory(settings=settings)
    async with session_factory() as session:
        result = await session.execute(
            select(ScanJob).order_by(ScanJob.started_at.desc()).limit(10)
        )
        jobs = result.scalars().all()

    return [
        ScanStatusResponse(
            id=j.id,
            kind=j.kind.value,
            started_at=j.started_at,
            finished_at=j.finished_at,
            status=j.status.value,
            tracks_added=j.tracks_added,
            tracks_updated=j.tracks_updated,
            tracks_removed=j.tracks_removed,
        )
        for j in jobs
    ]


@router.websocket("/ws")
async def scan_websocket(websocket: WebSocket):
    """WebSocket endpoint for live scan progress updates.

    Note: WebSocket auth is handled by verifying a token query parameter,
    since the standard HTTP auth headers don't apply to WebSocket upgrades.
    """
    # Accept first, then verify token from query params
    await websocket.accept()
    try:
        # Check for token in query params
        token = websocket.query_params.get("token")
        if not token:
            await websocket.send_json({"error": "Authentication required"})
            await websocket.close(code=4001)
            return

        settings = Settings()
        from raidio.core.auth import decode_access_token

        try:
            decode_access_token(token, settings.jwt_secret)
        except Exception:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close(code=4001)
            return

        while True:
            active = {k: v for k, v in _scan_progress.items() if v["phase"] != "done"}
            if active:
                await websocket.send_json(active)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
