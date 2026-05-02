# Raidio — Deployment Guide

How to run Raidio on a home server (or development machine) for LAN use.

## Prerequisites

- Python 3.12+
- [Bun](https://bun.sh/) runtime
- [uv](https://docs.astral.sh/uv/) package manager
- [Taskfile](https://taskfile.dev/) task runner
- [Liquidsoap](https://www.liquidsoap.info/) audio engine
- [Icecast 2](https://icecast.org/) HTTP broadcast server
- [ffmpeg](https://ffmpeg.org/) for silence detection

### Installing runtime dependencies (Ubuntu/Debian)

```bash
sudo apt-get install icecast2 liquidsoap-mode-visual liquidsoap ffmpeg
```

### Installing runtime dependencies (macOS)

```bash
brew install icecast liquidsoap ffmpeg
```

## Development Mode

```bash
# Clone and enter the repo
cd raidio

# Install all dependencies
task install

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your admin credentials and library paths

# Start all services (backend, frontend, liquidsoap, icecast)
task dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8001
- API docs: http://localhost:8001/docs
- Audio stream: http://localhost:8000/raidio.mp3

## Production Deployment

### Option A: systemd services

Create systemd unit files for each service:

**`/etc/systemd/system/raidio-backend.service`**
```ini
[Unit]
Description=Raidio FastAPI Backend
After=network.target

[Service]
Type=simple
User=raidio
WorkingDirectory=/opt/raidio/backend
ExecStart=/opt/raidio/backend/.venv/bin/uvicorn raidio.main:app --host 0.0.0.0 --port 8001
Restart=on-failure
RestartSec=5
Environment=LIBRARY_PATH=/srv/music
Environment=JINGLES_PATH=/srv/jingles

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/raidio-frontend.service`**
```ini
[Unit]
Description=Raidio Frontend (static build)
After=network.target

[Service]
Type=simple
User=raidio
WorkingDirectory=/opt/raidio/frontend
ExecStart=/usr/bin/python3 -m http.server 8080 --directory dist
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/raidio-liquidsoap.service`**
```ini
[Unit]
Description=Raidio Liquidsoap Audio Engine
After=network.target sound.target

[Service]
Type=simple
User=raidio
ExecStart=/usr/bin/liquidsoap /opt/raidio/liquidsoap/raidio.liq
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/raidio-icecast.service`**
```ini
[Unit]
Description=Raidio Icecast Broadcast Server
After=network.target

[Service]
Type=simple
User=raidio
ExecStart=/usr/bin/icecast2 -c /opt/raidio/liquidsoap/icecast.xml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable raidio-{backend,frontend,liquidsoap,icecast}
sudo systemctl start raidio-{backend,frontend,liquidsoap,icecast}
```

### Option B: Docker Compose

```yaml
version: "3.8"
services:
  backend:
    build: ./backend
    ports:
      - "8001:8001"
    volumes:
      - ./database:/app/database
      - /srv/music:/music:ro
      - /srv/jingles:/jingles:ro
    env_file: ./backend/.env

  frontend:
    build: ./frontend
    ports:
      - "5173:80"

  liquidsoap:
    image: savonet/liquidsoap:latest
    volumes:
      - ./liquidsoap:/etc/liquidsoap
      - /srv/music:/music:ro
      - /srv/jingles:/jingles:ro
    command: liquidsoap /etc/liquidsoap/raidio.liq

  icecast:
    image: infiniteproject/icecast:latest
    ports:
      - "8000:8000"
    environment:
      - ICECAST_SOURCE_PASSWORD=yourpassword
      - ICECAST_ADMIN_PASSWORD=youradminpw
      - ICECAST_HOSTNAME=localhost
```

## Building the Frontend for Production

```bash
cd frontend
bun run build
# Output in frontend/dist/ — serve with any static file server
```

## Network Configuration

Raidio is designed for LAN-only use. To make it accessible to other devices on your network:

1. Bind the backend to `0.0.0.0` instead of `127.0.0.1`
2. Ensure the Icecast stream URL in the frontend points to the host machine's LAN IP
3. Open ports 5173 (frontend), 8001 (API), and 8000 (audio stream) if a firewall is active

## Configuration

All runtime settings are configured through the admin UI at `/admin → Settings`. The `.env` file is used only for initial bootstrap; the database settings table is the source of truth.

Key settings:
- **Library path** — where your MP3 files live
- **Jingles path** — where jingle files live
- **Idle behavior** — what plays when nothing is queued (random / auto-playlist / silence)
- **Crossfade** — duration of overlap between tracks (0 = off / gapless)
- **Jingle duck depth** — how much to lower music during jingle overlay (−24 to 0 dB)
- **Icecast buffer offset** — aligns now-playing UI with actual audio (default 3000 ms)
