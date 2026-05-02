# Raidio — Documentation Index

Welcome to the Raidio documentation hub. This is the central reference for understanding, building, and deploying the project.

## Core Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | Full system design — architecture, data model, API surface, technology decisions |
| [PRD.md](./PRD.md) | Product requirements — user stories, acceptance criteria, quality bars |
| [IMPLEMENT.md](./IMPLEMENT.md) | Phased implementation plan with task-level checklists |
| [playlist-format.md](./playlist-format.md) | `.raidio` playlist file format specification |
| [deployment.md](./deployment.md) | Running on a home server — systemd, Docker, configuration |

## Component Documentation

| Document | Description |
|----------|-------------|
| [../backend/README.md](../backend/README.md) | Backend API reference, env vars, project structure, extension guide |
| [../frontend/README.md](../frontend/README.md) | Frontend component hierarchy, state management, development guide |
| [../code_quality.md](../code_quality.md) | Coverage reports, benchmark results, lint status |

## Quick Start

```bash
# Install all dependencies
task install

# Start all services
task dev
```

See the [root README](../README.md) for full prerequisites and setup instructions.

## Architecture Overview

```
React SPA ←(HTTP/WS)→ FastAPI ←(ORM)→ SQLite
    │                      │
    │ HTTP audio           │ Telnet control
    └──→ Icecast 2 ←──── Liquidsoap ←── Music library + jingles
         (:8000/raidio.mp3)
```

Three processes run on the host: **FastAPI** (API + scheduler), **Liquidsoap** (audio engine), **Icecast** (HTTP broadcast).

## Key Concepts

- **Single playhead:** One audio stream, many synchronized listeners on the LAN
- **Round-robin scheduling:** User playlists interleave fairly (A1, B1, C1, A2, B2, C2, …)
- **Two-phase scanner:** Fast tag extraction (Phase A) then slow audio analysis (Phase B)
- **Now-playing alignment:** Icecast buffer offset delays UI updates to match what listeners hear
