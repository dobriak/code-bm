# Raidio — System Design

**Status:** Draft v1
**Audience:** Implementer (you) + future contributors
**Companion doc:** [`PRD.md`](./PRD.md) — product requirements & user stories

---

## 1. Summary

Raidio is a single-host, LAN-only personal radio station. One audio stream is produced by the server and consumed simultaneously by 1–5 listeners on the local network. Anonymous users contribute playlists that compete in a round-robin scheduler; an admin manages the library, jingles, and live queue.

The defining constraint is **one server-side playhead, many listeners**. This rules out the common "each browser plays its own `<audio>` element" architecture and pushes us toward a server-side audio pipeline that produces a continuous broadcast.

---

## 2. Technology Stack (mandated)

| Layer        | Choice                                       |
| ------------ | -------------------------------------------- |
| Backend      | FastAPI on Python 3.12, managed with `uv`    |
| ORM          | SQLAlchemy 2.x                               |
| Database     | SQLite at `database/raidio.db`               |
| Frontend     | React + TypeScript, built/run with Bun       |
| Task runner  | Taskfile                                     |

**Additional runtime dependencies (chosen, not mandated):**

- **ffmpeg** — file transcoding, silence detection, metadata fallback. Already a hard requirement for `silencedetect`.
- **Liquidsoap** — server-side audio playback engine (gapless, crossfade, ducking, queue management). Pipes its output to Icecast.
- **Icecast 2** — HTTP audio broadcast server. The browser `<audio>` element connects to a single Icecast mount point.
- **Mutagen** (Python) — fast ID3/FLAC tag reading without spawning ffprobe.
- **watchfiles** — *not used*; scanner is manual-only per requirements.

The Liquidsoap + Icecast choice is the most consequential decision in this document and is justified in §4.

---

## 3. High-level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          LAN host (one machine)                     │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐     │
│  │  React SPA   │◄──►│   FastAPI    │◄──►│   SQLite           │     │
│  │  (Bun build) │HTTP│   backend    │ORM │   raidio.db        │     │
│  │              │ WS │              │    │                    │     │
│  └──────┬───────┘    └──────┬───────┘    └────────────────────┘     │
│         │                   │                                       │
│         │ HTTP audio        │ Telnet / harbor control               │
│         │ (Icecast mount)   │                                       │
│         │                   ▼                                       │
│         │            ┌──────────────┐    ┌────────────────────┐     │
│         └───────────►│   Icecast 2  │◄───│   Liquidsoap       │     │
│                      │   (mount)    │ src│   (audio engine)   │     │
│                      └──────────────┘    └─────────┬──────────┘     │
│                                                    │ reads          │
│                                                    ▼                │
│                                          ┌────────────────────┐     │
│                                          │  Music library +   │     │
│                                          │  jingles directory │     │
│                                          └────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

Three processes run on the host: **FastAPI**, **Liquidsoap**, **Icecast**. Taskfile orchestrates `task dev` to start all three (and the Bun dev server).

### 3.1 Data flow — playback

1. User adds a playlist via the SPA (HTTP POST → FastAPI).
2. FastAPI persists/queues it and tells Liquidsoap (via its telnet control port) which file to play next when the current one ends.
3. Liquidsoap decodes the MP3, applies crossfade/gapless logic, and pushes a continuous PCM → MP3 stream to Icecast.
4. All listeners' `<audio src="http://host:8000/raidio.mp3">` elements receive the same stream.
5. FastAPI broadcasts "now playing" + "next 3 / previous 3" updates over WebSocket so every UI updates in lockstep with what listeners are actually hearing.

### 3.2 Data flow — scan

Admin clicks **Scan**. FastAPI launches a background worker (asyncio task) that walks the library tree, reads tags with Mutagen, upserts rows, and queues each file into a separate **analysis** worker pool that runs `ffmpeg -af silencedetect` to find quiet passages. Progress is streamed to the admin UI via WebSocket. See §6.

---

## 4. The streaming decision (why Liquidsoap + Icecast)

Three alternatives were considered:

| Approach                                          | Gapless | Crossfade | Ducking | Sync across listeners | Complexity |
| ------------------------------------------------- | :-----: | :-------: | :-----: | :-------------------: | :--------: |
| Each browser plays its own `<audio>`              |  Hard   |   Hard    |   No    |       **No**          |    Low     |
| FastAPI streams a custom MP3 mux via `StreamingResponse` |   Yes   |    Yes    |   Yes   |        Yes            |   Very High |
| **Liquidsoap → Icecast** (chosen)                 |   Yes   |    Yes    |   Yes   |        Yes            |   Medium   |

The "shared broadcast" requirement (`Q1.3`) makes the per-browser approach unworkable: even if two browsers start the same file at the same instant, drift accumulates and they desync within seconds. Building our own MP3 muxer with crossfade is several weeks of audio-engineering work that Liquidsoap solves out of the box in ~50 lines of `.liq` script. Liquidsoap is purpose-built for community/internet radio stations and natively supports every requirement on our list.

**What FastAPI controls in Liquidsoap:**

- `request.queue.push <uri>` — append a track to the active queue
- `request.queue.consume` — peek/clear pending requests
- `var.set <name> <value>` — toggle crossfade on/off, change duration
- `output.icecast.skip` — skip current track
- A second queue (the "interrupt" source) is used for jingles — Liquidsoap's `smooth_add` operator ducks the main queue underneath the jingle automatically.

**Latency caveat:** Icecast buffers ~3–10 seconds. The "now playing" indicator in each UI must therefore be aligned to **what listeners are hearing**, not what Liquidsoap is currently decoding. We solve this by having Liquidsoap emit a `metadata` callback when a track starts, FastAPI delays that event by the configured Icecast buffer offset before broadcasting it on the WebSocket. This is documented as a tunable in admin settings.

---

## 5. Data Model (SQLAlchemy)

All times in UTC, all durations in milliseconds.

### 5.1 Tables

**`tracks`** — one row per audio file in the library
- `id` PK
- `path` TEXT UNIQUE — absolute path on disk
- `file_hash` TEXT — sha1 of first 64 KiB + size, used to detect moves vs. re-encodes
- `artist`, `album`, `title`, `genre`, `year`, `track_number`, `disc_number`
- `duration_ms` INTEGER
- `bitrate_kbps`, `sample_rate_hz`
- `cover_art_path` TEXT — extracted to `cache/covers/<hash>.jpg`, NULL if none
- `tags_scanned_at`, `audio_analyzed_at` TIMESTAMP — NULL if pending
- `analysis_status` ENUM(`pending`, `running`, `done`, `error`)
- `analysis_error` TEXT NULL

**`quiet_passages`** — many-per-track
- `id` PK, `track_id` FK
- `start_ms`, `end_ms`, `duration_ms`
- `region` ENUM(`intro`, `outro`) — `intro` = within first 60 s, `outro` = within last 120 s
- `db_threshold` REAL — the noise floor used (for re-analysis)

**`jingles`** — same shape as `tracks` but minimal: `id, path, file_hash, title, duration_ms, cover_art_path`. Kept separate to avoid polluting library queries.

**`playlists`** — server-saved playlists (auto-playlists + any user playlist sent to the queue)
- `id` PK, `name`, `notes`
- `kind` ENUM(`auto`, `user_session`) — `auto` is admin-managed; `user_session` is created when a user pushes a playlist to the live queue
- `owner_label` TEXT — the funny name, NULL for auto
- `created_at`, `updated_at`

**`playlist_items`** — ordered tracks (and optional jingles) in a playlist
- `id` PK, `playlist_id` FK, `position` INTEGER
- `track_id` FK NULLABLE
- `jingle_id` FK NULLABLE
- `overlay_at_ms` INTEGER NULLABLE — if set, jingle plays as overlay starting at this offset within the previous track instead of as its own item
- CHECK exactly one of `track_id`/`jingle_id` is non-null (unless `overlay_at_ms` is set, in which case `jingle_id` and the previous row's `track_id` are both relevant)

**`live_queue`** — the active broadcast queue
- `id` PK, `position` INTEGER
- `playlist_id` FK NULLABLE — which user/auto playlist this item came from (for round-robin bookkeeping)
- `track_id` FK NULLABLE, `jingle_id` FK NULLABLE
- `state` ENUM(`pending`, `playing`, `played`, `skipped`)
- `enqueued_at`, `started_at`, `ended_at`

**`settings`** — singleton key/value table, loaded once at startup
- `library_path`, `jingles_path`
- `idle_behavior` ENUM(`auto_playlist`, `random`, `silence`)
- `default_auto_playlist_id`
- `crossfade_enabled` BOOL, `crossfade_duration_ms` INT
- `gapless_enabled` BOOL
- `jingle_duck_db` REAL — how much to attenuate music underneath jingle (default −12 dB)
- `icecast_buffer_offset_ms` INT — for now-playing alignment (default 3000)

**`scan_jobs`** — audit trail of scans
- `id` PK, `kind` ENUM(`library`, `jingles`), `started_at`, `finished_at`, `status`, `tracks_added`, `tracks_updated`, `tracks_removed`, `errors_json`

### 5.2 Indices

- `tracks(artist, album, track_number)` — album browsing
- `tracks(genre)`, `tracks(year)` — filters
- FTS5 virtual table `tracks_fts` over `(artist, album, title, genre)` — fuzzy search (see §8)
- `live_queue(state, position)` — scheduler hot path

---

## 6. Library Scanner

Triggered manually by the admin. Two phases run concurrently:

**Phase A — Tag extraction (fast, synchronous-ish)**
- `os.scandir`-based recursive walk of `library_path`.
- For each `.mp3`: read tags with Mutagen, compute `file_hash`, upsert into `tracks`. Extract embedded cover art on first encounter, write to `cache/covers/<hash>.jpg`, dedupe by hash.
- Removed-file detection: any DB row whose `path` no longer exists and whose `file_hash` doesn't match any new path is marked deleted.
- Target throughput: ~500 files/sec on SSD. A 100k library = ~3.5 minutes for Phase A.

**Phase B — Audio analysis (slow, parallel)**
- Each newly-added or changed track is enqueued into an `asyncio.Queue` consumed by N worker tasks (N = `min(os.cpu_count(), 4)` by default).
- Each worker shells out:
  ```
  ffmpeg -i <file> -af silencedetect=noise=-30dB:d=2 -f null - 2>&1
  ```
- Parses `silence_start` / `silence_end` lines. Filters to: only quiet passages within first 60 s OR last 120 s, only on tracks longer than 4 minutes, only ≥ minimum duration (admin-configurable, default 2 s).
- Writes `quiet_passages` rows; sets `audio_analyzed_at`.
- Throughput: ffmpeg silencedetect on a 4-min MP3 is ~2–4 s wall-clock. With 4 workers, 100k tracks = ~14–28 hours. **This is fine** — it runs in the background and the library is fully usable during analysis (rows just lack quiet-passage data).

**Idempotency:** the scanner is safe to re-run. `file_hash` mismatch triggers re-analysis; matching hash skips both phases. The admin UI exposes a "Force re-analyze" button that clears `audio_analyzed_at`.

**Progress reporting:** the scanner publishes `(phase, total, done, current_path)` events on a WebSocket channel; the admin UI shows a progress bar and a tail of recent files.

---

## 7. Live Queue & Scheduler

The scheduler is a single asyncio task in FastAPI that owns the `live_queue` table and Liquidsoap's request queue.

### 7.1 Round-robin between user playlists

When multiple `user_session` playlists are loaded:

```
playlists = [P_alice, P_bob, P_carol]
cursor    = [0, 0, 0]   # next item to take from each
loop:
    for i, p in enumerate(playlists):
        if cursor[i] < len(p.items):
            push p.items[cursor[i]] onto live_queue
            cursor[i] += 1
    if all exhausted: break
```

This produces an interleaved sequence `A0, B0, C0, A1, B1, C1, …`. When a user adds a new playlist mid-broadcast, it joins the rotation at the next cycle. When a playlist is exhausted, it drops out silently.

### 7.2 Idle behavior

If `live_queue` is empty AND no user playlists are loaded, the scheduler falls back to `settings.idle_behavior`: pick a random track from the library, or play through `default_auto_playlist_id`, or silence (a Liquidsoap blank source).

### 7.3 Jingle insertion (admin live action)

Admin clicks **Insert jingle now** in the admin UI:
- Backend pushes the jingle path onto Liquidsoap's *interrupt* queue (a separate source wrapped in `smooth_add` over the main queue).
- Liquidsoap ducks the main queue by `jingle_duck_db`, mixes the jingle on top, then restores volume. No track skip; the music continues playing underneath. This satisfies the "ducking/overplaying" requirement (`Q5`).

For jingles embedded in playlists with an `overlay_at_ms`, the same interrupt mechanism is used, but the trigger is a Liquidsoap `on_metadata` callback that fires `overlay_at_ms` ms into the parent track.

### 7.4 Crossfade & gapless

Both are Liquidsoap built-ins:
- `crossfade(duration=settings.crossfade_duration_ms/1000, …)` wrapped around the queue source.
- `gapless` is achieved by feeding Liquidsoap raw sources without re-encoding boundaries; it concatenates samples directly.

Toggling these at runtime: FastAPI sets a Liquidsoap variable via the telnet interface; the `.liq` script reads the variable on each track transition.

---

## 8. Search

FTS5 virtual table on `(artist, album, title, genre)` populated by triggers on `tracks`. Query syntax exposed to the frontend:

- Free text → `tokens NEAR/4 tokens` for prefix-fuzzy match
- Field-scoped: `artist:radiohead album:kid` → maps to FTS5 column filters
- Numeric ranges (year, duration) handled in SQL, not FTS

Year and duration filters are AND-combined with the FTS result. Result pagination is keyset-based on `(artist, album, track_number, id)` to keep scrolling smooth in libraries with 100k+ rows.

---

## 9. API Surface (FastAPI)

REST under `/api/v1`, plus two WebSocket channels.

**Public (no auth):**
- `GET  /tracks?q=&artist=&album=&genre=&year_from=&year_to=&duration_min=&duration_max=&cursor=`
- `GET  /tracks/{id}`
- `GET  /tracks/{id}/cover` — streams cover image from cache
- `GET  /artists`, `GET /albums`, `GET /genres` — facet listings
- `GET  /jingles`
- `GET  /now-playing` — current track, prev 3, next 3
- `POST /queue/playlists` — submit a user playlist (body: items + funny name)
- `WS   /ws/now-playing` — live updates of the same shape as `GET /now-playing`

**Admin (basic auth from `.env`):**
- `POST /admin/scan/library`, `POST /admin/scan/jingles`
- `GET  /admin/scan/status`
- `WS   /ws/admin/scan` — progress
- `GET  /admin/stats` — counts by genre/artist/album, total playtime
- `GET  /admin/settings`, `PUT /admin/settings`
- `POST /admin/auto-playlists`, `GET/PUT/DELETE /admin/auto-playlists/{id}`
- `POST /admin/queue/insert-jingle/{jingle_id}` — duck-overlay now
- `POST /admin/queue/skip`
- `PUT  /admin/queue/reorder` — drag-and-drop reorder of pending items
- `DELETE /admin/queue/{queue_item_id}`

**Audio (served by Icecast, not FastAPI):**
- `GET http://host:8000/raidio.mp3` — the broadcast mount

### 9.1 Auth

Single admin: `ADMIN_EMAIL` and `ADMIN_PASSWORD_HASH` (bcrypt) in `backend/.env`. Login returns a signed JWT (HS256, 7-day expiry). Frontend stores it in `localStorage` under `raidio.admin_jwt`. All `/admin/*` routes require it.

Non-admin users: no auth. The browser generates a funny name on first visit and stores it in `localStorage.raidio.user_label`. The label is sent in a custom header `X-Raidio-User` on relevant POSTs purely for display ("Bob's playlist queued") — no security significance.

---

## 10. Frontend Architecture

Single-page React app. Three top-level routes:

- `/` — **Player** (default for users)
- `/create` — **Playlist creator**
- `/admin` — **Admin console** (gated by JWT)

**State management:** Zustand for global state (now-playing, queue, user label, admin auth). React Query for server data + caching. WebSocket events dispatch directly into Zustand stores.

**Key components:**

- `<NowPlaying />` — full-bleed album art with fade-out gradient, track metadata, prev-3 / next-3 strips, controls, optional Web Audio API visualizer (analyzer node fed from the `<audio>` element).
- `<TrackTable />` — virtualized (react-virtuoso) for 100k rows, draggable rows (dnd-kit). Each row shows a tiny inline waveform-marker for known quiet passages.
- `<PlaylistBuilder />` — two `<TrackTable />` panes side by side, drop targets wired through dnd-kit.
- `<AdminScanPanel />` — progress bar + tail log via WebSocket.

**Theme:** CSS variables for light/dark, toggled by a class on `<html>`. Persisted in `localStorage.raidio.theme`. Full-screen-art toggle is a separate boolean that hides chrome.

**Visualizer:** `AudioContext.createAnalyser()` over the `<audio>` element. 32-band bars or sine-wave mode. Requires the `<audio>` element to have `crossOrigin="anonymous"` and Icecast to send `Access-Control-Allow-Origin: *` (configurable in icecast.xml). If we can't get CORS right, the visualizer gracefully degrades to off.

---

## 11. Configuration

`backend/.env`:
```
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD_HASH=$2b$12$...
JWT_SECRET=<random 32 bytes>

LIBRARY_PATH=/srv/music
JINGLES_PATH=/srv/jingles
COVER_CACHE_PATH=./cache/covers

LIQUIDSOAP_HOST=127.0.0.1
LIQUIDSOAP_TELNET_PORT=1234
ICECAST_HOST=127.0.0.1
ICECAST_PORT=8000
ICECAST_MOUNT=/raidio.mp3
ICECAST_SOURCE_PASSWORD=<random>
```

`liquidsoap/raidio.liq` is checked into the repo and reads its config from environment variables passed by Taskfile.

---

## 12. Testing Strategy

Aligned with the benchmark's three tiers:

- **Unit:** pure functions — scanner path normalization, FTS query builder, round-robin scheduler logic (with a fake Liquidsoap client), funny-name generator. Pytest + pytest-asyncio. Target ≥ 90% line coverage on `backend/raidio/core/`.
- **Functional:** FastAPI route tests with `httpx.AsyncClient` against an in-memory SQLite + a fake Liquidsoap that records commands. Covers all `/api/v1` endpoints and WebSocket flows. Target ≥ 80%.
- **Integration:** Playwright tests that spin up the full stack (FastAPI + a real Liquidsoap configured to write to a file sink instead of Icecast) and exercise: load a playlist → verify queue order → skip → verify next track. The file-sink output is checked for non-silent audio at expected timestamps.

Frontend: Vitest for component logic, Playwright for E2E (shared with integration above).

---

## 13. Risks & Open Questions

1. **Liquidsoap operational complexity.** It's a domain-specific language; debugging requires reading `.liq`. Mitigation: keep our `raidio.liq` short (target < 100 lines) and well-commented; treat it as configuration, not application code.
2. **Icecast latency vs. UI sync.** §4 covers the buffer-offset trick, but it depends on a stable buffer size. If Icecast's actual buffer drifts, the now-playing indicator will be off by 1–2 s. Acceptable for a personal radio.
3. **CORS for visualizer.** Icecast must be configured to send permissive CORS. If the user runs Raidio behind a reverse proxy, the proxy must preserve the headers.
4. **MP3-only assumption.** Locked in for v1 per `Q3`. If FLAC support is added later, the scanner already handles tag reading; we'd need Liquidsoap to decode FLAC (it does, natively) and the `<audio>` element either fed transcoded MP3 (Safari) or native FLAC (Chrome/Firefox).
5. **No auth for users on a LAN.** Acceptable for home use, but anyone on the LAN can submit playlists. Out of scope to add per-user auth.
6. **Funny-name collision.** With ~10k adjectives × ~1k scientists = 10M combinations, collisions are negligible at 1–5 users. No collision detection needed.

---

## 14. Repository Layout

```
raidio/
├── backend/
│   ├── pyproject.toml             # uv-managed
│   ├── .env.example
│   ├── README.md
│   └── raidio/
│       ├── main.py                # FastAPI app factory
│       ├── api/                   # routers
│       ├── core/                  # pure logic (scheduler, FTS, name gen)
│       ├── db/                    # SQLAlchemy models, migrations
│       ├── scanner/               # tag + audio analysis
│       ├── streaming/             # Liquidsoap client
│       └── ws/                    # WebSocket handlers
├── frontend/
│   ├── package.json               # Bun
│   ├── README.md
│   └── src/
│       ├── pages/                 # Player, Create, Admin
│       ├── components/
│       ├── stores/                # Zustand
│       ├── api/                   # React Query hooks
│       └── lib/
├── liquidsoap/
│   └── raidio.liq
├── database/
│   └── raidio.db                  # gitignored
├── docs/
│   └── index.md
├── DESIGN.md                      # this file
├── PRD.md
├── code_quality.md
└── Taskfile.yml
```
