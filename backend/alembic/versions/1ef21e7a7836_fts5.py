"""fts5

Revision ID: 1ef21e7a7836
Revises: 552a93cdaa62
Create Date: 2026-05-02 12:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "1ef21e7a7836"
down_revision: Union[str, Sequence[str], None] = "552a93cdaa62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FTS_CREATE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts
USING fts5(artist, album, title, genre, content='tracks', content_rowid='id');
"""

FTS_TRIGGERS_SQL = [
    """\
CREATE TRIGGER IF NOT EXISTS tracks_fts_insert AFTER INSERT ON tracks BEGIN
    INSERT INTO tracks_fts(rowid, artist, album, title, genre)
    VALUES (new.id,
            COALESCE(new.artist, ''),
            COALESCE(new.album, ''),
            COALESCE(new.title, ''),
            COALESCE(new.genre, ''));
END;
""",
    """\
CREATE TRIGGER IF NOT EXISTS tracks_fts_update AFTER UPDATE ON tracks BEGIN
    INSERT INTO tracks_fts(tracks_fts, rowid, artist, album, title, genre)
    VALUES ('delete', old.id,
            COALESCE(old.artist, ''),
            COALESCE(old.album, ''),
            COALESCE(old.title, ''),
            COALESCE(old.genre, ''));
    INSERT INTO tracks_fts(rowid, artist, album, title, genre)
    VALUES (new.id,
            COALESCE(new.artist, ''),
            COALESCE(new.album, ''),
            COALESCE(new.title, ''),
            COALESCE(new.genre, ''));
END;
""",
    """\
CREATE TRIGGER IF NOT EXISTS tracks_fts_delete AFTER DELETE ON tracks BEGIN
    INSERT INTO tracks_fts(tracks_fts, rowid, artist, album, title, genre)
    VALUES ('delete', old.id,
            COALESCE(old.artist, ''),
            COALESCE(old.album, ''),
            COALESCE(old.title, ''),
            COALESCE(old.genre, ''));
END;
""",
]


def upgrade() -> None:
    """Create FTS5 virtual table and content-sync triggers."""
    conn = op.get_bind()
    conn.execute(text(FTS_CREATE_SQL))
    for trigger_sql in FTS_TRIGGERS_SQL:
        conn.execute(text(trigger_sql))


def downgrade() -> None:
    """Drop FTS5 table and triggers."""
    conn = op.get_bind()
    for name in ["tracks_fts_insert", "tracks_fts_update", "tracks_fts_delete"]:
        conn.execute(text(f"DROP TRIGGER IF EXISTS {name}"))
    conn.execute(text("DROP TABLE IF EXISTS tracks_fts"))
