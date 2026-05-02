# Raidio

Personal LAN radio station with round-robin playlist scheduling.

## Documentation

- [DESIGN.md](./docs/DESIGN.md) — System architecture and data model
- [PRD.md](./docs/PRD.md) — Product requirements and user stories
- [IMPLEMENT.md](./docs/IMPLEMENT.md) — Phased implementation plan
- [code_quality.md](./code_quality.md) — Quality benchmarks and results

## Quick Start

```bash
task install
task dev
```

Visit `http://localhost:5173` in your browser.

## Requirements

- Python 3.12+ with `uv`
- Bun
- ffmpeg
- Liquidsoap
- Icecast 2

## Installation

### Icecast 2

**Ubuntu/Debian:**
```bash
sudo apt-get install icecast2
```

**macOS (Homebrew):**
```bash
brew install icecast
```

**Docker:**
```bash
docker run -p 8000:8000 -v $(pwd)/liquidsoap:/etc/icecast2 icecast/icecast
```

### Liquidsoap

**Ubuntu/Debian:**
```bash
sudo apt-get install liquidsoap
```

**macOS (Homebrew):**
```bash
brew install liquidsoap
```

**From source:**
See [https://www.liquidsoap.info/doc-dev/install.html](https://www.liquidsoap.info/doc-dev/install.html)

### Running the application

1. Create `backend/.env` from `.env.example` and update passwords
2. Run `task install` to install dependencies
3. Run `task dev` to start all services (backend, frontend, liquidsoap, icecast)
4. Open `http://localhost:5173` in your browser

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌────────────────────┐
│  React SPA   │◄──►│   FastAPI    │◄──►│   SQLite           │
│  (Bun build) │HTTP│   backend    │ORM │   raidio.db        │
│              │ WS │              │    │                    │
└──────┬───────┘    └──────┬───────┘    └────────────────────┘
       │                   │
       │ HTTP audio        │ Telnet
       │ (Icecast mount)   │
       │                   ▼
       │            ┌──────────────┐    ┌────────────────────┐
       └───────────►│   Icecast 2  │◄───│   Liquidsoap       │
                    │   (mount)    │ src│   (audio engine)   │
                    └──────────────┘    └─────────┬──────────┘
                                                  │ reads
                                                  ▼
                                          ┌────────────────────┐
                                          │  Music library +   │
                                          │  jingles directory  │
                                          └────────────────────┘
```