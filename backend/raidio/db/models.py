from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from raidio.db.base import Base


class AnalysisStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class QuietRegion(enum.StrEnum):
    INTRO = "intro"
    OUTRO = "outro"


class PlaylistKind(enum.StrEnum):
    AUTO = "auto"
    USER_SESSION = "user_session"


class LiveQueueState(enum.StrEnum):
    PENDING = "pending"
    PLAYING = "playing"
    PLAYED = "played"
    SKIPPED = "skipped"


class IdleBehavior(enum.StrEnum):
    AUTO_PLAYLIST = "auto_playlist"
    RANDOM = "random"
    SILENCE = "silence"


class ScanKind(enum.StrEnum):
    LIBRARY = "library"
    JINGLES = "jingles"


class ScanStatus(enum.StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False)

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

    tags_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audio_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False
    )
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    quiet_passages: Mapped[list[QuietPassage]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tracks_artist_album_track_number", "artist", "album", "track_number"),
        Index("ix_tracks_genre", "genre"),
        Index("ix_tracks_year", "year"),
    )


class QuietPassage(Base):
    __tablename__ = "quiet_passages"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )

    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    region: Mapped[QuietRegion] = mapped_column(Enum(QuietRegion), nullable=False)
    db_threshold: Mapped[float] = mapped_column(Numeric, nullable=False)

    track: Mapped[Track] = relationship(back_populates="quiet_passages")


class Jingle(Base):
    __tablename__ = "jingles"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_art_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    kind: Mapped[PlaylistKind] = mapped_column(Enum(PlaylistKind), nullable=False)
    owner_label: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list[PlaylistItem]] = relationship(
        back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistItem.position"
    )

    __table_args__ = (CheckConstraint("kind IN ('auto', 'user_session')"),)


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    track_id: Mapped[int | None] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=True
    )
    jingle_id: Mapped[int | None] = mapped_column(
        ForeignKey("jingles.id", ondelete="CASCADE"), nullable=True
    )

    overlay_at_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    playlist: Mapped[Playlist] = relationship(back_populates="items")
    track: Mapped[Track | None] = relationship()
    jingle: Mapped[Jingle | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "CASE WHEN overlay_at_ms IS NOT NULL THEN 1 ELSE (track_id IS NOT NULL) END = 1",
            name="chk_track_or_jingle",
        ),
        UniqueConstraint("playlist_id", "position", name="uq_playlist_position"),
    )


class LiveQueueItem(Base):
    __tablename__ = "live_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    playlist_id: Mapped[int | None] = mapped_column(
        ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True
    )
    track_id: Mapped[int | None] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=True
    )
    jingle_id: Mapped[int | None] = mapped_column(
        ForeignKey("jingles.id", ondelete="CASCADE"), nullable=True
    )

    state: Mapped[LiveQueueState] = mapped_column(
        Enum(LiveQueueState), default=LiveQueueState.PENDING, nullable=False
    )

    enqueued_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_live_queue_state_position", "state", "position"),)


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, default=1, primary_key=True)

    library_path: Mapped[str] = mapped_column(Text, nullable=False)
    jingles_path: Mapped[str] = mapped_column(Text, nullable=False)

    idle_behavior: Mapped[IdleBehavior] = mapped_column(
        Enum(IdleBehavior), default=IdleBehavior.RANDOM, nullable=False
    )
    default_auto_playlist_id: Mapped[int | None] = mapped_column(
        ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True
    )

    crossfade_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    crossfade_duration_ms: Mapped[int] = mapped_column(Integer, default=4000, nullable=False)
    gapless_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    jingle_duck_db: Mapped[float] = mapped_column(Numeric, default=-12.0, nullable=False)
    icecast_buffer_offset_ms: Mapped[int] = mapped_column(Integer, default=3000, nullable=False)

    min_quiet_duration_s: Mapped[int] = mapped_column(Integer, default=2, nullable=False)


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ScanKind] = mapped_column(Enum(ScanKind), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus), default=ScanStatus.RUNNING, nullable=False
    )

    tracks_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tracks_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tracks_removed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    errors_json: Mapped[str | None] = mapped_column(Text, nullable=True)
