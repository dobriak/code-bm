#!/bin/bash
PYVER=3.12

set -e

TARGET=$1

if [ "$TARGET" != "frontend" ] && [ "$TARGET" != "backend" ]; then
    echo "Usage: $0 [frontend|backend]"
    echo "  frontend - Set up React + TypeScript + TailwindCSS + ShadCN"
    echo "  backend  - Set up FastAPI + Pydantic + SQLAlchemy + SQLite"
    exit 1
fi

echo "Setting up $TARGET..."

install_uv() {
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
}

install_bun() {
    echo "Installing bun..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
}

install_task() {
    echo "Installing task (Taskfile CLI)..."
    sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
}

check_prerequisites() {
    if [ "$TARGET" = "backend" ]; then
        if ! command -v uv &> /dev/null; then
            echo "uv not found"
            install_uv
        else
            echo "✓ uv is installed"
        fi
    fi
    
    if [ "$TARGET" = "frontend" ]; then
        if ! command -v bun &> /dev/null; then
            echo "bun not found"
            install_bun
        else
            echo "✓ bun is installed"
        fi
    fi
    if ! command -v task &> /dev/null; then
        echo "task cli not found"
        install_task
    else
        echo "✓ task is installed"
    fi
    if [ ! -f Taskfile.yml ]; then
        setup_taskfile
    fi
}

setup_backend() {
    echo ""
    echo "=== Setting up Backend ==="
    echo ""
    
    check_prerequisites
    
    echo "Creating root .gitignore..."
    cat > .gitignore << 'EOF'
# Database
database/*.db

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment variables
.env
.env.local
.env.*.local
EOF
    
    echo "Creating backend directory..."
    mkdir -p backend
    mkdir -p database
    
    cd backend
    
    echo "Initializing Python project with uv..."
    uv init --name raidio-backend --python $PYVER
    
    echo "Adding dependencies..."
    uv add fastapi uvicorn[standard] pydantic sqlalchemy
    
    echo "Creating main application file..."
    cat > main.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column
from typing import Optional

app = FastAPI(title="Raidio API", version="1.0.0")

DATABASE_URL = "sqlite:///../database/raidio.db"

engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


Base.metadata.create_all(bind=engine)


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


@app.get("/")
def root():
    return {"message": "Welcome to Raidio API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate):
    db = SessionLocal()
    try:
        db_user = User(**user.model_dump())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/users/", response_model=list[UserResponse])
def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return users
    finally:
        db.close()


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
    
    echo "Creating .python-version file..."
    echo "3.12" > .python-version
    
    echo "Creating backend .gitignore..."
    cat > .gitignore << 'EOF'
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
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
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
pytestdebug.log

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# poetry
poetry.lock

# pdm
.pdm.toml
.pdm-python
.pdm-build/

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# Ruff
.ruff_cache/

# Database files
*.db
*.sqlite
*.sqlite3

# Lock files (uv)
uv.lock
EOF
    
    cd ..
    
    echo ""
    echo "✓ Backend setup complete!"
    echo ""
    echo "To run the backend:"
    echo "  task backend:dev"
    echo ""
    echo "API will be available at: http://localhost:8000"
    echo "API docs will be available at: http://localhost:8000/docs"
    echo ""
    echo "Other useful commands:"
    echo "  task backend:install   - Install backend dependencies"
    echo "  task backend:run       - Run backend in production mode"
    echo "  task --list            - List all available tasks"
}

setup_frontend() {
    echo ""
    echo "=== Setting up Frontend ==="
    echo ""
    
    check_prerequisites
    

    
    echo "Creating React project with Bun..."
    bun init --react frontend
    
    cd frontend
    
    echo "Installing TailwindCSS 4..."
    bun add tailwindcss @tailwindcss/vite
    
    echo "Configuring Vite for TailwindCSS..."
    cat > vite.config.ts << 'EOF'
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
EOF
    
    echo "Creating main CSS with TailwindCSS..."
    cat > src/index.css << 'EOF'
@import "tailwindcss";
EOF
    
    echo "Updating tsconfig.json..."
    cat > tsconfig.json << 'EOF'
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
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF
    
    echo "Installing ShadCN UI..."
    bunx shadcn@latest init -d -y
    
    echo "Creating example component..."
    cat > src/App.tsx << 'EOF'
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
EOF
    
    echo "Fixing frontend.tsx import..."
    if [ -f src/frontend.tsx ]; then
        sed -i 's/import { App } from ".\/App";/import App from ".\/App";/' src/frontend.tsx
    fi
    
    cd ..
    
    echo ""
    echo "✓ Frontend setup complete!"
    echo ""
    echo "To run the frontend:"
    echo "  task frontend:dev"
    echo ""
    echo "App will be available at: http://localhost:3000"
    echo ""
    echo "Other useful commands:"
    echo "  task frontend:install  - Install frontend dependencies"
    echo "  task frontend:build    - Build for production"
    echo "  task --list            - List all available tasks"
}

setup_taskfile(){

    cat > Taskfile.yml << 'EOF'
# yaml-language-server: $schema=https://taskfile.dev/schema.json

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

  # Backend tasks
  backend:install:
    desc: Install backend dependencies using uv
    dir: backend
    cmds:
      - uv sync

  backend:run:
    desc: Run the FastAPI backend server
    dir: backend
    cmds:
      - uv run uvicorn main:app --host 0.0.0.0 --port {{.BACKEND_PORT}}

  backend:dev:
    desc: Run the FastAPI backend in development mode with auto-reload
    dir: backend
    cmds:
      - uv run uvicorn main:app --reload --host 0.0.0.0 --port {{.BACKEND_PORT}}

  # Frontend tasks
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

  # Combined tasks
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
EOF
    echo "Taskfile created."
}

setup_root() {
    if [ ! -f .gitignore ]; then
        echo "Creating root .gitignore..."
        cat > .gitignore << 'EOF'
# Database
database/

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment variables
.env
.env.local
.env.*.local
EOF
    fi
    echo "Making sure automation did not try to add .git in frontend and backend"
    for dir in frontend backend; do
        if [ -d ${dir}/.git ]; then
            echo "Removing ${dir}/.git"
            rm -rf ${dir}/.git
        fi
    done
}


if [ "$TARGET" = "backend" ]; then
    setup_backend
elif [ "$TARGET" = "frontend" ]; then
    setup_frontend
fi
setup_root

echo ""
echo "Setup completed successfully! 🎉"
echo ""
echo "Next steps:"
echo "  1. Run 'task --list' to see all available commands"
echo "  2. Run 'task dev' to start both backend and frontend in development mode"
echo "  3. Or run 'task backend:dev' or 'task frontend:dev' individually"

