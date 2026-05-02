# Raidio Frontend

React + TypeScript single-page application for the Raidio personal radio station.

## Development

```bash
cd frontend
bun install          # Install dependencies
bun run dev          # Start Vite dev server on :5173
bun test             # Run vitest
bun run build        # Production build → dist/
```

## Routes

| Route | Purpose | Auth |
|-------|---------|------|
| `/` | Player — full-bleed album art, now-playing, visualizer | None |
| `/create` | Playlist creator — two-pane drag-and-drop builder | None |
| `/admin/login` | Admin login form | None |
| `/admin` | Dashboard, scan, settings, queue, auto-playlists | JWT |

## Component Hierarchy

```
App.tsx
├── PlayerPage (/)
│   └── NowPlaying
│       ├── Visualizer (Web Audio API — bars/wave/off)
│       ├── PlayerAudio (hidden <audio> connected to Icecast)
│       └── TrackChip (prev/next strips)
├── CreatePage (/create)
│   └── PlaylistBuilder
│       ├── FilterSidebar (genre/artist/album/year facets)
│       ├── TrackTable (react-virtuoso virtualized list)
│       └── SortablePlaylistItem (dnd-kit drag handles)
├── AdminLoginPage (/admin/login)
│   └── Login form
└── AdminPage (/admin)
    ├── AdminDashboard (stats)
    ├── AdminScanPanel (scan triggers + progress WS)
    ├── AdminSettings (settings form)
    ├── AdminQueue (drag-to-reorder queue)
    └── AdminAutoPlaylists (CRUD)
```

## State Management

- **Zustand** — Global client state (user identity, admin auth, now-playing)
- **React Query** — Server data fetching, caching, and background refresh
- **WebSocket** — Real-time now-playing and scan progress updates dispatch into Zustand stores

### Stores

| Store | File | Purpose |
|-------|------|---------|
| `useUserStore` | `stores/userStore.ts` | Funny name identity, persisted in localStorage |
| `useNowPlayingStore` | `stores/nowPlayingStore.ts` | Current/prev/next track state from WS |
| `useAdminAuthStore` | `stores/adminAuthStore.ts` | JWT token, persisted in localStorage |

## Key Libraries

| Library | Purpose |
|---------|---------|
| `react-virtuoso` | Virtualized lists (100k+ rows) |
| `@dnd-kit/core` + `sortable` | Drag-and-drop for playlist reordering |
| `@tanstack/react-query` | Server state management |
| `zustand` | Client-side global state |
| `react-router-dom` | SPA routing |

## Theme System

Dark/light themes toggle via `data-theme` attribute on `<html>`. CSS variables for both themes. User preference persisted in `localStorage.raidio.theme`.

Full-screen art mode hides chrome and expands album art to 90vw × 90vh, persisted in `localStorage.raidio.fullscreen_art`.

## Visualizer

`Visualizer.tsx` uses the Web Audio API (`AudioContext` + `AnalyserNode`) connected to the Icecast `<audio>` element. Two modes:
- **Bars** — 32-band frequency bars on a canvas
- **Wave** — Time-domain waveform on a canvas

Mode is cycled via a toggle button and persisted in `localStorage.raidio.visualizer_mode`. On CORS failure, the visualizer gracefully hides itself.

## Keyboard Shortcuts (Playlist Creator)

| Key | Action |
|-----|--------|
| `/` | Focus search input |
| `r` | Feeling Lucky — add random track |
| `Enter` | (planned) Add top search result |

## Extension Guide

1. **New page:** Create component in `pages/`, add `<Route>` in `App.tsx`.
2. **New API hook:** Add fetch function in `api/client.ts`, wrap with `useQuery`/`useMutation` in `api/hooks.ts`.
3. **New store:** Create in `stores/` with `create()` from Zustand, add persist middleware if needed.
4. **New component:** Add in `components/`, follow inline style convention.
