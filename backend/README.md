# Raidio Backend

## Running

```bash
task install          # install deps
task dev:backend     # run FastAPI on :8001
task db:migrate      # apply pending migrations
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:///database/raidio.db` |
| `ADMIN_PASSWORD_HASH` | Bcrypt hash of admin password | (required) |
| `JWT_SECRET` | HS256 signing secret | (required) |
| `LIQUIDSOAP_HOST` | Liquidsoap telnet host | `localhost` |
| `LIQUIDSOAP_PORT` | Liquidsoap telnet port | `1234` |
| `LIBRARY_PATH` | Root music library path | (required) |
| `JINGLES_PATH` | Jingles directory path | (required) |
| `ICECAST_SOURCE_PASSWORD` | Icecast source password | `hackme` |
| `COVER_CACHE_PATH` | Directory for cover art cache | `cache/covers` |

## API Reference

Interactive documentation available at `/docs` (Swagger UI) when the server is running.

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/tracks` | List/search tracks (paginated) |
| `GET` | `/api/v1/tracks/{id}` | Track detail with quiet passages |
| `GET` | `/api/v1/tracks/{id}/cover` | Stream cover art |
| `GET` | `/api/v1/tracks/random` | Random track |
| `POST` | `/api/v1/tracks/resolve-paths` | Resolve file paths to track/jingle IDs |
| `GET` | `/api/v1/artists` | Artist facet listing |
| `GET` | `/api/v1/albums` | Album facet listing |
| `GET` | `/api/v1/genres` | Genre facet listing |
| `GET` | `/api/v1/jingles` | List jingles |
| `POST` | `/api/v1/queue/playlists` | Submit a playlist to the queue |
| `GET` | `/api/v1/now-playing` | Current/prev/next track info |
| `WS` | `/api/v1/ws/now-playing` | Real-time now-playing updates |

### Admin Endpoints (JWT required)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/admin/login` | Admin login, returns JWT |
| `POST` | `/api/v1/admin/scan/library` | Trigger library scan |
| `POST` | `/api/v1/admin/scan/jingles` | Trigger jingles scan |
| `GET` | `/api/v1/admin/scan/status` | Scan job status |
| `WS` | `/api/v1/admin/scan` | Real-time scan progress |
| `GET` | `/api/v1/admin/stats` | Dashboard statistics |
| `GET` | `/api/v1/admin/settings` | Get settings |
| `PUT` | `/api/v1/admin/settings` | Update settings |
| `GET` | `/api/v1/admin/queue` | Live queue + active playlists |
| `PUT` | `/api/v1/admin/queue/reorder` | Reorder queue items |
| `DELETE` | `/api/v1/admin/queue/{id}` | Remove queue item |
| `POST` | `/api/v1/admin/queue/skip` | Skip current track |
| `POST` | `/api/v1/admin/queue/insert-jingle/{id}` | Insert jingle |
| `POST` | `/api/v1/admin/tracks/{id}/reanalyze` | Re-trigger audio analysis |
| `GET` | `/api/v1/admin/auto-playlists` | List auto-playlists |
| `POST` | `/api/v1/admin/auto-playlists` | Create auto-playlist |
| `GET` | `/api/v1/admin/auto-playlists/{id}` | Get auto-playlist |
| `PUT` | `/api/v1/admin/auto-playlists/{id}` | Update auto-playlist |
| `DELETE` | `/api/v1/admin/auto-playlists/{id}` | Delete auto-playlist |

## Extension Guide

### Adding a new database model

1. Add the model class in `raidio/db/models.py`
2. Create a migration: `task db:revision -- "add new model"`
3. Apply: `task db:migrate`

### Adding a new API router

1. Create `raidio/api/your_router.py` with a `APIRouter()`
2. Register in `raidio/main.py`: `app.include_router(your_router, prefix="/api/v1", tags=["your-tag"])`

### Streaming pipeline

The broadcast flow: `Broadcaster` → `LiquidsoapClient` (telnet push) → Icecast → browser.

To debug Liquidsoap, connect: `telnet localhost 1234` and type `help`.
