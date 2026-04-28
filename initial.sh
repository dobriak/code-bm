#!/bin/bash
set -euo pipefail

PYTHON_VERSION="3.12"

log()   { printf "\033[0;34m[INFO]\033[0m %s\n" "$*"; }
ok()    { printf "\033[0;32m[OK]\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()   { printf "\033[0;31m[ERROR]\033[0m %s\n" "$*" >&2; }
step()  { printf "\n\033[0;34m==>\033[0m \033[1m%s\033[0m\n" "$*"; }

install_uv() {
    warn "uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
}

install_bun() {
    warn "bun not found, installing..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
}

install_task() {
    warn "task not found, installing..."
    sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
    export PATH="$HOME/.local/bin:$PATH"
}

check_prerequisites() {
    step "Checking prerequisites..."

    if ! command -v uv &> /dev/null; then
        install_uv
    fi
    ok "uv $(uv --version 2>/dev/null || echo 'installed')"

    if ! command -v bun &> /dev/null; then
        install_bun
    fi
    ok "bun $(bun --version 2>/dev/null || echo 'installed')"

    if ! command -v task &> /dev/null; then
        install_task
    fi
    ok "task $(task --version 2>/dev/null || echo 'installed')"
    if ! command -v jq &> /dev/null; then
        err "Please install jq"
        exit 1
    fi
}

setup_backend() {
    step "Setting up Backend (FastAPI + SQLAlchemy + SQLite)"

    log "Initializing Python project with uv..."
    mkdir -p backend
    (cd backend && uv init --app --name raidio-backend --python "$PYTHON_VERSION")

    log "Removing default scaffold files..."
    rm -f backend/main.py backend/hello.py

    log "Adding dependencies..."
    (cd backend && uv add "fastapi[standard]" sqlalchemy)

    log "Creating app package structure..."
    mkdir -p backend/app/{models,schemas,routers}
    touch backend/app/__init__.py
    touch backend/app/models/__init__.py
    touch backend/app/schemas/__init__.py
    touch backend/app/routers/__init__.py

    log "Creating database configuration..."
    cat > backend/app/database.py << 'PYEOF'
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

DATABASE_URL = "sqlite:///../database/raidio.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
PYEOF

    log "Creating User model..."
    cat > backend/app/models/user.py << 'PYEOF'
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
PYEOF

    log "Creating User schemas..."
    cat > backend/app/schemas/user.py << 'PYEOF'
from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None

    class Config:
        from_attributes = True
PYEOF

    log "Creating users router..."
    cat > backend/app/routers/users.py << 'PYEOF'
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: DbSession):
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/", response_model=List[UserResponse])
def list_users(db: DbSession):
    return db.query(User).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: DbSession):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: DbSession):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"ok": True}
PYEOF

    log "Creating main application..."
    cat > backend/app/main.py << 'PYEOF'
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
from app.routers import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Raidio API", version="1.0.0", lifespan=lifespan)

app.include_router(users.router)


@app.get("/")
def root():
    return {"message": "Welcome to Raidio API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
PYEOF

    log "Creating database initialization script..."
    cat > backend/init_db.py << 'PYEOF'
from app.database import engine, Base
from app.models.user import User  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database initialized at ../database/raidio.db")
PYEOF

    log "Creating backend .gitignore..."
    cat > backend/.gitignore << 'PYEOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
*.manifest
*.spec
pip-log.txt
pip-delete-this-directory.txt
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/
pytestdebug.log
*.mo
*.pot
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
instance/
.webassets-cache
.scrapy
docs/_build/
.pybuilder/
target/
.ipynb_checkpoints
profile_default/
ipython_config.py
.python-version
Pipfile.lock
poetry.lock
.pdm.toml
.pdm-python
.pdm-build/
__pypackages__/
celerybeat-schedule
celerybeat.pid
*.sage.py
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/
.spyderproject
.spyproject
.ropeproject
/site
.mypy_cache/
.dmypy.json
dmypy.json
.pyre/
.pytype/
cython_debug/
.ruff_cache/
*.db
*.sqlite
*.sqlite3
uv.lock
PYEOF

    log "Creating backend README.md..."
    cat > backend/README.md << 'PYEOF'
# Raidio Backend

FastAPI application serving the Raidio API.

## Technology Stack

- **Framework:** FastAPI
- **Runtime:** Python 3.12
- **Package Manager:** uv
- **ORM:** SQLAlchemy
- **Database:** SQLite

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, lifespan, router includes
│   ├── database.py      # Engine, SessionLocal, Base, get_db dependency
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py      # User SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py      # User Pydantic schemas
│   └── routers/
│       ├── __init__.py
│       └── users.py      # User CRUD endpoints
├── init_db.py            # Database initialization script
├── pyproject.toml
└── README.md
```

## Getting Started

```bash
task backend:install
task backend:dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/health` | Health check |
| POST | `/users/` | Create a user |
| GET | `/users/` | List all users |
| GET | `/users/{user_id}` | Get user by ID |
| DELETE | `/users/{user_id}` | Delete user by ID |

## Extending

1. Create a new model in `app/models/`
2. Create matching schemas in `app/schemas/`
3. Create a new router in `app/routers/`
4. Register the router in `app/main.py` with `app.include_router()`
5. Import the model in `init_db.py` so its tables are created
PYEOF

    ok "Backend setup complete"
}

setup_frontend() {
    step "Setting up Frontend (React + TypeScript + TailwindCSS + ShadCN)"

    log "Creating React project with Bun..."
    bun init --react=tailwind frontend

    log "Installing Vite and TailwindCSS..."
    (cd frontend && bun add -d vite @vitejs/plugin-react)
    (cd frontend && bun add tailwindcss @tailwindcss/vite)

    log "Configuring Vite..."
    cat > frontend/vite.config.ts << 'TSEOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
TSEOF

    log "Creating Vite entry HTML..."
    cat > frontend/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Raidio</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/frontend.tsx"></script>
  </body>
</html>
HTMLEOF

    log "Configuring TailwindCSS..."
    cat > frontend/src/index.css << 'CSSEOF'
@import "tailwindcss";
CSSEOF

    log "Updating TypeScript configuration..."
    cat > frontend/tsconfig.json << 'JSONEOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
JSONEOF
    if cat $HOME/.npmrc | grep '^ignore-scripts=true'; then
      log "Manual bun initialization because of ignore-scripts"
      (cd frontend/node_modules/bun && node install.js)
    fi
    log "Initializing ShadCN UI..."
    (cd frontend && bunx shadcn@latest init -d -y)

    log "Updating package.json scripts for Vite..."
    contents=$(jq '.scripts.dev = "vite"' frontend/package.json) && echo -E "${contents}" > frontend/package.json
    contents=$(jq '.scripts.build = "vite build --base=/"' frontend/package.json) && echo -E "${contents}" > frontend/package.json

    log "Updating App component..."
    cat > frontend/src/App.tsx << 'TSEOF'
import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Raidio
        </h1>
        <p className="text-gray-600 mb-4">
          Welcome to your React + TypeScript + TailwindCSS + ShadCN app
        </p>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setCount(count + 1)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Count is {count}
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
TSEOF

    log "Fixing frontend entry point import..."
    if [ -f frontend/src/frontend.tsx ]; then
        sed -i.bak 's/import { App } from/import App from/' frontend/src/frontend.tsx && rm frontend/src/frontend.tsx.bak
    fi

    log "Creating frontend README.md..."
    cat > frontend/README.md << 'PYEOF'
# Raidio Frontend

React/TypeScript application for the Raidio UI.

## Technology Stack

- **Framework:** React with TypeScript
- **Runtime/Package Manager:** Bun
- **Bundler/Dev Server:** Vite
- **Styling:** TailwindCSS 4
- **UI Components:** ShadCN UI

## Getting Started

```bash
task frontend:install
task frontend:dev
```

## Extending

1. Add new components in `src/components/` (ShadCN manages this via `bunx shadcn@latest add <component>`)
2. Add pages/routes in `src/pages/`
3. Update `src/App.tsx` to include new routes
PYEOF

    ok "Frontend setup complete"
}

setup_database() {
    step "Initializing Database (SQLite)"

    mkdir -p database
    (cd backend && uv run python init_db.py)

    ok "Database initialized at database/raidio.db"
}

setup_taskfile() {
    step "Creating Taskfile.yml"

    cat > Taskfile.yml << 'YAMLEOF'
version: '3'

env:
  BACKEND_PORT: 8000
  FRONTEND_PORT: 3000

tasks:
  default:
    desc: List all available tasks
    cmds:
      - task --list
    silent: true

  backend:install:
    desc: Install backend dependencies using uv
    dir: backend
    cmds:
      - uv sync

  backend:run:
    desc: Run the FastAPI backend server
    dir: backend
    cmds:
      - uv run uvicorn app.main:app --host 0.0.0.0 --port {{.BACKEND_PORT}}

  backend:dev:
    desc: Run the FastAPI backend in development mode with auto-reload
    dir: backend
    cmds:
      - uv run uvicorn app.main:app --reload --host 0.0.0.0 --port {{.BACKEND_PORT}}

  frontend:install:
    desc: Install frontend dependencies using bun
    dir: frontend
    cmds:
      - bun install

  frontend:run:
    desc: Run the React frontend development server
    dir: frontend
    cmds:
      - bun dev

  frontend:dev:
    desc: Run the React frontend development server (alias for frontend:run)
    dir: frontend
    cmds:
      - bun dev

  frontend:build:
    desc: Build the frontend for production
    dir: frontend
    cmds:
      - bun run build

  frontend:start:
    desc: Run the frontend production server
    dir: frontend
    cmds:
      - bun start

  install:
    desc: Install all dependencies (backend + frontend)
    deps:
      - backend:install
      - frontend:install

  dev:
    desc: Run both backend and frontend in development mode
    deps:
      - backend:dev
      - frontend:dev

  run:
    desc: Run both backend and frontend servers
    deps:
      - backend:run
      - frontend:run
YAMLEOF

    ok "Taskfile.yml created"
}

setup_root() {
    step "Setting up root project files"

    if [ ! -f .gitignore ]; then
        log "Creating root .gitignore..."
        cat > .gitignore << 'EOF'
database/

.DS_Store
Thumbs.db

.vscode/
.idea/
*.swp
*.swo
*~

.env
.env.local
.env.*.local
EOF
    fi

    if [ ! -f code_quality.md ]; then
        log "Creating code_quality.md..."
        cat > code_quality.md << 'EOF'
# Code Quality Metrics

_This file is auto-generated during CI/CD or manual test runs._

## Summary

| Metric | Value |
|--------|-------|
| Backend Coverage | — |
| Frontend Coverage | — |
| Lint Status | — |
| Type Check Status | — |

## Backend

_No data yet._

## Frontend

_No data yet._
EOF
    fi

    log "Cleaning up nested .git directories..."
    for dir in frontend backend; do
        if [ -d "$dir/.git" ]; then
            rm -rf "$dir/.git"
        fi
    done

    ok "Root project files created"
}

main() {
    printf "\n"
    printf "\033[0;34m╔══════════════════════════════════════╗\033[0m\n"
    printf "\033[0;34m║       Raidio Project Setup           ║\033[0m\n"
    printf "\033[0;34m╚══════════════════════════════════════╝\033[0m\n"
    printf "\n"

    check_prerequisites
    setup_backend
    setup_frontend
    setup_database
    setup_taskfile
    setup_root

    printf "\n"
    ok "Setup completed successfully!"
    printf "\n"
    printf "  Next steps:\n"
    printf "    1. Run 'task --list' to see all available commands\n"
    printf "    2. Run 'task dev' to start both backend and frontend\n"
    printf "    3. Backend API:  http://localhost:8000\n"
    printf "    4. Backend Docs: http://localhost:8000/docs\n"
    printf "    5. Frontend:     http://localhost:3000\n"
    printf "\n"
}

main
