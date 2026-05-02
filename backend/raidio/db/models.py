"""SQLAlchemy ORM models for Raidio.

All tables from DESIGN.md §5. All times in UTC, all durations in milliseconds.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from raidio.db.base import Base

# ── Enums ──────────────────────────────────────────────────────────


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class QuietRegion(StrEnum):
    INTRO = "intro"
    OUTRO = "outro"


class PlaylistKind(StrEnum):
    AUTO = "auto"
    USER_SESSION = "user_session"


class LiveQueueState(StrEnum):
    PENDING = "pending"
    PLAYING = "playing"
    PLAYED = "played"
    SKIPPED = "skipped"


class IdleBehavior(StrEnum):
    AUTO_PLAYLIST = "auto_playlist"
    RANDOM = "random"
    SILENCE = "silence"


class ScanKind(StrEnum):
    LIBRARY = "library"
    JINGLES = "jingles"


class ScanStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


# ── Track ──────────────────────────────────────────────────────────


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artist: Mapped[str | None] = mapped_column(Text, nullable=True)
    album: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    track_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disc_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_rate_hz: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_art_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_scanned_at: Mapped[datetime | None] = mapped_column(nullable=True)
    audio_analyzed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        default=AnalysisStatus.PENDING, nullable=False
    )
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    quiet_passages: Mapped[list[QuietPassage]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tracks_artist_album_track", "artist", "album", "track_number"),
        Index("ix_tracks_genre", "genre"),
        Index("ix_tracks_year", "year"),
    )


# ── QuietPassage ───────────────────────────────────────────────────


class QuietPassage(Base):
    __tablename__ = "quiet_passages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[QuietRegion] = mapped_column(nullable=False)
    db_threshold: Mapped[float] = mapped_column(Float, nullable=False)

    track: Mapped[Track] = relationship(back_populates="quiet_passages")


# ── Jingle ─────────────────────────────────────────────────────────


class Jingle(Base):
    __tablename__ = "jingles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_art_path: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Playlist ───────────────────────────────────────────────────────


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[PlaylistKind] = mapped_column(default=PlaylistKind.USER_SESSION, nullable=False)
    owner_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(tz=UTC).replace(tzinfo=None), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(tz=UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(tz=UTC).replace(tzinfo=None),
        nullable=False,
    )

    items: Mapped[list[PlaylistItem]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistItem.position",
    )


# ── PlaylistItem ───────────────────────────────────────────────────


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    track_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True
    )
    jingle_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jingles.id", ondelete="SET NULL"), nullable=True
    )
    overlay_at_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    playlist: Mapped[Playlist] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint(
            "track_id IS NOT NULL OR jingle_id IS NOT NULL",
            name="ck_playlist_item_has_content",
        ),
    )


# ── LiveQueueItem ──────────────────────────────────────────────────


class LiveQueueItem(Base):
    __tablename__ = "live_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    playlist_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True
    )
    track_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True
    )
    jingle_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jingles.id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[LiveQueueState] = mapped_column(default=LiveQueueState.PENDING, nullable=False)
    enqueued_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (Index("ix_live_queue_state_position", "state", "position"),)


# ── Setting ────────────────────────────────────────────────────────


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    jingles_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    idle_behavior: Mapped[IdleBehavior] = mapped_column(default=IdleBehavior.RANDOM, nullable=False)
    default_auto_playlist_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True
    )
    crossfade_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    crossfade_duration_ms: Mapped[int] = mapped_column(Integer, default=4000, nullable=False)
    gapless_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    jingle_duck_db: Mapped[float] = mapped_column(Float, default=-12.0, nullable=False)
    icecast_buffer_offset_ms: Mapped[int] = mapped_column(Integer, default=3000, nullable=False)
    min_quiet_duration_s: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)


# ── ScanJob ────────────────────────────────────────────────────────


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[ScanKind] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(tz=UTC).replace(tzinfo=None), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[ScanStatus] = mapped_column(default=ScanStatus.RUNNING, nullable=False)
    tracks_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tracks_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tracks_removed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_json: Mapped[str | None] = mapped_column(Text, nullable=True)
