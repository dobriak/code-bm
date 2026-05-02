# Raidio Frontend

## Component Hierarchy

```
App
├── nav (ThemeToggle)
├── PlayerAudio (AudioSourceContext provider)
│   └── [Visualizer via NowPlaying]
└── routes
    ├── / (PlayerPage / App landing)
    ├── /browse (BrowsePage)
    ├── /create (PlaylistBuilder)
    └── /admin/*
        ├── /admin/login (AdminLoginPage)
        ├── /admin (AdminScanPanel)
        ├── /admin/dashboard (AdminDashboard)
        ├── /admin/settings (AdminSettings)
        └── /admin/queue (AdminQueue)
```

## State Management

| Store | Manager | Key | Purpose |
|-------|---------|-----|---------|
| `useUserStore` | Zustand | `raidio.user_label` | Persistent random username |
| `useAdminAuthStore` | Zustand | `raidio.admin_jwt` | Admin JWT |
| `useAdminScanStore` | Zustand | (memory) | Scan progress WebSocket state |

## API Layer

- `src/api/tracks.ts` — Public: tracks, artists, albums, genres, jingles, random track, resolve-paths, playlist save/load
- `src/api/admin.ts` — Admin mutations (scan, settings, queue, auto-playlists)
- `src/api/adminAuth.ts` — `adminFetch()` wrapper that injects `Authorization: Bearer` header
- React Query handles caching, stale time, retries

## Theme System

`src/lib/theme.ts` exports `setTheme` / `getTheme` / `applyTheme` / `initTheme`. Theme is stored as `light | dark | system` in `localStorage.raidio.theme`. Applied via `data-theme` attribute on `<html>`.

CSS variables are defined in `src/index.css` under `:root` (light) and `[data-theme="dark"]`.

## Routing

React Router v6. Admin routes are wrapped in `<AdminRoute>` which checks `localStorage.raidio.admin_jwt`.

## Key Files

| File | Purpose |
|------|---------|
| `src/components/PlayerAudio.tsx` | Hidden audio element streaming from Icecast |
| `src/components/NowPlaying.tsx` | Full now-playing view with controls, visualizer, fullscreen art |
| `src/components/Visualizer.tsx` | Web Audio API canvas visualizer (bars/wave modes) |
| `src/components/ThemeToggle.tsx` | Theme selector dropdown |
| `src/pages/PlaylistBuilder.tsx` | Playlist creator with drag-drop, save/load |
| `src/pages/BrowsePage.tsx` | Hierarchical browse + search |

## Running

```bash
task install
task dev:frontend   # Vite on :5173
```

## Testing

```bash
bun run test        # Vitest unit tests
bunx playwright test  # E2E (after writing tests)
```
