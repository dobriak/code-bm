# Raidio — Agent Instructions

## Project Nature

This is a **benchmark/evaluation codebase** for AI-assisted code generation. The goal is a fully functional "Raidio" personal LAN radio station app, evaluated on code quality, test coverage, and architectural adherence. Quality metrics are recorded in `code_quality.md`.

## Technology Stack (mandated, non-negotiable)

| Layer | Choice |
|---|---|
| Backend | FastAPI + Python 3.12 + `uv` |
| Frontend | React + TypeScript + **Bun** |
| Database | SQLite at `database/raidio.db` via SQLAlchemy |
| Task runner | Taskfile (`task` CLI) |

Additional required runtimes: ffmpeg, Liquidsoap, Icecast 2.

## Key Docs

- `docs/IMPLEMENT.md` — **follow this phased plan in order**. Exit criteria must be met before advancing.
- `docs/DESIGN.md` — system architecture, data model, API surface, frontend structure.
- `docs/PRD.md` — product requirements and user stories.
- `code_quality.md` — benchmarking results (target: ≥90% coverage on `backend/raidio/core/`, ≥80% overall backend).

## Critical Conventions

- **Task runner is `task`** (Taskfile). Commands: `task install`, `task dev`, `task test`, `task lint`, `task db:migrate`.
- Backend uses `uv` exclusively — no `pip`, no `poetry`, no `venv`.
- Frontend uses **Bun** exclusively — not npm/yarn/pnpm.
- **Run `task lint && task test` before every commit.** CI enforces this.
- Tests live with the code they test: `backend/.../test_*.py` or `frontend/.../*.test.tsx`.
- Commit per task (small commits referencing task number, e.g. `feat(scanner): implement Phase A walker — task 2.4`).
- No silent skips — if a task can't be done as written, leave a `<!-- note: -->` and ask.