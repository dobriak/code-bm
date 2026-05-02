"""fts5

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-03 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
            artist, album, title, genre,
            content='tracks',
            content_rowid='id',
            tokenize='porter unicode61'
        )
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
            INSERT INTO tracks_fts(rowid, artist, album, title, genre)
            VALUES (new.id, new.artist, new.album, new.title, new.genre);
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
            INSERT INTO tracks_fts(tracks_fts, rowid, artist, album, title, genre)
            VALUES ('delete', old.id, old.artist, old.album, old.title, old.genre);
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
            INSERT INTO tracks_fts(tracks_fts, rowid, artist, album, title, genre)
            VALUES ('delete', old.id, old.artist, old.album, old.title, old.genre);
            INSERT INTO tracks_fts(rowid, artist, album, title, genre)
            VALUES (new.id, new.artist, new.album, new.title, new.genre);
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tracks_au")
    op.execute("DROP TRIGGER IF EXISTS tracks_ad")
    op.execute("DROP TRIGGER IF EXISTS tracks_ai")
    op.execute("DROP TABLE IF EXISTS tracks_fts")
