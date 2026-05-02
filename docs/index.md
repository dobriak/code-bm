# Raidio Docs Index

## Getting Started

- [Root README](../README.md) — Quickstart, prerequisites, overview
- [PRD.md](./PRD.md) — Product requirements & user stories
- [DESIGN.md](./DESIGN.md) — System architecture, data model, API surface

## Implementation

- [IMPLEMENT.md](./IMPLEMENT.md) — Phased implementation plan (this document)
- [Playlist Format](./playlist-format.md) — `.raidio` file format specification

## Deployment

- [Deployment Guide](./deployment.md) — Home server setup, systemd units, Docker compose

## Project Structure

```
backend/           FastAPI + SQLAlchemy + Alembic
frontend/          React + TypeScript + Vite
liquidsoap/        Liquidsoap broadcast script
database/          SQLite db (auto-created)
cache/covers/      Embedded album art cache
docs/              This directory
```
