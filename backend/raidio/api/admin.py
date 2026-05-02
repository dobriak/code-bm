"""Admin API — authentication, stats, settings, queue management, auto-playlists, jingles, audio analysis.

All endpoints require admin JWT unless noted.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from raidio.core.auth import (
    LoginRequest,
    TokenResponse,
    create_access_token,
    require_admin,
    verify_password,
)
from raidio.db.models import (
    AnalysisStatus,
    IdleBehavior,
    Jingle,
    LiveQueueItem,
    LiveQueueState,
    Playlist,
    PlaylistItem,
    PlaylistKind,
    QuietPassage,
    Setting,
    Track,
)
from raidio.db.session import get_session_factory
from raidio.db.settings import Settings
from raidio.scanner.audio_analysis import AnalysisWorkerPool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# ── Audio analysis worker pool (singleton) ─────────────────────────
_analysis_pool: AnalysisWorkerPool | None = None


def get_analysis_pool() -> AnalysisWorkerPool:
    """Get or create the singleton analysis worker pool."""
    global _analysis_pool
    if _analysis_pool is None:
        settings = Settings()
        _analysis_pool = AnalysisWorkerPool(
            session_factory=get_session_factory(settings=settings),
            min_quiet_duration_s=settings.min_quiet_duration_s
            if hasattr(settings, "min_quiet_duration_s")
            else 2.0,
        )
    return _analysis_pool


# ── 4.1: Login ────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def admin_login(body: LoginRequest):
    """Authenticate admin and return JWT token.

    Generic error message on failure (no info about which field is wrong).
    """
    settings = Settings()

    if body.email != settings.admin_email:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, settings.admin_password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_access_token(settings.jwt_secret, settings.admin_email)
    return TokenResponse(access_token=token)


# ── 4.3: Admin dashboard stats ────────────────────────────────────


class StatsResponse(BaseModel):
    track_count: int
    artist_count: int
    album_count: int
    genre_count: int
    total_playtime_ms: int
    queue_length: int
    broadcast_status: str


@router.get("/stats", response_model=StatsResponse)
async def admin_stats(admin_email: Annotated[str, Depends(require_admin)]):
    """Get admin dashboard statistics."""
    factory = get_session_factory()
    async with factory() as session:
        track_count = (await session.execute(select(func.count()).select_from(Track))).scalar() or 0
        artist_count = (
            await session.execute(
                select(func.count(func.distinct(Track.artist))).where(Track.artist.isnot(None))
            )
        ).scalar() or 0
        album_count = (
            await session.execute(
                select(func.count(func.distinct(Track.album))).where(Track.album.isnot(None))
            )
        ).scalar() or 0
        genre_count = (
            await session.execute(
                select(func.count(func.distinct(Track.genre))).where(Track.genre.isnot(None))
            )
        ).scalar() or 0
        total_playtime_ms = (
            await session.execute(
                select(func.coalesce(func.sum(Track.duration_ms), 0)).where(
                    Track.duration_ms.isnot(None)
                )
            )
        ).scalar() or 0
        queue_length = (
            await session.execute(
                select(func.count())
                .select_from(LiveQueueItem)
                .where(LiveQueueItem.state.in_([LiveQueueState.PENDING, LiveQueueState.PLAYING]))
            )
        ).scalar() or 0

        # Determine broadcast status
        playing = (
            await session.execute(
                select(func.count())
                .select_from(LiveQueueItem)
                .where(LiveQueueItem.state == LiveQueueState.PLAYING)
            )
        ).scalar() or 0
        broadcast_status = "playing" if playing > 0 else "idle"

    return StatsResponse(
        track_count=track_count,
        artist_count=artist_count,
        album_count=album_count,
        genre_count=genre_count,
        total_playtime_ms=total_playtime_ms,
        queue_length=queue_length,
        broadcast_status=broadcast_status,
    )


# ── 4.4: Settings ─────────────────────────────────────────────────


class SettingsResponse(BaseModel):
    id: int
    library_path: str
    jingles_path: str
    idle_behavior: str
    default_auto_playlist_id: int | None
    crossfade_enabled: bool
    crossfade_duration_ms: int
    gapless_enabled: bool
    jingle_duck_db: float
    icecast_buffer_offset_ms: int
    min_quiet_duration_s: float


class SettingsUpdate(BaseModel):
    library_path: str | None = None
    jingles_path: str | None = None
    idle_behavior: str | None = None
    default_auto_playlist_id: int | None = None
    crossfade_enabled: bool | None = None
    crossfade_duration_ms: int | None = Field(None, ge=0, le=10000)
    gapless_enabled: bool | None = None
    jingle_duck_db: float | None = Field(None, ge=-24.0, le=0.0)
    icecast_buffer_offset_ms: int | None = Field(None, ge=0, le=10000)
    min_quiet_duration_s: float | None = Field(None, ge=1.0, le=10.0)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(admin_email: Annotated[str, Depends(require_admin)]):
    """Get current admin settings."""
    factory = get_session_factory()
    async with factory() as session:
        setting = await session.get(Setting, 1)
        if not setting:
            raise HTTPException(status_code=500, detail="Settings row not found")

        return SettingsResponse(
            id=setting.id,
            library_path=setting.library_path,
            jingles_path=setting.jingles_path,
            idle_behavior=setting.idle_behavior.value,
            default_auto_playlist_id=setting.default_auto_playlist_id,
            crossfade_enabled=setting.crossfade_enabled,
            crossfade_duration_ms=setting.crossfade_duration_ms,
            gapless_enabled=setting.gapless_enabled,
            jingle_duck_db=setting.jingle_duck_db,
            icecast_buffer_offset_ms=setting.icecast_buffer_offset_ms,
            min_quiet_duration_s=setting.min_quiet_duration_s,
        )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    admin_email: Annotated[str, Depends(require_admin)],
    request: object = None,
):
    """Update admin settings. Triggers Liquidsoap set_var for crossfade changes."""
    factory = get_session_factory()
    async with factory() as session:
        setting = await session.get(Setting, 1)
        if not setting:
            raise HTTPException(status_code=500, detail="Settings row not found")

        # Apply updates
        updates: dict = {}
        if body.library_path is not None:
            setting.library_path = body.library_path
        if body.jingles_path is not None:
            setting.jingles_path = body.jingles_path
        if body.idle_behavior is not None:
            try:
                setting.idle_behavior = IdleBehavior(body.idle_behavior)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid idle_behavior: {body.idle_behavior}",
                ) from None
        if body.default_auto_playlist_id is not None:
            setting.default_auto_playlist_id = body.default_auto_playlist_id
        if body.crossfade_enabled is not None:
            setting.crossfade_enabled = body.crossfade_enabled
            updates["crossfade_enabled"] = str(body.crossfade_enabled).lower()
        if body.crossfade_duration_ms is not None:
            setting.crossfade_duration_ms = body.crossfade_duration_ms
            updates["crossfade_duration"] = str(body.crossfade_duration_ms / 1000.0)
        if body.gapless_enabled is not None:
            setting.gapless_enabled = body.gapless_enabled
        if body.jingle_duck_db is not None:
            setting.jingle_duck_db = body.jingle_duck_db
            updates["jingle_duck_db"] = str(body.jingle_duck_db)
        if body.icecast_buffer_offset_ms is not None:
            setting.icecast_buffer_offset_ms = body.icecast_buffer_offset_ms
        if body.min_quiet_duration_s is not None:
            setting.min_quiet_duration_s = body.min_quiet_duration_s

        await session.commit()
        await session.refresh(setting)

        # Push variable changes to Liquidsoap (best-effort, non-fatal)
        if updates:
            try:
                from raidio.main import app as fastapi_app

                ls_client = fastapi_app.state.liquidsoap
                for var_name, var_value in updates.items():
                    await ls_client.set_var(var_name, var_value)
                    logger.info("Set Liquidsoap var %s = %s", var_name, var_value)
            except Exception:
                logger.warning("Failed to push settings to Liquidsoap", exc_info=True)

    return SettingsResponse(
        id=setting.id,
        library_path=setting.library_path,
        jingles_path=setting.jingles_path,
        idle_behavior=setting.idle_behavior.value,
        default_auto_playlist_id=setting.default_auto_playlist_id,
        crossfade_enabled=setting.crossfade_enabled,
        crossfade_duration_ms=setting.crossfade_duration_ms,
        gapless_enabled=setting.gapless_enabled,
        jingle_duck_db=setting.jingle_duck_db,
        icecast_buffer_offset_ms=setting.icecast_buffer_offset_ms,
        min_quiet_duration_s=setting.min_quiet_duration_s,
    )


# ── 4.5: Audio analysis — Phase B of scanner ──────────────────────


@router.post("/tracks/{track_id}/reanalyze")
async def reanalyze_track(
    track_id: int,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Clear analysis for a track and re-enqueue it for Phase B analysis."""
    factory = get_session_factory()
    async with factory() as session:
        track = await session.get(Track, track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        # Clear existing analysis
        await session.execute(delete(QuietPassage).where(QuietPassage.track_id == track_id))
        track.analysis_status = AnalysisStatus.PENDING
        track.analysis_error = None
        track.audio_analyzed_at = None
        await session.commit()

    # Enqueue for analysis
    pool = get_analysis_pool()
    pool.enqueue(track_id)
    return {"status": "enqueued"}


# ── 4.7: Jingle live drop ─────────────────────────────────────────


@router.post("/queue/insert-jingle/{jingle_id}")
async def insert_jingle(
    jingle_id: int,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Push a jingle onto Liquidsoap's interrupt queue for live ducking."""
    factory = get_session_factory()
    async with factory() as session:
        jingle = await session.get(Jingle, jingle_id)
        if not jingle:
            raise HTTPException(status_code=404, detail="Jingle not found")

    try:
        from raidio.main import app as fastapi_app

        ls_client = fastapi_app.state.liquidsoap
        await ls_client.push_jingle(jingle.path)
        logger.info("Inserted jingle %d: %s", jingle_id, jingle.path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "inserted", "jingle_id": jingle_id}


# ── 4.8: Live queue management ────────────────────────────────────


class QueueItemResponse(BaseModel):
    id: int
    position: int
    playlist_id: int | None
    track_id: int | None
    jingle_id: int | None
    state: str
    artist: str | None = None
    title: str | None = None
    album: str | None = None
    duration_ms: int | None = None
    owner_label: str | None = None


class QueueResponse(BaseModel):
    items: list[QueueItemResponse]
    active_playlists: list[dict]


@router.get("/queue", response_model=QueueResponse)
async def get_queue(admin_email: Annotated[str, Depends(require_admin)]):
    """Get the current live queue and active user playlists."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(LiveQueueItem).order_by(LiveQueueItem.position))
        lq_items = result.scalars().all()

        items: list[QueueItemResponse] = []
        for lq in lq_items:
            artist, title, album, duration_ms, owner_label = None, None, None, None, None

            if lq.track_id:
                track = await session.get(Track, lq.track_id)
                if track:
                    artist, title, album, duration_ms = (
                        track.artist,
                        track.title,
                        track.album,
                        track.duration_ms,
                    )
            elif lq.jingle_id:
                jingle = await session.get(Jingle, lq.jingle_id)
                if jingle:
                    title, duration_ms = jingle.title, jingle.duration_ms

            if lq.playlist_id:
                pl = await session.get(Playlist, lq.playlist_id)
                if pl:
                    owner_label = pl.owner_label

            items.append(
                QueueItemResponse(
                    id=lq.id,
                    position=lq.position,
                    playlist_id=lq.playlist_id,
                    track_id=lq.track_id,
                    jingle_id=lq.jingle_id,
                    state=lq.state.value,
                    artist=artist,
                    title=title,
                    album=album,
                    duration_ms=duration_ms,
                    owner_label=owner_label,
                )
            )

        # Active playlists
        active_pls = await session.execute(
            select(Playlist)
            .where(Playlist.kind == PlaylistKind.USER_SESSION)
            .order_by(Playlist.created_at)
        )
        active_playlists = [
            {
                "id": pl.id,
                "name": pl.name,
                "owner_label": pl.owner_label,
                "item_count": len(pl.items),
            }
            for pl in active_pls.scalars().all()
        ]

    return QueueResponse(items=items, active_playlists=active_playlists)


class ReorderItem(BaseModel):
    id: int
    position: int


@router.put("/queue/reorder")
async def reorder_queue(
    body: list[ReorderItem],
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Reorder pending items in the live queue."""
    factory = get_session_factory()
    async with factory() as session:
        for item in body:
            lq = await session.get(LiveQueueItem, item.id)
            if not lq:
                raise HTTPException(status_code=404, detail=f"Queue item {item.id} not found")
            if lq.state != LiveQueueState.PENDING:
                raise HTTPException(
                    status_code=422,
                    detail=f"Cannot reorder item {item.id} in state '{lq.state.value}'",
                )
            lq.position = item.position
        await session.commit()
    return {"status": "reordered"}


@router.delete("/queue/{item_id}")
async def delete_queue_item(
    item_id: int,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Remove a pending item from the live queue."""
    factory = get_session_factory()
    async with factory() as session:
        lq = await session.get(LiveQueueItem, item_id)
        if not lq:
            raise HTTPException(status_code=404, detail="Queue item not found")
        if lq.state != LiveQueueState.PENDING:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot delete item in state '{lq.state.value}'",
            )
        await session.delete(lq)
        await session.commit()
    return {"status": "deleted"}


@router.post("/queue/skip")
async def skip_current_track(
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Skip the currently playing track in Liquidsoap."""
    from raidio.main import app as fastapi_app

    ls_client = fastapi_app.state.liquidsoap
    try:
        await ls_client.skip()

        # Mark current playing item as skipped in DB
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(LiveQueueItem)
                .where(LiveQueueItem.state == LiveQueueState.PLAYING)
                .order_by(LiveQueueItem.position)
                .limit(1)
            )
            current = result.scalar_one_or_none()
            if current:
                current.state = LiveQueueState.SKIPPED
                current.ended_at = datetime.now(tz=UTC).replace(tzinfo=None)
                await session.commit()

        return {"status": "skipped"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ── 4.9: Auto-playlists CRUD ──────────────────────────────────────


class AutoPlaylistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    notes: str | None = None
    items: list[dict] = Field(..., min_length=1)


class AutoPlaylistResponse(BaseModel):
    id: int
    name: str
    notes: str | None
    is_default: bool
    item_count: int
    created_at: str | None


class AutoPlaylistDetail(AutoPlaylistResponse):
    items: list[dict]


@router.get("/auto-playlists", response_model=list[AutoPlaylistResponse])
async def list_auto_playlists(admin_email: Annotated[str, Depends(require_admin)]):
    """List all auto-playlists."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Playlist).where(Playlist.kind == PlaylistKind.AUTO).order_by(Playlist.name)
        )
        playlists = result.scalars().all()

        # Get default auto-playlist ID from settings
        settings_row = await session.get(Setting, 1)
        default_id = settings_row.default_auto_playlist_id if settings_row else None

        return [
            AutoPlaylistResponse(
                id=pl.id,
                name=pl.name,
                notes=pl.notes,
                is_default=pl.id == default_id,
                item_count=len(pl.items),
                created_at=pl.created_at.isoformat() if pl.created_at else None,
            )
            for pl in playlists
        ]


@router.post("/auto-playlists", response_model=AutoPlaylistResponse)
async def create_auto_playlist(
    body: AutoPlaylistCreate,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Create a new auto-playlist."""
    factory = get_session_factory()
    async with factory() as session:
        pl = Playlist(
            name=body.name,
            notes=body.notes,
            kind=PlaylistKind.AUTO,
        )
        session.add(pl)
        await session.flush()

        for idx, item in enumerate(body.items):
            track_id = item.get("track_id")
            jingle_id = item.get("jingle_id")
            if track_id:
                track = await session.get(Track, track_id)
                if not track:
                    raise HTTPException(status_code=404, detail=f"Track {track_id} not found")
            if jingle_id:
                jingle = await session.get(Jingle, jingle_id)
                if not jingle:
                    raise HTTPException(status_code=404, detail=f"Jingle {jingle_id} not found")

            pi = PlaylistItem(
                playlist_id=pl.id,
                position=idx,
                track_id=track_id,
                jingle_id=jingle_id,
            )
            session.add(pi)

        await session.commit()
        await session.refresh(pl)

    return AutoPlaylistResponse(
        id=pl.id,
        name=pl.name,
        notes=pl.notes,
        is_default=False,
        item_count=len(body.items),
        created_at=pl.created_at.isoformat() if pl.created_at else None,
    )


@router.get("/auto-playlists/{playlist_id}", response_model=AutoPlaylistDetail)
async def get_auto_playlist(
    playlist_id: int,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Get a single auto-playlist with its items."""
    factory = get_session_factory()
    async with factory() as session:
        pl = await session.get(Playlist, playlist_id)
        if not pl or pl.kind != PlaylistKind.AUTO:
            raise HTTPException(status_code=404, detail="Auto-playlist not found")

        settings_row = await session.get(Setting, 1)
        default_id = settings_row.default_auto_playlist_id if settings_row else None

        return AutoPlaylistDetail(
            id=pl.id,
            name=pl.name,
            notes=pl.notes,
            is_default=pl.id == default_id,
            item_count=len(pl.items),
            created_at=pl.created_at.isoformat() if pl.created_at else None,
            items=[
                {
                    "id": item.id,
                    "position": item.position,
                    "track_id": item.track_id,
                    "jingle_id": item.jingle_id,
                    "overlay_at_ms": item.overlay_at_ms,
                }
                for item in pl.items
            ],
        )


class AutoPlaylistUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None
    is_default: bool | None = None
    items: list[dict] | None = None


@router.put("/auto-playlists/{playlist_id}", response_model=AutoPlaylistResponse)
async def update_auto_playlist(
    playlist_id: int,
    body: AutoPlaylistUpdate,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Update an auto-playlist."""
    factory = get_session_factory()
    async with factory() as session:
        pl = await session.get(Playlist, playlist_id)
        if not pl or pl.kind != PlaylistKind.AUTO:
            raise HTTPException(status_code=404, detail="Auto-playlist not found")

        if body.name is not None:
            pl.name = body.name
        if body.notes is not None:
            pl.notes = body.notes

        # Set/unset as default
        if body.is_default:
            settings_row = await session.get(Setting, 1)
            if settings_row:
                settings_row.default_auto_playlist_id = playlist_id
        elif body.is_default is False:
            settings_row = await session.get(Setting, 1)
            if settings_row and settings_row.default_auto_playlist_id == playlist_id:
                settings_row.default_auto_playlist_id = None

        # Replace items if provided
        if body.items is not None:
            # Delete existing items
            await session.execute(
                delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id)
            )
            for idx, item in enumerate(body.items):
                pi = PlaylistItem(
                    playlist_id=playlist_id,
                    position=idx,
                    track_id=item.get("track_id"),
                    jingle_id=item.get("jingle_id"),
                    overlay_at_ms=item.get("overlay_at_ms"),
                )
                session.add(pi)

        pl.updated_at = datetime.now(tz=UTC).replace(tzinfo=None)
        await session.commit()
        await session.refresh(pl)

        # Eagerly load items to avoid detached instance error

        await session.refresh(pl, ["items"])

        settings_row = await session.get(Setting, 1)
        default_id = settings_row.default_auto_playlist_id if settings_row else None

        item_count = len(pl.items)

    return AutoPlaylistResponse(
        id=pl.id,
        name=pl.name,
        notes=pl.notes,
        is_default=pl.id == default_id,
        item_count=item_count,
        created_at=pl.created_at.isoformat() if pl.created_at else None,
    )


@router.delete("/auto-playlists/{playlist_id}")
async def delete_auto_playlist(
    playlist_id: int,
    admin_email: Annotated[str, Depends(require_admin)],
):
    """Delete an auto-playlist."""
    factory = get_session_factory()
    async with factory() as session:
        pl = await session.get(Playlist, playlist_id)
        if not pl or pl.kind != PlaylistKind.AUTO:
            raise HTTPException(status_code=404, detail="Auto-playlist not found")

        # Unset as default if this was the default
        settings_row = await session.get(Setting, 1)
        if settings_row and settings_row.default_auto_playlist_id == playlist_id:
            settings_row.default_auto_playlist_id = None

        await session.delete(pl)
        await session.commit()

    return {"status": "deleted"}
