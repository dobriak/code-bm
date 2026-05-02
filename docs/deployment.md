# Raidio Deployment Guide

## Prerequisites

- Python 3.12+
- Node.js 18+ (or Bun)
- [uv](https://github.com/astral-sh/uv) for Python package management
- [Bun](https://bun.sh) for frontend package management
- ffmpeg
- Liquidsoap >= 2.0
- Icecast 2

## Quick Start

```bash
git clone <repo>
cd raidio
task install
task dev
```

Open `http://localhost:5173` in your browser.

## Production Setup

### Environment Variables

Copy `.env.example` to `.env` and set real values:

```
DATABASE_URL=sqlite+aiosqlite:///database/raidio.db
ADMIN_PASSWORD_HASH=<bcrypt hash>
JWT_SECRET=<random 256-bit secret>
LIQUIDSOAP_HOST=localhost
LIQUIDSOAP_PORT=1234
LIBRARY_PATH=/path/to/music
JINGLES_PATH=/path/to/jingles
ICECAST_SOURCE_PASSWORD=<strong password>
COVER_CACHE_PATH=cache/covers
```

### Systemd Units

#### Raidio Backend

```ini
# /etc/systemd/system/raidio-backend.service
[Unit]
Description=Raidio FastAPI Backend
After=network.target

[Service]
Type=simple
User=raidio
WorkingDirectory=/opt/raidio
ExecStart=/home/raidio/.local/bin/uv run uvicorn raidio.main:app --host 0.0.0.0 --port 8001
Restart=on-failure
RestartSec=5s
EnvironmentFile=/opt/raidio/.env

[Install]
WantedBy=multi-user.target
```

#### Liquidsoap

```ini
# /etc/systemd/system/raidio-liquidsoap.service
[Unit]
Description=Raidio Liquidsoap Broadcaster
After=network.target

[Service]
Type=simple
User=raidio
WorkingDirectory=/opt/raidio
ExecStart=/usr/bin/liquidsoap /opt/raidio/liquidsoap/raidio.liq
Restart=on-failure
RestartSec=5s
EnvironmentFile=/opt/raidio/.env

[Install]
WantedBy=multi-user.target
```

#### Icecast

```ini
# /etc/systemd/system/raidio-icecast.service
[Unit]
Description=Raidio Icecast Streaming Server
After=network.target

[Service]
Type=simple
User=raidio
WorkingDirectory=/opt/raidio
ExecStart=/usr/bin/icecast -c /opt/raidio/liquidsoap/icecast.xml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Start all services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable raidio-backend raidio-liquidsoap raidio-icecast
sudo systemctl start raidio-backend raidio-liquidsoap raidio-icecast
```

### Reverse Proxy (optional)

For HTTPS and external access:

```nginx
# /etc/nginx/sites-available/raidio
server {
    listen 443 ssl;
    server_name radio.example.com;

    ssl_certificate /etc/letsencrypt/live/radio.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/radio.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5173;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Compose (alternative)

```yaml
version: "3.8"
services:
  backend:
    build: ./backend
    ports: ["8001:8001"]
    env_file: .env
    volumes: [./database:/app/database]

  frontend:
    build: ./frontend
    ports: ["5173:5173"]

  liquidsoap:
    image: raidio/liquidsoap
    volumes: [./liquidsoap:/config:ro]
    environment:
      - LIQUIDSOAP_HOST=liquidsoap

  icecast:
    image: raidio/icecast
    ports: ["8000:8000"]
    volumes: [./liquidsoap:/config:ro]
```

## Library Scanning

After setup, scan your library via the admin panel at `/admin`:

1. Log in with admin credentials
2. Click "Scan Library"
3. Wait for completion (progress shown in real-time)
4. Browse at `/browse` or create playlists at `/create`

## Troubleshooting

### Liquidsoap won't start

Check the log: `journalctl -u raidio-liquidsoap -n 50`
Common issues: wrong `LIQUIDSOAP_HOST`, port already in use, missing ffmpeg.

### Icecast 403 on mount point

Verify `ICECAST_SOURCE_PASSWORD` matches `liquidsoap/icecast.xml` source password.

### Database migration failures

```bash
task db:migrate        # apply pending migrations
task db:revision -- "description"  # create new migration
```
