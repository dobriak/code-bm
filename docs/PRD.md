# Raidio — Product Requirements Document

**Status:** Draft v1
**Companion doc:** [`DESIGN.md`](./DESIGN.md) — system design

---

## 1. Vision

Raidio is a self-hosted personal radio station for a home network. It turns a folder of MP3s into a shared listening experience: one stream, multiple listeners, collaborative queueing. It feels less like a music player and more like a tiny FM station that the people in your house program together.

## 2. Goals & Non-goals

**Goals**

- Make a 100k-song MP3 library searchable, browsable, and queueable from any device on the LAN.
- Produce a single, continuous, gapless audio broadcast that all listeners hear in sync.
- Let anyone in the house contribute playlists without creating accounts; resolve contention fairly.
- Give one admin full operational control: scan, settings, live queue, jingle drops.

**Non-goals (v1)**

- Multi-host or cloud deployment.
- Per-user authentication, permissions, or sharing across the internet.
- FLAC, OGG, or other formats beyond MP3.
- Mobile-native apps (the web UI must work on a phone browser, but no native app).
- Auto-tagging, lyric fetching, scrobbling, recommendations.
- Filesystem watching (scans are manual only).
- Auto-insertion of jingles based on quiet-passage detection (admin-driven only).

## 3. Personas

**The Admin (you).** Owns the host, knows where the music lives, occasionally drops jingle bombs into the stream, wants to keep the library tidy and the broadcast running.

**The Housemates (1–4 others).** Open Raidio in a browser, get a fun random name, browse music, build a playlist, send it to the queue, listen along. They don't want to think about accounts or sync.

**The Listener (any of the above).** Sometimes the player is just on in the background and nobody is actively curating. The station should keep playing something reasonable.

## 4. User Stories & Acceptance Criteria

### 4.1 Listening (any user)

- **US-L1.** As a user, I open Raidio and immediately hear what everyone else is hearing.
  - *Accept:* `<audio>` autoplays the Icecast mount (after a one-time click to satisfy browser autoplay policy). Two browsers opened within a minute hear synchronized audio (drift ≤ 200 ms, since Icecast distributes a single stream).

- **US-L2.** As a user, I see the album art of the current song full-bleed, and I see the previous 3 and next 3 entries.
  - *Accept:* Now-playing view shows the current track's art at ≥ 80% viewport height by default. A horizontal strip lists prev-3 and next-3 with artist + title. Updates in ≤ 1 s of an actual track change.

- **US-L3.** As a user, I can toggle a clean "art-only" full-screen mode and switch dark/light themes.
  - *Accept:* Two toggle buttons in the player. Theme persists across reloads.

- **US-L4.** As a user, I see a Web Audio visualizer that I can turn off.
  - *Accept:* Bars or sine-wave mode, fed by an `AnalyserNode`. Toggle persists. If CORS prevents analyzer access, the toggle is hidden (no broken UI).

- **US-L5.** As a user, I see the remaining time of the current song and standard transport controls *for my own playback only* (volume, mute, pause-my-output).
  - *Accept:* Pause/resume affects only the local `<audio>` element, not the broadcast. Tooltip clarifies this. (Skip is admin-only.)

### 4.2 Browsing & Search (any user)

- **US-B1.** I can search the library by free text and see results within 500 ms on a 100k-row library.
  - *Accept:* FTS5-backed search; first 50 results render in ≤ 500 ms p95 on the host.

- **US-B2.** I can filter by genre, artist, album, year range, duration range.
  - *Accept:* Faceted filters combine with free-text search via AND.

- **US-B3.** I can browse the library hierarchically: Genres → Artists → Albums → Songs.
  - *Accept:* Each level is a paginated list; album view shows track listing with track numbers.

- **US-B4.** When I see a track in any list, I can tell at a glance whether it has known quiet passages.
  - *Accept:* A small marker on the track row indicates intro/outro quiet regions; hover shows their start/end. Tracks not yet analyzed show a neutral "pending" marker.

### 4.3 Playlist creation (any user)

- **US-P1.** I open the Playlist Creator and see two scrollable lists side-by-side: available songs and my playlist-in-progress.
  - *Accept:* Both lists virtualize. Search box on top of the available pane.

- **US-P2.** I drag songs from the left list to the right to add them, and reorder by dragging within the right list.
  - *Accept:* dnd-kit drag handles; visual drop indicator; works on touch screens.

- **US-P3.** I name my playlist and add freeform notes.
  - *Accept:* Two text inputs at the top of the right pane: name (required, ≤ 80 chars) and notes (optional, ≤ 500 chars).

- **US-P4.** I can hit "Feeling lucky" to add a single random song from the library.
  - *Accept:* Button adds one track sampled uniformly at random from the full library (not the filtered view).

- **US-P5.** I can insert a jingle at any position in my playlist, or pin it to overlay a quiet passage of an adjacent track.
  - *Accept:* Jingles appear in a third tab/section; dragging a jingle between two tracks inserts it as its own item; dragging onto a track's quiet-passage marker creates an overlay (jingle plays *over* that passage).

- **US-P6.** I can save my playlist to a text file and load it back later.
  - *Accept:* Save = downloads a file (custom Raidio JSON-in-`.raidio` format that includes track paths, jingle insertions, and notes). Load = file picker that restores the playlist into the editor.

- **US-P7.** I can send my playlist to the live queue.
  - *Accept:* "Send to queue" button POSTs the playlist with my funny name attached. Confirmation toast: "Queued as $LABEL — playing in ~$ESTIMATE".

### 4.4 Identity (any user)

- **US-I1.** On my first visit, I'm assigned a funny name in `adjective_scientist` style.
  - *Accept:* Name generated client-side from a curated word list, persisted in `localStorage.raidio.user_label`. Visible in the header.

- **US-I2.** I can re-roll my name if I don't like it.
  - *Accept:* Click name → "New name" button → new label generated and saved.

### 4.5 Broadcast scheduling (system behavior)

- **US-S1.** When I'm the only one with a queued playlist, my playlist plays end-to-end.
  - *Accept:* Items appear in the live queue in the order I sent them.

- **US-S2.** When multiple users have queued playlists, they interleave fairly.
  - *Accept:* Round-robin: with users A, B, C each having an N-song playlist, the broadcast plays `A1, B1, C1, A2, B2, C2, …`. Late joiners enter on the next cycle.

- **US-S3.** When no playlists are loaded, the system falls back to admin-configured idle behavior.
  - *Accept:* Admin can choose `auto-playlist`, `random`, or `silence`.

- **US-S4.** Tracks transition gaplessly; crossfade can be enabled with a configurable duration.
  - *Accept:* With gapless on and crossfade off, no audible gap between tracks. With crossfade on, end of track N overlaps start of track N+1 by the configured duration (default 4 s).

### 4.6 Admin (admin only)

- **US-A1.** I log in with email + password from `.env` and land on a control center.
  - *Accept:* Login form on `/admin`; failed login shows a generic error (no user enumeration); JWT lasts 7 days.

- **US-A2.** I see an at-a-glance dashboard: total tracks, artists, albums, genres, total playtime, broadcast status, current queue length.
  - *Accept:* All counts computed from SQL aggregates; loads in ≤ 1 s.

- **US-A3.** I trigger a library scan or a jingles scan and watch progress live.
  - *Accept:* Buttons fire off async scan. Progress bar + tail of recent file paths via WebSocket. Errors collected and shown at the end.

- **US-A4.** I configure operational settings: library path, jingles path, idle behavior, default auto-playlist, crossfade on/off + duration, gapless on/off, jingle ducking depth, minimum quiet-passage duration.
  - *Accept:* Settings page with sane validation; changes take effect immediately (no restart).

- **US-A5.** I CRUD auto-playlists.
  - *Accept:* Same builder UI as users, plus admin-only fields (mark as default).

- **US-A6.** I view and manipulate the live queue: reorder pending items, remove items, skip the current track.
  - *Accept:* Drag to reorder; delete button per row; "Skip" button is one click with a 2-second undo toast.

- **US-A7.** I drop a jingle onto the live broadcast on demand.
  - *Accept:* Jingle list with a "Play now" button per jingle. Jingle audio mixes over the current track at the configured duck depth; track continues playing underneath. No skip.

- **US-A8.** I can see why a track has no quiet-passage data.
  - *Accept:* Track detail shows `analysis_status` and `analysis_error` if any. "Re-analyze" button enqueues it.

## 5. UX Principles

- **Streaming is shared, control is personal.** What plays out of the speakers is collective. What you see on your screen and your local volume are yours.
- **Minimal chrome.** The player should look beautiful with the chrome hidden. Album art is the hero.
- **No modals for routine actions.** Toasts and inline confirmations only.
- **Touch-first for the player, keyboard-first for the playlist builder.** The phone is a remote; the laptop is a workstation.
- **Readable at a glance.** Every list shows artist–album–title in a consistent, readable hierarchy.

## 6. Quality Bars

- **Search latency:** p95 ≤ 500 ms on a 100k library.
- **Now-playing update latency:** ≤ 1 s after server detects track change (within Icecast buffer alignment).
- **Scan throughput:** Phase A ≥ 500 files/sec on SSD; Phase B parallelism configurable.
- **Listener sync:** ≤ 200 ms drift between any two listeners (Icecast property; we don't add to it).
- **Test coverage:** ≥ 90% on backend `core/`, ≥ 80% overall backend, integration tests cover all happy paths in §4.

## 7. Out of Scope (deferred to vNext)

- Audio analysis features beyond silence detection (key, BPM, danceability, chromatic mixing) — the schema accommodates them; the workers don't compute them yet.
- Smart auto-playlists ("more like this", mood-based).
- FLAC and other format support.
- Internet-facing deployment, HTTPS, multi-user auth.
- Listener-side voting / reactions.
- Recording the broadcast to disk.

## 8. Release Plan

**Milestone 1 — Skeleton (week 1):** repo scaffold, Taskfile, FastAPI hello-world, React shell, Liquidsoap + Icecast playing a hardcoded file end-to-end.

**Milestone 2 — Library (week 2):** scanner Phase A, search, browse, track tables. No streaming integration yet.

**Milestone 3 — Broadcast (week 3):** scheduler, round-robin, user-playlist submission, live queue UI, gapless, crossfade.

**Milestone 4 — Admin & jingles (week 4):** admin auth, settings, jingle scan, jingle live drop, ducking, quiet-passage analysis (Phase B).

**Milestone 5 — Polish (week 5):** themes, full-screen art, visualizer, Feeling Lucky, playlist save/load, integration tests, `code_quality.md` populated.

## 9. Open Questions for the Admin (you)

- Should the funny-name generator's word list be checked into the repo, or fetched on demand? (Recommend: checked in, ~10k × ~1k = ~120 KB gzipped.)
- For the `.raidio` playlist file format: prefer a JSON file, or a more human-readable INI/YAML? (Recommend: JSON for round-trip fidelity.)
- Default crossfade duration: 0 s (off), 2 s, 4 s? (Recommend: 0 s by default — gapless is the surprise-free choice; users can opt in.)
- Should admin settings be editable from the UI only, or also reloadable from `.env` on SIGHUP? (Recommend: UI is the source of truth; `.env` is bootstrap only.)
