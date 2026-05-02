# Raidio Backend

Self-hosted LAN-only personal radio station — FastAPI backend.

## Running

```bash
# Install dependencies
cd backend && uv sync

# Run development server (port 8001)
uv run uvicorn raidio.main:app --host 127.0.0.1 --port 8001 --reload
```

Or use Taskfile from the repo root:
```bash
task dev:backend
```

## Environment Variables

Copy `.env.example` to `.env` and fill in values:

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_EMAIL` | Admin login email | — |
| `ADMIN_PASSWORD_HASH` | Bcrypt hash of admin password | — |
| `JWT_SECRET` | HS256 signing key (32+ bytes) | — |
| `LIBRARY_PATH` | Path to MP3 library directory | — |
| `JINGLES_PATH` | Path to jingles directory | — |
| `COVER_CACHE_PATH` | Where extracted cover art is stored | `./cache/covers` |
| `LIQUIDSOAP_HOST` | Liquidsoap telnet host | `127.0.0.1` |
| `LIQUIDSOAP_TELNET_PORT` | Liquidsoap telnet port | `1234` |
| `ICECAST_HOST` | Icecast server host | `127.0.0.1` |
| `ICECAST_PORT` | Icecast server port | `8000` |
| `ICECAST_MOUNT` | Icecast mount point | `/raidio.mp3` |
| `ICECAST_SOURCE_PASSWORD` | Icecast source password | — |

## API Reference

Interactive Swagger docs are available at `http://localhost:8001/docs` when the server is running.

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check with version |
| `GET` | `/api/v1/tracks` | Search & browse tracks (cursor-paginated) |
| `GET` | `/api/v1/tracks/{id}` | Full track detail with quiet passages |
| `GET` | `/api/v1/tracks/{id}/cover` | Stream cover art image |
| `GET` | `/api/v1/tracks/random` | Single random track |
| `GET` | `/api/v1/artists` | Artist facet listing with counts |
| `GET` | `/api/v1/albums` | Album facet listing with counts |
| `GET` | `/api/v1/genres` | Genre facet listing with counts |
| `GET` | `/api/v1/jingles` | List all jingles |
| `GET` | `/api/v1/now-playing` | Current + prev3/next3 |
| `POST` | `/api/v1/queue/playlists` | Submit user playlist |
| `WS` | `/ws/now-playing` | Live track-change updates |

### Admin Endpoints (JWT required)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/admin/login` | Authenticate, returns JWT |
| `POST` | `/api/v1/admin/scan/library` | Start library scan |
| `POST` | `/api/v1/admin/scan/jingles` | Start jingles scan |
| `GET` | `/api/v1/admin/scan/status` | Scan job history |
| `WS` | `/ws/admin/scan` | Live scan progress |
| `GET` | `/api/v1/admin/stats` | Dashboard statistics |
| `GET` | `/api/v1/admin/settings` | Get runtime settings |
| `PUT` | `/api/v1/admin/settings` | Update settings |
| `POST` | `/api/v1/admin/queue/skip` | Skip current track |
| `PUT` | `/api/v1/admin/queue/reorder` | Reorder pending items |
| `DELETE` | `/api/v1/admin/queue/{id}` | Remove queue item |
| `POST` | `/api/v1/admin/queue/insert-jingle/{id}` | Live jingle drop |
| `POST` | `/api/v1/admin/auto-playlists` | Create auto-playlist |
| `GET` | `/api/v1/admin/auto-playlists` | List auto-playlists |
| `GET` | `/api/v1/admin/auto-playlists/{id}` | Get auto-playlist detail |
| `PUT` | `/api/v1/admin/auto-playlists/{id}` | Update auto-playlist |
| `DELETE` | `/api/v1/admin/auto-playlists/{id}` | Delete auto-playlist |
| `POST` | `/api/v1/admin/tracks/{id}/reanalyze` | Re-run silence analysis |

## Project Structure

```
backend/
├── pyproject.toml          # Dependencies and tool config
├── alembic/                # Database migrations
└── raidio/
    ├── main.py             # FastAPI app factory + lifespan
    ├── api/                # Route handlers
    │   ├── catalog.py      # Public track/artist/album endpoints
    │   ├── queue.py        # Playlist submission, now-playing
    │   ├── scan.py         # Scan triggering + progress WS
    │   └── admin.py        # Auth, settings, queue management
    ├── core/               # Pure logic (no I/O)
    │   ├── auth.py         # JWT issuance/verification
    │   ├── scheduler.py    # Round-robin scheduler
    │   ├── names.py        # Funny-name generator
    │   └── now_playing.py  # Current/prev/next queue state
    ├── db/                 # SQLAlchemy models & session
    │   ├── models.py       # All ORM models
    │   ├── session.py      # Engine + session factory
    │   ├── settings.py     # pydantic-settings loader
    │   ├── bootstrap.py    # Default settings row
    │   └── fts.py          # FTS5 virtual table + query builder
    ├── scanner/            # Library scanning & audio analysis
    │   ├── walker.py       # Filesystem tree walker
    │   ├── tags.py         # Mutagen tag reader
    │   ├── cover_cache.py  # Cover art extraction & caching
    │   ├── library_scanner.py  # Scan orchestrator
    │   └── audio_analysis.py   # ffmpeg silencedetect workers
    ├── streaming/          # Liquidsoap integration
    │   ├── liquidsoap.py   # Async telnet client
    │   └── broadcaster.py  # Scheduler → Liquidsoap bridge
    └── ws/                 # WebSocket handlers (in api/)
```

## Testing

```bash
uv run pytest                        # All tests
uv run pytest --cov=raidio           # With coverage
uv run pytest tests/test_scheduler   # Specific module
```

## Extension Guide

1. **New API endpoint:** Add a route handler in `api/`, include the router in `main.py`.
2. **New database table:** Add a model in `db/models.py`, create an Alembic revision with `task db:revision MSG="..."`.
3. **New background worker:** Create an async task class, start/stop it in `main.py`'s lifespan.
4. **New setting:** Add a column to `Setting` model in `db/models.py`, update `db/bootstrap.py` defaults, add to `admin.py` settings schemas.
