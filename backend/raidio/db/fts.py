"""FTS5 full-text search for tracks.

Creates a virtual table `tracks_fts` over (artist, album, title, genre)
with content-sync triggers. Provides a query builder that escapes user input
and produces FTS5 MATCH expressions with prefix-fuzzy semantics.
"""

from __future__ import annotations

import re
import sqlite3

# ── DDL for FTS5 table + triggers ──────────────────────────────────

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


def create_fts_tables(conn: sqlite3.Connection) -> None:
    """Create the FTS5 virtual table and content-sync triggers.

    Must be called on a raw sqlite3 connection (not SQLAlchemy async).
    Used in Alembic migrations via op.get_bind().
    """
    conn.execute(FTS_CREATE_SQL)
    for trigger_sql in FTS_TRIGGERS_SQL:
        conn.execute(trigger_sql)


def drop_fts_tables(conn: sqlite3.Connection) -> None:
    """Drop the FTS5 table and triggers."""
    for name in ["tracks_fts_insert", "tracks_fts_update", "tracks_fts_delete"]:
        conn.execute(f"DROP TRIGGER IF EXISTS {name}")
    conn.execute("DROP TABLE IF EXISTS tracks_fts")


# ── Query builder ──────────────────────────────────────────────────

# Characters that have special meaning in FTS5 and must be escaped.
_FTS_SPECIAL = re.compile(r'["*()\\:]')


def fts_query(text: str) -> str:
    """Build an FTS5 MATCH expression from user input.

    - Each word is prefix-fuzzied by appending ``*``
    - Words are combined with ``NEAR/4`` for relevance
    - Special FTS5 characters are escaped
    - Empty/whitespace-only input returns ``"*"`` (match all)

    Examples::

        >>> fts_query("beatles")
        'beatles*'
        >>> fts_query("radiohead kid a")
        'radiohead* NEAR/4 kid* NEAR/4 a*'
        >>> fts_query('test "quote"')
        'test* NEAR/4 \\"quote\\"*'
    """
    if not text or not text.strip():
        return '"*"'

    # Tokenize on whitespace, escape special chars, append * for prefix
    tokens = []
    for word in text.split():
        escaped = _FTS_SPECIAL.sub(r"\\\g<0>", word)
        tokens.append(f"{escaped}*")

    return " NEAR/4 ".join(tokens)
