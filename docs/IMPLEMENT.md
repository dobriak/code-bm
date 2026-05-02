# Raidio — Implementation Plan

**Companion docs:** [`DESIGN.md`](./DESIGN.md), [`PRD.md`](./PRD.md)
**Audience:** Coding agent (or human implementer) working through milestones sequentially.

---

## How to use this document

- Work through phases **in order**. Each phase ends in a working, demonstrable state.
- Check off `[ ]` → `[x]` as tasks complete. Don't skip ahead — later tasks assume earlier ones are done.
- Each phase has an **Exit criteria** block. Don't move on until every item there is true.
- "DoD" = Definition of Done. Every code task implies: code written, types correct, lint clean, tests added, tests passing.
- When a task says **"Read first: <path>"**, read that file/skill before writing code. The codebase has conventions that matter.
- If a task is blocked or ambiguous, stop and ask before guessing. Notes belong in the task as `<!-- note: ... -->`.

---

## Phase 0 — Repository scaffold & tooling

**Goal:** A clean repo where `task install` and `task dev` work end-to-end against placeholder code.

### 0.1 Repository structure
- [x] Create top-level directories per `DESIGN.md` §14: `backend/`, `frontend/`, `liquidsoap/`, `database/`, `docs/`, `cache/covers/`.
- [x] Add `.gitignore` covering: `database/raidio.db`, `cache/`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `.env`, `*.log`.
- [x] Add an MIT (or chosen) `LICENSE` file.
- [x] Add `README.md` at repo root linking to `DESIGN.md`, `PRD.md`, `IMPLEMENT.md`, `code_quality.md`.

### 0.2 Backend bootstrap (Python 3.12 + uv)
- [x] `backend/pyproject.toml` with project metadata, Python ≥ 3.12, dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `alembic`, `pydantic`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `mutagen`, `python-multipart`, `httpx`, `websockets`.
- [x] Dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `httpx`.
- [x] `backend/.env.example` with every variable from `DESIGN.md` §11 (no real secrets).
- [x] `backend/raidio/__init__.py` exposes `__version__`.
- [x] `backend/raidio/main.py` minimal app: `GET /api/v1/health` returns `{"status": "ok", "version": __version__}`.
- [x] Confirm `uv sync` and `uv run uvicorn raidio.main:app --reload` work.

### 0.3 Frontend bootstrap (React + TS + Bun)
- [x] `bun create vite frontend --template react-ts`, then commit.
- [x] Install runtime deps: `react-router-dom`, `zustand`, `@tanstack/react-query`, `@dnd-kit/core`, `@dnd-kit/sortable`, `react-virtuoso`.
- [x] Install dev deps: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@playwright/test`, `eslint`, `prettier`.
- [x] Configure ESLint + Prettier; add `bun lint` and `bun format` scripts.
- [x] `frontend/src/App.tsx` shows "Raidio" and pings `/api/v1/health` via React Query.
- [x] Vite dev server proxies `/api` and `/ws` to the backend on `:8001`.

### 0.4 Database scaffold
- [x] `backend/raidio/db/base.py` — SQLAlchemy `DeclarativeBase`.
- [x] `backend/raidio/db/session.py` — engine + `async_sessionmaker`, points at `database/raidio.db` (path from settings).
- [x] `backend/raidio/db/settings.py` — `pydantic-settings` loader for `.env`.
- [x] Initialize Alembic in `backend/alembic/`; first revision creates an empty schema (no tables yet).
- [x] On app startup, ensure `database/` directory exists and run `alembic upgrade head`.

### 0.5 Taskfile orchestration
- [x] `Taskfile.yml` at root with tasks:
  - `install` → installs backend (`uv sync`) and frontend (`bun install`) deps
  - `dev:backend` → runs FastAPI on `:8001`
  - `dev:frontend` → runs Vite on `:5173`
  - `dev:liquidsoap` → placeholder (echo "not implemented yet")
  - `dev:icecast` → placeholder
  - `dev` → runs all four in parallel
  - `test:backend`, `test:frontend`, `test` → all
  - `lint`, `format`
  - `db:migrate`, `db:revision -- "msg"`
- [x] Confirm `task --list` shows all tasks and `task install && task dev:backend` works.

### 0.6 CI skeleton (optional but recommended)
- [x] `.github/workflows/ci.yml` runs `task lint && task test` on push.

### Exit criteria — Phase 0
- [x] `task install && task dev` runs without errors (Liquidsoap/Icecast tasks may be placeholders).
- [x] Browser at `http://localhost:5173` shows "Raidio" and a green "backend ok" indicator.
- [x] `task test` runs (zero tests is fine for now).

---

## Phase 1 — Audio plumbing skeleton

**Goal:** A hardcoded MP3 file plays from Liquidsoap → Icecast → browser. No database, no scheduler. Proves the streaming chain works.

### 1.1 Icecast setup
- [x] Add `liquidsoap/icecast.xml` template with: source password from env, mount `/raidio.mp3`, port 8000, permissive CORS (`Access-Control-Allow-Origin: *`).
- [x] Add `Taskfile` task `dev:icecast` that runs `icecast -c liquidsoap/icecast.xml` (with envsubst for variable injection).
- [x] Document Icecast install in root `README.md` (apt/brew/Docker).

### 1.2 Liquidsoap baseline script
- [x] `liquidsoap/raidio.liq` with: a `request.queue()` named `main`, a `single("test.mp3")` fallback, output to Icecast using env-injected source password and mount path.
- [x] `dev:liquidsoap` task runs `liquidsoap liquidsoap/raidio.liq` with env vars passed through (via envsubst template).
- [x] Place a royalty-free test MP3 at `liquidsoap/test.mp3` (generated 440Hz sine tone via ffmpeg).

### 1.3 Browser audio element
- [x] `frontend/src/components/PlayerAudio.tsx` — a hidden `<audio>` element with `src="http://localhost:8000/raidio.mp3"`, `crossOrigin="anonymous"`, plus a one-time "Click to start" overlay to satisfy autoplay policy.
- [x] Mount it in `App.tsx`.
- [x] Add a basic volume slider and pause/resume controls (operate on the local `<audio>` only — not the broadcast).

### 1.4 Liquidsoap control client (backend)
- [x] `backend/raidio/streaming/liquidsoap.py` — async client over Liquidsoap's telnet port.
  - [x] Methods: `push(uri)`, `skip()`, `set_var(name, value)`, `queue_size()`, `current_metadata()`.
  - [x] Connection pooled, reconnects on failure, raises typed exceptions.
- [x] Wire client into FastAPI app state (singleton, created on startup).
- [x] Add `POST /api/v1/admin/queue/skip` (no auth yet) that calls `client.skip()`.

### 1.5 Tests
- [x] Unit tests for `LiquidsoapClient` against an `asyncio.start_server` fake that records commands.
- [x] Integration test: with `dev:liquidsoap` and `dev:icecast` running locally, hit `/api/v1/health` and verify Icecast responds at `:8000/raidio.mp3` with a 200 + `audio/mpeg`.

### Exit criteria — Phase 1
- [x] Open the frontend in two browser tabs → click "Start" → both hear the same audio in sync.
- [x] POST to skip endpoint → audio cuts; Liquidsoap falls back to the `single()` source.
- [x] Test suite green.

---

## Phase 2 — Library scanner & catalog

**Goal:** Admin can point Raidio at a folder of MP3s and the database fills with rows. Browsing and search work in the UI. No streaming integration yet — Phase 1's hardcoded file still plays.

### 2.1 SQLAlchemy models
- [x] `backend/raidio/db/models.py` — implement every table from `DESIGN.md` §5:
  - [x] `Track`, `QuietPassage`, `Jingle`, `Playlist`, `PlaylistItem`, `LiveQueueItem`, `Setting`, `ScanJob`.
  - [x] All foreign keys, enums (`AnalysisStatus`, `QuietRegion`, `PlaylistKind`, `LiveQueueState`, `IdleBehavior`, `ScanKind`), check constraints.
- [x] Indices per `DESIGN.md` §5.2.
- [x] Alembic revision: `0002_initial_schema`.
- [x] Apply with `task db:migrate`.

### 2.2 Settings bootstrap
- [x] On startup, ensure `settings` table has exactly one row; if missing, insert defaults: `crossfade_enabled=False`, `crossfade_duration_ms=4000`, `gapless_enabled=True`, `jingle_duck_db=-12.0`, `icecast_buffer_offset_ms=3000`, `idle_behavior='random'`, `library_path` and `jingles_path` from env.

### 2.3 FTS5 virtual table
- [x] `backend/raidio/db/fts.py` — raw SQL to create `tracks_fts` virtual table over `(artist, album, title, genre)` with content table sync triggers.
- [x] Alembic revision: `0003_fts5`.
- [x] Helper: `def fts_query(text: str) -> str` that escapes user input and produces an FTS5 MATCH expression with prefix-fuzzy semantics (per `DESIGN.md` §8).

### 2.4 Scanner — Phase A (tag extraction)
- [x] `backend/raidio/scanner/walker.py` — `scan_library(path)` async generator yielding `(absolute_path, file_size, mtime)` for every `.mp3`.
- [x] `backend/raidio/scanner/tags.py` — `read_tags(path) -> TrackTags` using Mutagen; extract: artist, album, title, genre, year, track number, disc number, duration, bitrate, sample rate, embedded cover art (bytes + mime).
- [x] `backend/raidio/scanner/cover_cache.py` — `store_cover(bytes, mime) -> Path` writing to `cache/covers/<sha1>.jpg|png`, deduplicated by hash.
- [x] `backend/raidio/scanner/library_scanner.py` — orchestrator:
  - [x] Computes `file_hash` (sha1 of first 64 KiB + size).
  - [x] Upserts `Track` rows.
  - [x] Detects removed files (path no longer exists, hash unique to removed path).
  - [x] Records progress in a `ScanJob` row.
- [x] Targets: ≥ 500 files/sec on SSD (`DESIGN.md` §6).

### 2.5 Scanner triggering API
- [x] `POST /api/v1/admin/scan/library` — kicks off Phase A as a background asyncio task. Returns `scan_job_id`.
- [x] `POST /api/v1/admin/scan/jingles` — same for jingles directory.
- [x] `GET /api/v1/admin/scan/status` — current/recent jobs with counts.
- [x] `WebSocket /ws/admin/scan` — emits `{phase, total, done, current_path}` events.
- [x] **Note:** auth not yet enforced; mark these endpoints with a TODO and add `# TODO(phase4): require admin JWT`.

### 2.6 Catalog read API (public)
- [x] `GET /api/v1/tracks` — query params per `DESIGN.md` §9. Cursor-based pagination keyed on `(artist, album, track_number, id)`.
- [x] `GET /api/v1/tracks/{id}` — full detail incl. quiet passages (empty list for now).
- [x] `GET /api/v1/tracks/{id}/cover` — streams the file from `cache/covers/`.
- [x] `GET /api/v1/artists`, `/albums`, `/genres` — facet listings with counts.
- [x] `GET /api/v1/jingles`.

### 2.7 Frontend — admin scan panel (minimal, unauthenticated)
- [x] `/admin` route renders an `AdminScanPanel` component (auth comes in Phase 4).
- [x] Two buttons: "Scan library", "Scan jingles".
- [x] Live progress bar + tail of recent paths via WebSocket.

### 2.8 Frontend — browse & search
- [x] `/create` route shows the playlist creator's left pane only for now: a virtualized track list (`react-virtuoso`).
- [x] Search box on top wired to `GET /tracks?q=`.
- [x] Faceted filters (artist, album, genre, year range, duration range) in a sidebar.
- [x] Hierarchical browse: Genres → Artists → Albums → Songs (tabs or breadcrumb nav).
- [x] Each track row shows artist–album–title and a placeholder marker for quiet passages (always neutral "pending" for now).

### 2.9 Tests
- [x] Unit: `read_tags` against a curated set of test MP3s with edge cases (missing tags, weird encodings, no cover art).
- [x] Unit: `fts_query` escape/build logic.
- [x] Functional: scanner against a temp directory of generated tiny MP3s (use `pydub` or pre-baked fixtures); assert correct row counts, correct removal detection.
- [x] Functional: every API endpoint with httpx.AsyncClient.
- [x] Frontend: Vitest tests for the search component and track-table virtualization.

### Exit criteria — Phase 2
- Point `LIBRARY_PATH` at a real folder of ≥ 1000 MP3s, click "Scan library" → all tracks land in DB within 1 minute (SSD).
- Search "beatles" returns relevant results in ≤ 500 ms.
- Browse Genres → Artists → Albums → Songs works at every level.
- `task test` green; backend coverage ≥ 80% on `scanner/` and `api/`.

---

## Phase 3 — Live broadcast & queueing

**Goal:** Real broadcast driven by user playlists. Round-robin scheduling. Gapless and crossfade work. The hardcoded test MP3 from Phase 1 is gone.

### 3.1 Funny-name generator
- [x] `backend/raidio/core/names.py` — adjective + scientist word lists (commit lists into repo per PRD §9 recommendation).
- [x] `generate_name() -> str` returns `"<adjective>_<scientist>"`.
- [x] Mirror the same lists in `frontend/src/lib/names.ts` so generation is client-side (no roundtrip).

### 3.2 Frontend — user identity
- [x] On first load, generate funny name client-side, persist to `localStorage.raidio.user_label`.
- [x] Header shows current name; click → "New name" button re-rolls.
- [x] All POSTs that create playlists send `X-Raidio-User: <label>`.

### 3.3 Scheduler — core logic
- [x] `backend/raidio/core/scheduler.py` — pure round-robin function:
  - [x] Input: list of playlists (each a list of items) + per-playlist cursors.
  - [x] Output: next item to enqueue, advanced cursors.
  - [x] No I/O. Fully unit-testable.
- [x] Scheduler tests cover: single playlist, multiple playlists, late-joiner, exhaustion, empty case.

### 3.4 Scheduler — runtime
- [x] `backend/raidio/streaming/broadcaster.py` — long-running asyncio task that:
  - [x] Watches `live_queue` table + active `user_session` playlists.
  - [x] Calls scheduler logic to determine next item.
  - [x] Pushes URIs to Liquidsoap when the queue depth in Liquidsoap drops below 2.
  - [x] Handles idle behavior: random track from library, default auto-playlist, or silence.
- [x] Started in FastAPI's `lifespan` context.
- [x] Reacts to `request.on_air` events from Liquidsoap (subscribe via telnet) to update `LiveQueueItem.state` and `started_at`/`ended_at`.

### 3.5 Now-playing state
- [x] `backend/raidio/core/now_playing.py` — tracks current/prev3/next3 from `live_queue`.
- [x] Aligns the "current track" emit time to `now() + icecast_buffer_offset_ms` so listener UIs match what they hear (per `DESIGN.md` §4 latency caveat).
- [x] `GET /api/v1/now-playing` returns the structured shape.
- [x] `WebSocket /ws/now-playing` pushes updates on every track change.

### 3.6 Playlist submission
- [x] `POST /api/v1/queue/playlists` — body: `{name, notes, items: [{track_id?, jingle_id?, overlay_at_ms?}], owner_label}`. Persists as `playlist.kind='user_session'` and registers it with the scheduler.
- [x] Validation: at least one item, items reference real tracks/jingles, only one of track_id/jingle_id set per item (unless overlay).
- [x] Returns: estimated time-to-play of the playlist's first item.

### 3.7 Liquidsoap — gapless + crossfade
- [x] Update `liquidsoap/raidio.liq`:
  - [x] Wrap main queue in `crossfade(duration=...)` controlled by a `var.set` variable from the backend.
  - [x] Configure for gapless via `audio_to_stereo` + appropriate buffer settings.
  - [x] Remove the `single("test.mp3")` fallback; on empty queue, pull from the idle source per settings.
- [x] Backend toggles `crossfade_enabled` and `crossfade_duration_ms` via `LiquidsoapClient.set_var`.

### 3.8 Frontend — player view
- [x] `/` route: `<NowPlaying />` component.
  - [x] Full-bleed album art (≥ 80% viewport height by default).
  - [x] Prev-3 / next-3 strip with artist + title.
  - [x] Subscribes to `/ws/now-playing`.
  - [x] Standard local controls (volume, mute, local pause). Tooltip clarifies these are local.
  - [x] Remaining time of currently playing song (computed from `started_at` + duration).

### 3.9 Frontend — playlist creator (right pane)
- [x] Two-pane layout in `/create` (left pane from Phase 2, right pane new).
- [x] Drag from left → right adds to playlist (dnd-kit).
- [x] Reorder within right pane.
- [x] Name (required) + notes (optional) fields.
- [x] "Feeling lucky" button: `GET /api/v1/tracks/random` (add this endpoint).
- [x] "Send to queue" button: POSTs to `/api/v1/queue/playlists`, shows toast.

### 3.10 Tests
- [x] Unit: scheduler logic (already in 3.3).
- [x] Functional: end-to-end queue submission against a fake Liquidsoap that records pushed URIs; assert round-robin order with multiple submissions.
- [x] Integration: real Liquidsoap configured with a file sink instead of Icecast; submit a 3-track playlist, assert audio file contains 3 distinct tracks.
- [x] Frontend: drag-and-drop works in Vitest with @testing-library + dnd-kit test utilities.

### Exit criteria — Phase 3
- Two browser tabs (different funny names) each submit a 5-track playlist → broadcast plays them interleaved A1, B1, A2, B2, … with no audible gaps.
- Toggling crossfade in admin (set the setting via DB for now) takes effect within one track transition.
- Now-playing UI updates within ~1 s of actual track change.
- Coverage on `core/scheduler.py` ≥ 95%.

---

## Phase 4 — Admin console, jingles, audio analysis

**Goal:** Lock the admin surface behind auth. Implement settings UI, jingle live drops with ducking, and the slow audio-analysis worker pool that fills `quiet_passages`.

### 4.1 Admin authentication
- [x] `backend/raidio/core/auth.py`:
  - [x] Bcrypt password verification against `ADMIN_PASSWORD_HASH` from env.
  - [x] JWT issuance (HS256, 7-day expiry, signed with `JWT_SECRET`).
  - [x] FastAPI dependency `require_admin` that validates JWT from `Authorization: Bearer …`.
- [x] `POST /api/v1/admin/login` — body: `{email, password}`. Returns `{access_token}`. Generic error message on failure.
- [x] Apply `require_admin` to every `/api/v1/admin/*` route. Remove the Phase 2 TODOs.

### 4.2 Frontend — admin login & gating
- [x] `/admin/login` page with form.
- [x] Store JWT in `localStorage.raidio.admin_jwt`.
- [x] React Query interceptor adds `Authorization` header when present.
- [x] On 401, redirect to `/admin/login`.
- [x] All admin pages gated behind a route guard.

### 4.3 Admin dashboard
- [x] `GET /api/v1/admin/stats` — counts of tracks/artists/albums/genres + total playtime + queue length + broadcast status.
- [x] `<AdminDashboard />` component renders these.

### 4.4 Settings UI
- [x] `GET /api/v1/admin/settings`, `PUT /api/v1/admin/settings`.
- [x] `<AdminSettings />` form with validation:
  - [x] Library path, jingles path (string).
  - [x] Idle behavior (enum dropdown).
  - [x] Default auto-playlist (dropdown of auto-playlists).
  - [x] Crossfade on/off + duration (0–10 s).
  - [x] Gapless on/off.
  - [x] Jingle duck depth (−24 to 0 dB).
  - [x] Icecast buffer offset (0–10000 ms).
  - [x] Minimum quiet-passage duration (1–10 s).
- [x] PUT triggers Liquidsoap `set_var` calls so changes take effect immediately.

### 4.5 Audio analysis — Phase B of scanner
- [x] `backend/raidio/scanner/audio_analysis.py`:
  - [x] Worker pool of N async tasks (N = `min(os.cpu_count(), 4)`) consuming an `asyncio.Queue`.
  - [x] Each worker shells out to `ffmpeg -i <file> -af silencedetect=noise=-30dB:d=<min_quiet_s> -f null -` and parses stderr for `silence_start`/`silence_end`.
  - [x] Filters: only intro (first 60 s) or outro (last 120 s); only tracks > 240 s; only duration ≥ `settings.min_quiet_duration_s`.
  - [x] Writes `QuietPassage` rows; updates `Track.audio_analyzed_at` and `analysis_status`.
  - [x] Errors set `analysis_status='error'` and store message in `analysis_error`.
- [x] Hook: at end of Phase A scan, enqueue every changed track into Phase B.
- [x] `POST /api/v1/admin/tracks/{id}/reanalyze` — clears analysis, re-enqueues.

### 4.6 Frontend — quiet-passage indicators
- [x] Update track-row marker logic from "always pending" (Phase 2) to real states: `done` (show start/end on hover), `pending` (neutral), `error` (red, hover shows error).
- [x] In the playlist creator, dragging a jingle onto a quiet-passage marker creates an `overlay_at_ms` item.

### 4.7 Jingles — live drop with ducking
- [x] Liquidsoap: add an interrupt source `jingles_queue = request.queue()` and combine with main using `smooth_add(normal=main, special=jingles_queue, p=lambda)` where `p` controls duck depth.
- [x] Expose `jingle_duck_db` as a Liquidsoap variable that the script reads when computing the smooth_add factor.
- [x] Backend: `POST /api/v1/admin/queue/insert-jingle/{jingle_id}` pushes the jingle path onto the interrupt queue.
- [x] Backend: for playlist items with `overlay_at_ms`, schedule a delayed task to push the jingle onto the interrupt queue at the right offset (use Liquidsoap's `on_metadata` callback to learn track-start time precisely).

### 4.8 Live queue management UI
- [x] `GET /api/v1/admin/queue` — current `live_queue` + active user playlists.
- [x] `PUT /api/v1/admin/queue/reorder` — body: `[{id, position}, …]`.
- [x] `DELETE /api/v1/admin/queue/{id}` — removes pending item.
- [x] `POST /api/v1/admin/queue/skip` (already exists from Phase 1) — wire into broadcaster to mark current as `skipped`.
- [x] `<AdminQueue />` component: drag-to-reorder pending items, delete buttons, "Skip current" button with 2-s undo toast, "Insert jingle" button per jingle.

### 4.9 Auto-playlists CRUD
- [x] `POST /api/v1/admin/auto-playlists`, `GET /…/{id}`, `PUT /…/{id}`, `DELETE /…/{id}`, `GET /…` (list).
- [x] `<AdminAutoPlaylists />` page reusing the playlist-creator component but with admin-only "set as default" toggle.

### 4.10 Tests
- [x] Unit: JWT issuance/verification, password hashing.
- [x] Functional: login flow, 401 on bad token, all admin endpoints with auth.
- [x] Functional: silencedetect parser against canned ffmpeg output strings.
- [x] Integration: real ffmpeg run on a test MP3 with a known quiet section; assert quiet_passages row.
- [x] Integration: jingle live-drop with file-sink Liquidsoap; assert jingle audio overlays main audio.

### Exit criteria — Phase 4
- Admin can log in, change crossfade duration in UI, hear it apply on next track.
- Admin clicks "Insert jingle" → jingle audibly overlays current track at correct duck depth; track keeps playing.
- After scanning a folder with songs > 4 min, quiet passages populate within minutes; track rows show indicators.
- Backend coverage ≥ 80% overall, ≥ 90% on `core/`.

---

## Phase 5 — Polish, persistence, and benchmarking

**Goal:** Every PRD user story is met. Visual polish complete. `code_quality.md` populated.

### 5.1 Theme & full-screen art
- [x] `frontend/src/lib/theme.ts` — toggle dark/light via `data-theme` attribute on `<html>`. Persist in `localStorage.raidio.theme`. Default = system preference.
- [x] CSS variables for both themes; audit every component for theme-correctness.
- [x] Full-screen art toggle on the player: hides chrome, expands art. Persist in `localStorage.raidio.fullscreen_art`.

### 5.2 Web Audio visualizer
- [x] `frontend/src/components/Visualizer.tsx`:
  - [x] `AudioContext` + `AnalyserNode` connected to the broadcast `<audio>` element.
  - [x] Two modes: 32-band bars (canvas) and sine wave. Toggle button cycles modes + off.
  - [x] Smoothing constant tuned for "musical" feel (≈ 0.85).
  - [x] On CORS error or `crossOrigin` failure, hide toggle (graceful degradation per PRD §4.1).
- [x] Persist user choice in `localStorage.raidio.visualizer_mode`.

### 5.3 Playlist save/load (.raidio JSON)
- [x] Format spec in `docs/playlist-format.md`:
  ```json
  {
    "raidio_version": 1,
    "name": "...",
    "notes": "...",
    "items": [
      {"type": "track", "path": "..."},
      {"type": "jingle", "path": "...", "overlay_at_ms": 12000}
    ]
  }
  ```
- [x] Save: serialize current builder state, trigger browser download.
- [x] Load: file picker → validate → resolve track/jingle paths to IDs via `POST /api/v1/tracks/resolve-paths` → restore builder state.
- [x] Mismatch handling: report tracks not found in current library; load the rest with a warning toast.

### 5.4 Feeling Lucky
- [x] `GET /api/v1/tracks/random` — uniformly samples one track from full library (use `ORDER BY RANDOM() LIMIT 1` — fine on SQLite up to ~1M rows).
- [x] Wire button in playlist creator.

### 5.5 Cross-cutting UX polish
- [x] Loading skeletons on every list (no spinner-on-blank).
- [x] Empty states with helpful copy ("No tracks yet — scan your library").
- [x] Error boundaries on each route.
- [x] Keyboard shortcuts in playlist creator: `/` focuses search, `Enter` adds top result, `r` triggers Feeling Lucky.
- [x] Touch targets ≥ 44 px on mobile breakpoints.
- [x] Audit accessibility: keyboard nav through all interactive elements, ARIA labels on icon buttons, contrast ratio ≥ 4.5:1.

### 5.6 Integration tests (Playwright)
- [x] User journey 1: scan library → search → build playlist → submit → verify in admin queue.
- [x] User journey 2: two browsers submit playlists → verify round-robin order in queue API.
- [x] User journey 3: admin login → change settings → trigger jingle drop.
- [x] User journey 4: save playlist file → reload page → load playlist file → state restored.

### 5.7 Documentation
- [x] `backend/README.md` — running, env vars, endpoint reference (link to `/docs` Swagger), extension guide.
- [x] `frontend/README.md` — component hierarchy, state management overview.
- [x] `docs/index.md` — wiki-style index linking to design, PRD, implementation, playlist format, deployment.
- [x] `docs/deployment.md` — how to run on a home server (systemd unit examples, Docker compose alternative).
- [x] Root `README.md` — quickstart, prerequisites, screenshots.

### 5.8 Benchmark recording
- [x] `code_quality.md` populated with:
  - [x] Backend coverage report (target ≥ 80% overall, ≥ 90% on `core/`).
  - [x] Frontend coverage report (target ≥ 70%).
  - [x] Lint pass status (ruff, eslint).
  - [x] Type-check pass status (mypy strict on `core/`, tsc strict on frontend).
  - [x] Search latency p95 measurement on a 100k-track library.
  - [x] Scan throughput measurement (files/sec).
  - [x] Listener sync drift measurement (ms between two browsers).

### Exit criteria — Phase 5
- Every user story in `PRD.md` §4 has a passing test or manual verification note.
- All four Playwright journeys green.
- `code_quality.md` shows all bars met.
- Manual smoke test on a phone browser: player works, builder works, admin works.

---

## Cross-phase backlog (deferred to vNext)

These are explicitly out of scope per `PRD.md` §7 but worth tracking:

- [x] FLAC support (transcoding pipeline + Safari fallback).
- [x] Audio analysis beyond silencedetect: key, BPM, danceability.
- [x] Smart auto-playlists ("more like this").
- [x] Listener-side voting / reactions / skip requests.
- [x] Recording the broadcast to disk.
- [x] Filesystem watcher for auto-rescan.
- [x] Multi-user auth, internet-facing deployment, HTTPS.
- [x] Native mobile apps.
- [x] Last.fm scrobbling.

---

## Working agreements for the implementing agent

1. **One phase at a time.** Don't start Phase N+1 until the exit criteria of Phase N are met and committed.
2. **Commit per task, not per phase.** Small commits; messages reference the task number (e.g. `feat(scanner): implement Phase A walker — task 2.4`).
3. **Tests live with the code they test**, named `test_*.py` (backend) or `*.test.tsx` (frontend).
4. **No silent skips.** If a task can't be done as written, leave a `<!-- note: -->` and ask.
5. **Read the conventions of files you're editing before adding to them.** Match style.
6. **Run `task lint && task test` before every commit.** CI will catch you anyway.
7. **Update `code_quality.md` incrementally** — don't leave it for Phase 5.7.
