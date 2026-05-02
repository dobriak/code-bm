# Raidio — Agent Onboarding Guide

> **Purpose:** This file gives any coding agent (or human) everything needed to understand the project, find things, and contribute correctly in under 5 minutes.

---

## What is Raidio?

A self-hosted, LAN-only personal radio station. One audio stream is produced server-side and consumed by 1–5 listeners on the local network. Users contribute playlists that compete in a round-robin scheduler; an admin manages the library, jingles, and live queue.

**Key constraint:** One server-side playhead, many synchronized listeners — not per-browser playback.

**Companion docs:**
- `docs/DESIGN.md` — full system design (architecture, data model, API surface, streaming decision)
- `docs/PRD.md` — product requirements, user stories, acceptance criteria
- `docs/IMPLEMENT.md` — phased implementation plan with checklists and exit criteria
- `code_quality.md` — benchmarking results and coverage metrics

---

## Technology Stack (mandatory, non-negotiable)

| Layer | Choice | Details |
|-------|--------|---------|
| Backend | FastAPI | Python 3.12, managed with `uv` |
| ORM | SQLAlchemy 2.x | Async, with Alembic migrations |
| Database | SQLite | `database/raidio.db` |
| Frontend | React + TypeScript | Built/run with Bun |
| Task runner | Taskfile | Orchestrates all services |
| Streaming | Liquidsoap → Icecast 2 | Server-side audio engine + HTTP broadcast |

**Runtime dependencies:** ffmpeg (silence detection, transcoding), Liquidsoap (audio engine), Icecast 2 (HTTP broadcast), Mutagen (Python tag reading).

---

## Repository Layout

```
.
├── backend/                  # FastAPI Python application
│   ├── pyproject.toml        # uv-managed dependencies
│   ├── .env.example          # Template for environment variables
│   ├── alembic/              # Database migrations
│   └── raidio/
│       ├── main.py           # FastAPI app factory
│       ├── api/              # Route handlers (routers)
│       ├── core/             # Pure logic: scheduler, FTS, name gen, auth
│       ├── db/               # SQLAlchemy models, session, FTS, settings
│       ├── scanner/          # Tag extraction + audio analysis workers
│       ├── streaming/        # Liquidsoap telnet client, broadcaster
│       └── ws/               # WebSocket handlers
├── frontend/                 # React + TypeScript SPA
│   ├── package.json          # Bun-managed dependencies
│   └── src/
│       ├── pages/            # Player (/), Create (/create), Admin (/admin)
│       ├── components/       # NowPlaying, TrackTable, PlaylistBuilder, etc.
│       ├── stores/           # Zustand global state
│       ├── api/              # React Query hooks
│       └── lib/              # Utilities, theme, name generator
├── liquidsoap/
│   ├── raidio.liq            # Liquidsoap script (< 100 lines, well-commented)
│   ├── icecast.xml           # Icecast config template
│   └── test.mp3              # Royalty-free test file
├── database/
│   └── raidio.db             # SQLite (gitignored)
├── cache/covers/             # Extracted album art (gitignored)
├── docs/                     # Living documentation
├── Taskfile.yml              # Task orchestration
├── AGENTS.md                 # This file
├── README.md
├── DESIGN.md
├── PRD.md
└── IMPLEMENT.md
```

---

## Commands

All work is done through [Taskfile](https://taskfile.dev). Run `task --list` for the full menu.

```bash
task install          # Install all dependencies (uv sync + bun install)
task dev              # Start all services (backend, frontend, liquidsoap, icecast)
task dev:backend      # FastAPI on :8001
task dev:frontend     # Vite dev server on :5173
task dev:liquidsoap   # Liquidsoap audio engine
task dev:icecast      # Icecast broadcast server on :8000
task test             # Run all tests
task test:backend     # pytest (with coverage)
task test:frontend    # vitest
task lint             # ruff + eslint
task format           # Auto-format code
task db:migrate       # Run Alembic migrations
task db:revision MSG="..." # Create new migration
```

---

## Architecture Overview

Three processes run on the host: **FastAPI** (API + scheduler), **Liquidsoap** (audio engine), **Icecast** (HTTP broadcast).

```
React SPA ←(HTTP/WS)→ FastAPI ←(ORM)→ SQLite
    │                      │
    │ HTTP audio           │ Telnet control
    └──→ Icecast 2 ←──── Liquidsoap ←── Music library + jingles
         (:8000/raidio.mp3)
```

### Data flow — playback
1. User submits playlist via SPA → FastAPI persists and tells Liquidsoap what to play next.
2. Liquidsoap decodes, applies crossfade/gapless, pushes continuous MP3 stream to Icecast.
3. All listeners connect to the same Icecast mount point.
4. FastAPI broadcasts "now playing" updates over WebSocket, delayed by Icecast buffer offset (~3s).

### Data flow — scan
Admin triggers scan → FastAPI walks library tree with Mutagen for tags (Phase A, ~500 files/sec) → then runs ffmpeg silencedetect in parallel workers (Phase B, slow/background) → progress streamed via WebSocket.

---

## Data Model (key tables)

- **`tracks`** — one row per audio file (path, hash, tags, duration, analysis status)
- **`quiet_passages`** — detected intro/outro silence regions per track
- **`jingles`** — minimal track shape, separate from library
- **`playlists`** — auto (admin) or user_session (submitted to queue)
- **`playlist_items`** — ordered tracks/jingles with optional overlay positions
- **`live_queue`** — active broadcast queue with state (pending/playing/played/skipped)
- **`settings`** — singleton key/value, loaded at startup
- **`scan_jobs`** — audit trail of library/jingle scans
- **FTS5** virtual table on tracks for fuzzy search

All times UTC, all durations in milliseconds. See `DESIGN.md §5` for full schema with indices and constraints.

---

## API Surface

**REST under `/api/v1`** + two WebSocket channels.

**Public (no auth):**
- `GET /tracks` — search + cursor-paginated browse (FTS5-backed, p95 ≤ 500ms on 100k rows)
- `GET /tracks/{id}`, `GET /tracks/{id}/cover`
- `GET /artists`, `/albums`, `/genres` — facet listings
- `GET /jingles`
- `GET /now-playing` — current + prev 3 / next 3
- `POST /queue/playlists` — submit user playlist
- `WS /ws/now-playing` — live track-change updates

**Admin (JWT auth from `/admin/login`):**
- Scan: `POST /admin/scan/library`, `POST /admin/scan/jingles`, `GET /admin/scan/status`, `WS /ws/admin/scan`
- Settings: `GET/PUT /admin/settings`
- Queue control: `POST /admin/queue/skip`, `PUT /admin/queue/reorder`, `DELETE /admin/queue/{id}`, `POST /admin/queue/insert-jingle/{jingle_id}`
- Auto-playlists: full CRUD
- Stats: `GET /admin/stats`
- Track analysis: `POST /admin/tracks/{id}/reanalyze`

**Audio stream:** `GET http://host:8000/raidio.mp3` (served by Icecast, not FastAPI)

---

## Frontend Routes

| Route | Purpose | Auth |
|-------|---------|------|
| `/` | Player — full-bleed album art, now-playing, visualizer, local controls | None |
| `/create` | Playlist creator — two-pane drag-and-drop builder | None |
| `/admin/login` | Admin login form | None |
| `/admin` | Dashboard, scan, settings, queue management, auto-playlists | JWT |

**State management:** Zustand (global state), React Query (server data + caching), WebSocket events dispatch into Zustand stores.

**Key UI libraries:** react-virtuoso (100k-row virtualization), @dnd-kit (drag-and-drop), Web Audio API (visualizer).

---

## Scheduling Logic

Round-robin between user playlists: with playlists A, B, C, the broadcast plays `A1, B1, C1, A2, B2, C2, …`. Late joiners enter at the next cycle. When exhausted, playlists drop out. When nothing is queued, falls back to admin-configured idle behavior (auto-playlist / random / silence).

---

## Configuration

Environment variables in `backend/.env` (see `.env.example`):
- Admin credentials (`ADMIN_EMAIL`, `ADMIN_PASSWORD_HASH`, `JWT_SECRET`)
- Paths (`LIBRARY_PATH`, `JINGLES_PATH`, `COVER_CACHE_PATH`)
- Liquidsoap connection (`LIQUIDSOAP_HOST`, `LIQUIDSOAP_TELNET_PORT`)
- Icecast connection (`ICECAST_HOST`, `ICECAST_PORT`, `ICECAST_MOUNT`, `ICECAST_SOURCE_PASSWORD`)

Settings are editable at runtime via the admin UI (source of truth). `.env` is bootstrap only.

---

## Implementation Phases

Work through `IMPLEMENT.md` phases **in order**. Each has an exit criteria checklist — don't skip ahead.

| Phase | Goal | Key Deliverables |
|-------|------|-----------------|
| **0** | Repo scaffold & tooling | Taskfile, FastAPI hello-world, React shell, DB scaffold |
| **1** | Audio plumbing skeleton | Liquidsoap → Icecast → browser plays a hardcoded MP3 |
| **2** | Library scanner & catalog | Scanner Phase A, FTS5 search, browse UI |
| **3** | Live broadcast & queueing | Scheduler, round-robin, user playlists, gapless/crossfade |
| **4** | Admin, jingles, audio analysis | Auth, settings UI, jingle ducking, silencedetect workers |
| **5** | Polish & benchmarking | Themes, visualizer, save/load, Playwright E2E, code_quality.md |

---

## Testing Strategy

| Tier | Scope | Tools | Targets |
|------|-------|-------|---------|
| Unit | Pure functions (scheduler, FTS, name gen, silencedetect parser) | pytest, vitest | ≥ 90% on `backend/raidio/core/` |
| Functional | API endpoints + WebSocket flows | httpx.AsyncClient, fake Liquidsoap | ≥ 80% backend overall |
| Integration | Full stack (FastAPI + real Liquidsoap with file sink) | Playwright | All happy paths from PRD |

**Naming:** `test_*.py` (backend), `*.test.tsx` (frontend). Tests live next to the code they test.

---

## Coding Conventions

1. **One phase at a time.** Don't start Phase N+1 until Phase N exit criteria are met and committed.
2. **Commit per task, not per phase.** Reference task number: `feat(scanner): implement Phase A walker — task 2.4`
3. **Run `task lint && task test` before every commit.** CI enforces this.
4. **No silent skips.** If a task is blocked, leave a `<!-- note: -->` and ask.
5. **Match existing style** in any file you edit.
6. **Update `code_quality.md` incrementally** — don't leave it for the end.
7. **Functions under 50 lines.** Comments for complex logic only.
8. **No hardcoded secrets.** All sensitive values from `.env`.
9. **Handle errors explicitly.** No silent failures.
10. **Liquidsoap scripts stay under 100 lines.** Treat as configuration, not application code.

---

## Key Design Decisions (context for why things are the way they are)

- **Liquidsoap + Icecast** (not per-browser `<audio>`): Required for synchronized multi-listener playback. Per-browser drifts within seconds; building a custom MP3 muxer is weeks of work. Liquidsoap handles gapless, crossfade, and ducking out of the box.
- **Now-playing delay**: Icecast buffers 3–10 seconds, so UI track-change events are delayed by `icecast_buffer_offset_ms` (default 3000) so they match what listeners actually hear.
- **FTS5 for search**: SQLite built-in, prefix-fuzzy, combined with SQL-level filters for year/duration. Cursor-based pagination for smooth scrolling on 100k+ rows.
- **Scanner two-phase**: Phase A (tags) is fast (~500 files/sec) and unblocks the UI immediately. Phase B (ffmpeg silencedetect) is slow (~2–4s per track) but runs in background with parallel workers; library is fully usable without it.
- **No user auth for LAN**: Acceptable for home use. Users get auto-generated funny names (adjective_scientist format) stored in localStorage. Admin is the only authenticated role (JWT, 7-day expiry).
- **MP3-only for v1**: Scanner handles tag reading generically via Mutagen; Liquidsoap natively decodes FLAC if needed later. The `<audio>` element receives transcoded MP3 from Icecast regardless.

---

## Risks & Gotchas

- **Liquidsoap is a DSL** — debugging requires reading `.liq`. Keep scripts short and commented.
- **Icecast latency can drift** — now-playing indicator may be off by 1–2 seconds. Acceptable for personal radio.
- **CORS for visualizer** — Icecast must send `Access-Control-Allow-Origin: *`. Visualizer gracefully degrades if unavailable.
- **Silencedetect is slow** — 100k tracks = 14–28 hours with 4 workers. This is by design; it runs in background.
- **SQLite concurrency** — single-writer. FastAPI uses async sessions; WAL mode should be enabled for read concurrency.
