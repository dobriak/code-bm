"""initial schema

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import func

from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    analysis_status = sa.Enum('pending', 'running', 'done', 'error', name='analysisstatus')
    analysis_status.create(op.get_bind())

    quiet_region = sa.Enum('intro', 'outro', name='quietregion')
    quiet_region.create(op.get_bind())

    playlist_kind = sa.Enum('auto', 'user_session', name='playlistkind')
    playlist_kind.create(op.get_bind())

    live_queue_state = sa.Enum('pending', 'playing', 'played', 'skipped', name='livequeuestate')
    live_queue_state.create(op.get_bind())

    idle_behavior = sa.Enum('auto_playlist', 'random', 'silence', name='idlebehavior')
    idle_behavior.create(op.get_bind())

    scan_kind = sa.Enum('library', 'jingles', name='scankind')
    scan_kind.create(op.get_bind())

    scan_status = sa.Enum('running', 'completed', 'failed', name='scanstatus')
    scan_status.create(op.get_bind())

    op.create_table(
        'tracks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('file_hash', sa.Text(), nullable=False),
        sa.Column('artist', sa.Text(), nullable=True),
        sa.Column('album', sa.Text(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('genre', sa.Text(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('track_number', sa.Integer(), nullable=True),
        sa.Column('disc_number', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('sample_rate_hz', sa.Integer(), nullable=True),
        sa.Column('cover_art_path', sa.Text(), nullable=True),
        sa.Column('tags_scanned_at', sa.DateTime(), nullable=True),
        sa.Column('audio_analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('analysis_status', analysis_status, nullable=False, server_default='pending'),
        sa.Column('analysis_error', sa.Text(), nullable=True),
        sa.UniqueConstraint('path'),
    )
    op.create_index(
        'ix_tracks_artist_album_track_number',
        'tracks',
        ['artist', 'album', 'track_number']
    )
    op.create_index('ix_tracks_genre', 'tracks', ['genre'])
    op.create_index('ix_tracks_year', 'tracks', ['year'])

    op.create_table(
        'quiet_passages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('start_ms', sa.Integer(), nullable=False),
        sa.Column('end_ms', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('region', quiet_region, nullable=False),
        sa.Column('db_threshold', sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
    )

    op.create_table(
        'jingles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('file_hash', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('cover_art_path', sa.Text(), nullable=True),
        sa.UniqueConstraint('path'),
    )

    op.create_table(
        'playlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('kind', playlist_kind, nullable=False),
        sa.Column('owner_label', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=func.now()),
        sa.CheckConstraint("kind IN ('auto', 'user_session')"),
    )

    op.create_table(
        'playlist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('playlist_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('jingle_id', sa.Integer(), nullable=True),
        sa.Column('overlay_at_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['jingle_id'], ['jingles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('playlist_id', 'position', name='uq_playlist_position'),
    )

    op.create_table(
        'live_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('playlist_id', sa.Integer(), nullable=True),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('jingle_id', sa.Integer(), nullable=True),
        sa.Column('state', live_queue_state, nullable=False, server_default='pending'),
        sa.Column('enqueued_at', sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['jingle_id'], ['jingles.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_live_queue_state_position', 'live_queue', ['state', 'position'])

    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('library_path', sa.Text(), nullable=False),
        sa.Column('jingles_path', sa.Text(), nullable=False),
        sa.Column('idle_behavior', idle_behavior, nullable=False, server_default='random'),
        sa.Column('default_auto_playlist_id', sa.Integer(), nullable=True),
        sa.Column('crossfade_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('crossfade_duration_ms', sa.Integer(), nullable=False, server_default='4000'),
        sa.Column('gapless_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('jingle_duck_db', sa.Numeric(), nullable=False, server_default='-12.0'),
        sa.Column('icecast_buffer_offset_ms', sa.Integer(), nullable=False, server_default='3000'),
        sa.Column('min_quiet_duration_s', sa.Integer(), nullable=False, server_default='2'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'scan_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kind', scan_kind, nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', scan_status, nullable=False, server_default='running'),
        sa.Column('tracks_added', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tracks_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tracks_removed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors_json', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('scan_jobs')
    op.drop_table('settings')
    op.drop_table('live_queue')
    op.drop_table('playlist_items')
    op.drop_table('playlists')
    op.drop_table('jingles')
    op.drop_table('quiet_passages')
    op.drop_table('tracks')
