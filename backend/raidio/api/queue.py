
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from raidio.core.names import generate_name
from raidio.db.models import (
    Jingle,
    LiveQueueItem,
    LiveQueueState,
    Playlist,
    Track,
)
from raidio.db.models import (
    PlaylistItem as DBPlaylistItem,
)

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        yield session


class PlaylistItemInput(BaseModel):
    track_id: int | None = None
    jingle_id: int | None = None
    overlay_at_ms: int | None = None


class PlaylistSubmitRequest(BaseModel):
    name: str = Field(max_length=80)
    notes: str | None = Field(default=None, max_length=500)
    items: list[PlaylistItemInput]
    owner_label: str | None = None


class PlaylistSubmitResponse(BaseModel):
    playlist_id: int
    queue_position: int | None
    estimated_wait_ms: int | None


@router.post("/queue/playlists", response_model=PlaylistSubmitResponse)
async def submit_playlist(
    request: Request,
    body: PlaylistSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    if not body.items:
        raise HTTPException(status_code=400, detail="At least one item required")

    for item in body.items:
        if item.track_id and item.jingle_id:
            raise HTTPException(
                status_code=400, detail="Cannot specify both track_id and jingle_id"
            )
        if not item.track_id and not item.jingle_id:
            raise HTTPException(
                status_code=400, detail="Each item must have track_id or jingle_id"
            )
        if item.overlay_at_ms is not None and item.jingle_id is None:
            raise HTTPException(
                status_code=400, detail="overlay_at_ms requires jingle_id"
            )

    if body.owner_label:
        owner_label = body.owner_label
    else:
        owner_label = generate_name()

    playlist = Playlist(
        name=body.name,
        notes=body.notes,
        kind="user_session",
        owner_label=owner_label,
    )
    db.add(playlist)
    await db.flush()

    for i, item_input in enumerate(body.items):
        db_item = DBPlaylistItem(
            playlist_id=playlist.id,
            position=i,
            track_id=item_input.track_id,
            jingle_id=item_input.jingle_id,
            overlay_at_ms=item_input.overlay_at_ms,
        )
        db.add(db_item)

    await db.flush()
    await db.refresh(playlist)

    playlist_items_result = await db.execute(
        select(DBPlaylistItem)
        .where(DBPlaylistItem.playlist_id == playlist.id)
        .order_by(DBPlaylistItem.position)
    )
    items = list(playlist_items_result.scalars().all())

    total_duration_ms = 0
    for item in items:
        if item.track_id:
            track = await db.get(Track, item.track_id)
            if track and track.duration_ms:
                total_duration_ms += track.duration_ms
        elif item.jingle_id:
            jingle = await db.get(Jingle, item.jingle_id)
            if jingle and jingle.duration_ms:
                total_duration_ms += jingle.duration_ms

    pending_result = await db.execute(
        select(LiveQueueItem).where(LiveQueueItem.state == LiveQueueState.PENDING)
    )
    pending_items = list(pending_result.scalars().all())

    max_position = -1
    for pending in pending_items:
        if pending.position is not None and pending.position > max_position:
            max_position = pending.position

    queue_position = len(pending_items)
    next_position = max_position + 1

    for item in items:
        queue_item = LiveQueueItem(
            playlist_id=playlist.id,
            track_id=item.track_id,
            jingle_id=item.jingle_id,
            state=LiveQueueState.PENDING,
            position=next_position,
        )
        db.add(queue_item)
        next_position += 1

    await db.commit()

    return PlaylistSubmitResponse(
        playlist_id=playlist.id,
        queue_position=queue_position,
        estimated_wait_ms=total_duration_ms if queue_position == 0 else None,
    )


class LiveQueueItemResponse(BaseModel):
    id: int
    position: int
    playlist_id: int | None
    track_id: int | None
    jingle_id: int | None
    state: str
    enqueued_at: str | None
    started_at: str | None

    class Config:
        from_attributes = True


@router.get("/queue")
async def get_queue(
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[LiveQueueItemResponse]]:
    result = await db.execute(
        select(LiveQueueItem)
        .options(selectinload(LiveQueueItem.track), selectinload(LiveQueueItem.jingle))
        .order_by(LiveQueueItem.position)
    )
    items = result.scalars().all()
    return {
        "queue": [
            LiveQueueItemResponse(
                id=item.id,
                position=item.position,
                playlist_id=item.playlist_id,
                track_id=item.track_id,
                jingle_id=item.jingle_id,
                state=item.state.value if item.state else "pending",
                enqueued_at=item.enqueued_at.isoformat() if item.enqueued_at else None,
                started_at=item.started_at.isoformat() if item.started_at else None,
            )
            for item in items
        ]
    }

