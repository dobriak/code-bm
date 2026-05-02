# Raidio

Welcome to **Raidio**. This repository implements the code for a home LAN level radio-like application that allows for users and administrator to create and queue music playlists with occasional jingle insertion.
All design context can be found in [DESIGN.md](docs/DESIGN.md) and [PRD.md](docs/PRD.md). The state of the current application implementation is kept in [IMPLEMENT.md](docs/IMPLEMENT.md).

### Companion docs
- [`docs/DESIGN.md`](docs/DESIGN.md) — full system design (architecture, data model, API surface, streaming decision)
- [`docs/PRD.md`](docs/PRD.md) — product requirements, user stories, acceptance criteria
- [`docs/IMPLEMENT.md`](docs/IMPLEMENT.md) — phased implementation plan with checklists and exit criteria
- [`code_quality.md`](code_quality.md) — benchmarking results and coverage metrics


## Project Overview

The goal of this project is to generate a fully functional application ("Raidio") from a set of defined prompts. The resulting codebase is strictly evaluated on code quality, test coverage, and architectural adherence.

All quality metrics and benchmarking results are recorded in [`code_quality.md`](code_quality.md).

## Architecture & Technology Stack

The Raidio application follows a modern, layered architecture. The following technology choices are mandatory and non-negotiable for the benchmarking process.

### Backend
*   **Location:** `backend/`
*   **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
*   **Runtime:** Python 3.12
*   **Package Manager:** [uv](https://github.com/astral-sh/uv)
*   **ORM:** [SQLAlchemy](https://docs.sqlalchemy.org/)
*   **Documentation:** [`backend/README.md`](backend/README.md)

### Frontend
*   **Location:** `frontend/`
*   **Framework:** [ReactJS](https://react.dev/) with [TypeScript](https://www.typescriptlang.org/)
*   **Runtime/Package Manager:** [Bun](https://bun.sh/)
*   **Documentation:** [`frontend/README.md`](frontend/README.md)

### Database
*   **Location:** `database/raidio.db`
*   **Engine:** [SQLite](https://www.sqlite.org/)
*   **Interaction:** Accessed exclusively via SQLAlchemy in the backend.

## Getting Started

This project utilizes [Taskfile](https://taskfile.dev/docs/guide) for task automation and management. Ensure you have the `task` binary installed on your system.

### Prerequisites
*   [Taskfile](https://taskfile.dev/installation/)
*   [uv](https://docs.astral.sh/uv/getting-started/installation/)
*   [Bun](https://bun.sh/docs/installation/)
*   [Icecast 2](https://icecast.org/) — HTTP audio broadcast server
*   [Liquidsoap](https://www.liquidsoap.info/) — server-side audio engine
*   [ffmpeg](https://ffmpeg.org/) — audio transcoding (also for silencedetect in Phase 4)

#### Installing runtime dependencies (Ubuntu/Debian)
```bash
sudo apt-get install icecast2 liquidsoap ffmpeg
```

#### Installing runtime dependencies (macOS)
```bash
brew install icecast liquidsoap ffmpeg
```

### Installation & Running

1.  **Install Dependencies:**
    ```bash
    task install
    ```

2.  **Run the Application:**
    This command typically starts both the backend API and the frontend development server.
    ```bash
    task dev
    ```

For detailed command references, run `task --list` or refer to the specific component READMEs linked above.

## Testing Strategy

Quality is a core metric for this benchmark. The codebase enforces a rigorous testing policy.

*   **Unit Tests:** Testing individual components/functions in isolation.
*   **Functional Tests:** Testing the interaction between specific modules (e.g., API endpoints).
*   **Integration Tests:** Testing the full stack flow (Frontend <-> Backend <-> Database).

Test coverage reports and quality metrics are generated during the CI/CD process or manually via task commands, and are persisted in [`code_quality.md`](code_quality.md).

## Documentation

The project maintains living documentation to ensure maintainability and knowledge transfer.

*   **Main Index:** [`docs/index.md`](docs/index.md) - The central hub for all project documentation (Wiki style).
*   **Backend Status:** [`backend/README.md`](backend/README.md) - Technical status, API specs, and extension guide for the backend.
*   **Frontend Status:** [`frontend/README.md`](frontend/README.md) - Technical status, component hierarchy, and extension guide for the frontend.

## Development Guidelines & Tools

### MCP & Tooling Usage
When extending this project or executing prompts, the usage of **MCP (Model Context Protocol)** and associated tools is highly encouraged. Specifically:

*   **Documentation Lookup:** Tools should be used to fetch the latest documentation for FastAPI, SQLAlchemy, React, and Bun to ensure the generated code utilizes the most current API standards and best practices.
*   **Code Generation:** Prompts used to build the Raidio application should leverage available tooling to validate code correctness against the defined technology stack.

### File Structure

```text
.
├── backend/              # FastAPI Python application
│   └── README.md
├── database/             # SQLite storage
│   └── raidio.db
├── docs/                 # Living documentation
│   └── index.md
├── frontend/             # React/Typescript application
│   └── README.md
├── code_quality.md       # Benchmarking results and coverage
├── README.md             # You are here
└── Taskfile.yml          # Task runner configuration
