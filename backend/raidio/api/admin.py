from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select

from raidio.core.auth import (
    LoginRequest,
    TokenResponse,
    authenticate_admin,
    require_admin,
)
from raidio.db.models import (
    Jingle,
    LiveQueueItem,
    Playlist,
    PlaylistItem,
    ScanJob,
    Setting,
    Track,
)
from raidio.scanner.audio_analysis import reanalyze_track
from raidio.scanner.library_scanner import ScanProgress, scan_jingles_to_db, scan_library_to_db

if TYPE_CHECKING:
    from raidio.streaming.liquidsoap import LiquidsoapClient

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


async def get_db_session_factory(request: Request):
    return request.app.state.db_session_factory


async def _run_scan_library(
    session_factory,
    progress_queue: asyncio.Queue,
    path: str | None,
):
    async def progress_callback():
        while True:
            progress = await progress_queue.get()
            if progress is None:
                break
            await manager.broadcast({
                "phase": progress.phase,
                "total": progress.total,
                "done": progress.done,
                "current_path": progress.current_path,
                "errors": progress.errors,
            })

    progress_task = asyncio.create_task(progress_callback())

    async with session_factory() as session:
        await scan_library_to_db(session, path)
        await session.commit()

    await progress_queue.put(None)
    await progress_task


async def _run_scan_jingles(
    session_factory,
    progress_queue: asyncio.Queue,
    path: str | None,
):
    async def progress_callback():
        while True:
            progress = await progress_queue.get()
            if progress is None:
                break
            await manager.broadcast({
                "phase": progress.phase,
                "total": progress.total,
                "done": progress.done,
                "current_path": progress.current_path,
                "errors": progress.errors,
            })

    progress_task = asyncio.create_task(progress_callback())

    async with session_factory() as session:
        await scan_jingles_to_db(session, path)
        await session.commit()

    await progress_queue.put(None)
    await progress_task


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    token = await authenticate_admin(body.email, body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=token)


@router.post("/scan/library")
async def scan_library(
    request: Request,
    path: str | None = None,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    progress_queue: asyncio.Queue[ScanProgress | None] = asyncio.Queue()

    task = asyncio.create_task(
        _run_scan_library(session_factory, progress_queue, path)
    )

    return {"status": "started", "task_id": id(task)}


@router.post("/scan/jingles")
async def scan_jingles(
    request: Request,
    path: str | None = None,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    progress_queue: asyncio.Queue[ScanProgress | None] = asyncio.Queue()

    task = asyncio.create_task(
        _run_scan_jingles(session_factory, progress_queue, path)
    )

    return {"status": "started", "task_id": id(task)}


@router.get("/scan/status")
async def scan_status(
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        result = await session.execute(
            select(ScanJob)
            .order_by(ScanJob.started_at.desc())
            .limit(10)
        )
        jobs = result.scalars().all()

        return {
            "jobs": [
                {
                    "id": j.id,
                    "kind": j.kind.value,
                    "status": j.status.value,
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                    "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                    "tracks_added": j.tracks_added,
                    "tracks_updated": j.tracks_updated,
                    "tracks_removed": j.tracks_removed,
                    "errors": json.loads(j.errors_json) if j.errors_json else [],
                }
                for j in jobs
            ]
        }


@router.websocket("/scan")
async def scan_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                await websocket.send_json({"received": msg})
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.get("/stats")
async def get_stats(
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        track_count = await session.scalar(select(func.count(Track.id)))
        artist_count = await session.scalar(
            select(func.count(func.distinct(Track.artist))).where(Track.artist.isnot(None))
        )
        album_count = await session.scalar(
            select(func.count(func.distinct(Track.album))).where(Track.album.isnot(None))
        )
        genre_count = await session.scalar(
            select(func.count(func.distinct(Track.genre))).where(Track.genre.isnot(None))
        )
        total_playtime_ms = await session.scalar(
            select(func.sum(Track.duration_ms)).where(Track.duration_ms.isnot(None))
        )
        jingle_count = await session.scalar(select(func.count(Jingle.id)))
        queue_count = await session.scalar(
            select(func.count(LiveQueueItem.id)).where(LiveQueueItem.state == "pending")
        )

        return {
            "tracks": track_count or 0,
            "artists": artist_count or 0,
            "albums": album_count or 0,
            "genres": genre_count or 0,
            "total_playtime_ms": total_playtime_ms or 0,
            "jingles": jingle_count or 0,
            "queue_length": queue_count or 0,
            "broadcast_status": "running",
        }


@router.get("/settings")
async def get_settings(
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        result = await session.execute(select(Setting).where(Setting.id == 1))
        setting = result.scalar_one_or_none()
        if not setting:
            raise HTTPException(status_code=404, detail="Settings not found")

        playlists_result = await session.execute(
            select(Playlist).where(Playlist.kind == "auto")
        )
        auto_playlists = playlists_result.scalars().all()

        return {
            "library_path": setting.library_path,
            "jingles_path": setting.jingles_path,
            "idle_behavior": setting.idle_behavior.value,
            "default_auto_playlist_id": setting.default_auto_playlist_id,
            "crossfade_enabled": setting.crossfade_enabled,
            "crossfade_duration_ms": setting.crossfade_duration_ms,
            "gapless_enabled": setting.gapless_enabled,
            "jingle_duck_db": setting.jingle_duck_db,
            "icecast_buffer_offset_ms": setting.icecast_buffer_offset_ms,
            "min_quiet_duration_s": setting.min_quiet_duration_s,
            "auto_playlists": [
                {"id": p.id, "name": p.name} for p in auto_playlists
            ],
        }


@router.put("/settings")
async def put_settings(
    request: Request,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    body = await request.json()
    async with session_factory() as session:
        result = await session.execute(select(Setting).where(Setting.id == 1))
        setting = result.scalar_one_or_none()
        if not setting:
            raise HTTPException(status_code=404, detail="Settings not found")

        if "library_path" in body:
            setting.library_path = body["library_path"]
        if "jingles_path" in body:
            setting.jingles_path = body["jingles_path"]
        if "idle_behavior" in body:
            setting.idle_behavior = body["idle_behavior"]
        if "default_auto_playlist_id" in body:
            setting.default_auto_playlist_id = body["default_auto_playlist_id"]
        if "crossfade_enabled" in body:
            setting.crossfade_enabled = body["crossfade_enabled"]
        if "crossfade_duration_ms" in body:
            setting.crossfade_duration_ms = body["crossfade_duration_ms"]
        if "gapless_enabled" in body:
            setting.gapless_enabled = body["gapless_enabled"]
        if "jingle_duck_db" in body:
            setting.jingle_duck_db = body["jingle_duck_db"]
        if "icecast_buffer_offset_ms" in body:
            setting.icecast_buffer_offset_ms = body["icecast_buffer_offset_ms"]
        if "min_quiet_duration_s" in body:
            setting.min_quiet_duration_s = body["min_quiet_duration_s"]

        await session.commit()

        client: LiquidsoapClient = request.app.state.liquidsoap
        await client.set_var("crossfade_enabled", "true" if setting.crossfade_enabled else "false")
        await client.set_var("crossfade_duration", str(setting.crossfade_duration_ms / 1000.0))
        await client.set_jingle_duck_db(float(setting.jingle_duck_db))

    return {"status": "ok"}


@router.get("/queue")
async def get_queue(
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        queue_result = await session.execute(
            select(LiveQueueItem).order_by(LiveQueueItem.position)
        )
        queue_items = queue_result.scalars().all()

        playlists_result = await session.execute(
            select(Playlist).where(Playlist.kind == "user_session")
        )
        playlists = playlists_result.scalars().all()

        return {
            "queue": [
                {
                    "id": item.id,
                    "position": item.position,
                    "track_id": item.track_id,
                    "jingle_id": item.jingle_id,
                    "state": item.state.value,
                    "enqueued_at": item.enqueued_at.isoformat() if item.enqueued_at else None,
                }
                for item in queue_items
            ],
            "active_playlists": [
                {"id": p.id, "name": p.name, "owner_label": p.owner_label}
                for p in playlists
            ],
        }


@router.put("/queue/reorder")
async def reorder_queue(
    request: Request,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    body = await request.json()
    items = body.get("items", [])
    async with session_factory() as session:
        for pos, item_id in enumerate(items):
            result = await session.execute(
                select(LiveQueueItem).where(LiveQueueItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if item:
                item.position = pos
        await session.commit()
    return {"status": "ok"}


@router.delete("/queue/{item_id}")
async def delete_queue_item(
    item_id: int,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        result = await session.execute(
            select(LiveQueueItem).where(LiveQueueItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item:
            await session.delete(item)
            await session.commit()
    return {"status": "ok"}


@router.post("/queue/skip")
async def skip_queue(
    request: Request,
    _admin_email: str = Depends(require_admin),
):
    client: LiquidsoapClient = request.app.state.liquidsoap
    await client.skip()
    return {"status": "ok"}


@router.post("/queue/insert-jingle/{jingle_id}")
async def insert_jingle(
    jingle_id: int,
    request: Request,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        result = await session.execute(
            select(Jingle).where(Jingle.id == jingle_id)
        )
        jingle = result.scalar_one_or_none()
        if not jingle:
            raise HTTPException(status_code=404, detail="Jingle not found")

        client: LiquidsoapClient = request.app.state.liquidsoap
        await client.push_jingle(f"file://{jingle.path}")

    return {"status": "ok"}


@router.post("/auto-playlists")
async def create_auto_playlist(
    request: Request,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    body = await request.json()
    async with session_factory() as session:
        playlist = Playlist(
            name=body["name"],
            notes=body.get("notes"),
            kind="auto",
        )
        session.add(playlist)
        await session.flush()

        for idx, item_data in enumerate(body.get("items", [])):
            playlist_item = PlaylistItem(
                playlist_id=playlist.id,
                position=idx,
                track_id=item_data.get("track_id"),
                jingle_id=item_data.get("jingle_id"),
            )
            session.add(playlist_item)

        await session.commit()
        return {"id": playlist.id}


@router.get("/auto-playlists")
async def list_auto_playlists(
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        result = await session.execute(
            select(Playlist).where(Playlist.kind == "auto")
        )
        playlists = result.scalars().all()
        return {
            "playlists": [
                {
                    "id": p.id,
                    "name": p.name,
                    "notes": p.notes,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in playlists
            ]
        }


@router.get("/auto-playlists/{playlist_id}")
async def get_auto_playlist(
    playlist_id: int,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        result = await session.execute(
            select(Playlist).where(Playlist.id == playlist_id, Playlist.kind == "auto")
        )
        playlist = result.scalar_one_or_none()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        items_result = await session.execute(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position)
        )
        items = items_result.scalars().all()

        return {
            "id": playlist.id,
            "name": playlist.name,
            "notes": playlist.notes,
            "items": [
                {
                    "id": item.id,
                    "position": item.position,
                    "track_id": item.track_id,
                    "jingle_id": item.jingle_id,
                    "overlay_at_ms": item.overlay_at_ms,
                }
                for item in items
            ],
        }


@router.put("/auto-playlists/{playlist_id}")
async def update_auto_playlist(
    playlist_id: int,
    request: Request,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    body = await request.json()
    async with session_factory() as session:
        result = await session.execute(
            select(Playlist).where(Playlist.id == playlist_id, Playlist.kind == "auto")
        )
        playlist = result.scalar_one_or_none()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        playlist.name = body.get("name", playlist.name)
        playlist.notes = body.get("notes", playlist.notes)

        if "items" in body:
            await session.execute(
                PlaylistItem.__table__.delete().where(
                    PlaylistItem.playlist_id == playlist_id
                )
            )
            for idx, item_data in enumerate(body["items"]):
                playlist_item = PlaylistItem(
                    playlist_id=playlist.id,
                    position=idx,
                    track_id=item_data.get("track_id"),
                    jingle_id=item_data.get("jingle_id"),
                    overlay_at_ms=item_data.get("overlay_at_ms"),
                )
                session.add(playlist_item)

        await session.commit()
    return {"status": "ok"}


@router.delete("/auto-playlists/{playlist_id}")
async def delete_auto_playlist(
    playlist_id: int,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        result = await session.execute(
            select(Playlist).where(Playlist.id == playlist_id, Playlist.kind == "auto")
        )
        playlist = result.scalar_one_or_none()
        if playlist:
            await session.delete(playlist)
            await session.commit()
    return {"status": "ok"}


@router.post("/tracks/{track_id}/reanalyze")
async def reanalyze(
    track_id: int,
    request: Request,
    session_factory = Depends(get_db_session_factory),
    _admin_email: str = Depends(require_admin),
):
    async with session_factory() as session:
        await reanalyze_track(session, track_id)
    return {"status": "ok"}
