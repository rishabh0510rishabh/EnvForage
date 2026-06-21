# Contributing to EnvForge

First off, thank you for considering contributing to EnvForge! It's people like you that make this tool better for everyone.

Please read the [Code of Conduct](./CODE_OF_CONDUCT.md) to keep our community approachable and respectable.

## Development Setup

1. **Fork & Clone** the repository.
2. **Start Database**: We use Docker Compose for the PostgreSQL database.
   ```bash
   docker-compose up -d
   ```
3. **Install Dependencies**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   cd ..
   ```

4. **Install Pre-commit Hooks**:
   We recommend installing `pre-commit` globally so it works across all your projects and terminal sessions without needing to activate a virtual environment.
   ```bash
   # Recommended: Install globally
   pipx install pre-commit

   # From the repo root, install the hooks
   pre-commit install
   ```
   > **Note**: If you prefer not to install it globally, you can use the version installed in `backend/.venv`, but you **must** ensure that virtual environment is active whenever you run `git commit`.

5. **Run Migrations & Seeds** (from `backend/`):
   ```bash
   cd backend
   alembic upgrade head
   python -m app.services.seed_service
   ```

## Local Development (No Docker)

If you prefer to run the entire application locally without Docker, follow this guide. This is ideal for rapid iteration, debugging, and development work.

-💡**Developer Workflow Optimization**

- A Makefile is now available at the repository root to standardize common tasks.
Instead of typing out long manual commands, you can now use these simple shortcuts
from the root folder.

- **Run Tests**: `make test`
- **Code Linting/Formatting**: `make lint`
- **Start Development Server**: `make run-dev`
- **Database Migration & Seeds**: `make db-upgrade`

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required for backend |
| Node.js | 18+ | Required for frontend |
| npm or yarn | Latest | Frontend package manager |
| Git | 2.40+ | Version control |
| PostgreSQL (optional) | 14+ | For full-featured development; SQLite available for simpler setup |

**Installation:**
- **Python**: [python.org](https://www.python.org/downloads/)
- **Node.js**: [nodejs.org](https://nodejs.org/) (includes npm)
- **PostgreSQL** (optional): [postgresql.org](https://www.postgresql.org/download/) or use Homebrew on macOS (`brew install postgresql`)
- **Git**: [git-scm.com](https://git-scm.com/)

### Backend Setup (FastAPI)

#### 1. Navigate to Backend Directory
```bash
cd backend
```

#### 2. Create and Activate Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate on macOS/Linux
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -e ".[dev]"
```

#### 4. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

**Option A: Using SQLite (Fastest for Development)**
```bash
# For development without external database
DATABASE_URL=sqlite+aiosqlite:///./envforge_dev.db
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
ENVFORGE_LLM_PROVIDER=mock
```

**Option B: Using PostgreSQL (Recommended)**
```bash
# Set up PostgreSQL database first
# macOS: brew install postgresql && brew services start postgresql
# Linux: sudo apt-get install postgresql && sudo systemctl start postgresql
# Windows: Download and run PostgreSQL installer

# Create database and user
psql -U postgres -c "CREATE ROLE envforge WITH LOGIN PASSWORD 'devpass';"
psql -U postgres -c "CREATE DATABASE envforge OWNER envforge;"

# In .env file:
DATABASE_URL=postgresql+asyncpg://envforge:devpass@localhost:5432/envforge
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
ENVFORGE_LLM_PROVIDER=mock
```

#### 5. Initialize Database

**For SQLite (automatic on first run, but can initialize with):**
```bash
alembic upgrade head
```

**For PostgreSQL:**
```bash
alembic upgrade head
python -m app.services.seed_service
```

#### 6. Run Backend Server
```bash
# From backend/ directory with .venv activated
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload
```

The backend API is now running at **`http://localhost:8000`**

**Verify it's working:**
```bash
curl http://localhost:8000/api/v1/docs
```

### Frontend Setup (Next.js)

#### 1. Navigate to Frontend Directory
```bash
cd frontend
```

#### 2. Install Dependencies
```bash
npm install
# or
yarn install
```

#### 3. Configure Environment Variables

Create a `.env.local` file in the `frontend/` directory:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

#### 4. Run Development Server
```bash
npm run dev
# or
yarn dev
```

The frontend is now running at **`http://localhost:3000`**

### Running Both Services Simultaneously

**Terminal 1: Backend**
```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2: Frontend**
```bash
cd frontend
npm run dev
```

**Terminal 3 (Optional): CLI Agent Testing**
```bash
cd cli
source .venv/bin/activate
pip install -e ".[dev]"
python -m envforge_agent diagnose
```

You now have a complete local development environment running without Docker!

### Environment Variables Reference

**Backend (.env in backend/ directory):**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/envforge
# Or SQLite: sqlite+aiosqlite:///./envforge_dev.db

# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here
APP_VERSION=1.0.0

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# LLM Provider (for AI features)
ENVFORGE_LLM_PROVIDER=mock              # Options: mock, openai, openrouter, ollama
# OPENAI_API_KEY=sk-...               # If using OpenAI
# OPENROUTER_API_KEY=sk-or-...        # If using OpenRouter
# OLLAMA_BASE_URL=http://localhost:11434  # If using Ollama

# Redis (optional, for rate limiting)
REDIS_URL=redis://localhost:6379/0
```

**Frontend (.env.local in frontend/ directory):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

### Troubleshooting

#### Backend Issues

**Port 8000 already in use:**
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:create_app --port 8001 --reload
```

**Database connection error:**
```bash
# If using PostgreSQL, verify service is running
# macOS
brew services list

# Linux
systemctl status postgresql

# Test connection
psql -U envforge -d envforge -c "SELECT 1;"
```

**Migration errors:**
```bash
# Reset database (development only!)
# For SQLite: delete envforge_dev.db
# For PostgreSQL: drop database envforge and recreate

# Then re-run migrations
alembic upgrade head
```

**Import or dependency errors:**
```bash
# Ensure venv is activated and reinstall
pip install -e ".[dev]" --force-reinstall --no-cache-dir
```

#### Frontend Issues

**Port 3000 already in use:**
```bash
# Use a different port
npm run dev -- -p 3001
```

**Dependencies not found:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**API connection issues:**
Check that:
1. Backend is running at `http://localhost:8000`
2. CORS is configured correctly in backend (should include `http://localhost:3000`)
3. `NEXT_PUBLIC_API_URL` in `.env.local` matches backend URL

#### General Issues

**"command not found" errors:**
- Python: Ensure you've installed Python 3.11+ and it's in your PATH
- Node.js: Install from nodejs.org, verify with `node --version`
- Ensure virtual environment is activated: `source .venv/bin/activate`

**Module import errors:**
```bash
# Backend: Reinstall with development dependencies
cd backend && pip install -e ".[dev]"

# Frontend: Clear dependencies
cd frontend && npm ci  # Uses exact versions from package-lock.json
```

**"CORS error" when calling API from frontend:**
Verify in backend `.env`:
```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Testing Locally

**Backend tests:**
```bash
cd backend
pytest tests/
pytest tests/ -v  # Verbose output
pytest tests/unit/  # Only unit tests
```

**Frontend linting:**
```bash
cd frontend
npm run lint
```

**CLI agent tests:**
```bash
cd cli
pytest tests/
```

### Next Steps

- Read [ARCHITECTURE.md](./docs/ARCHITECTURE.md) to understand the codebase structure
- Check [API_DESIGN.md](./docs/API_DESIGN.md) for API endpoint documentation
- See [TESTING.md](./docs/TESTING.md) for comprehensive testing guidelines
- Review [PROFILE_SPEC.md](./docs/PROFILE_SPEC.md) before adding new profiles

## Folder Structure

```
EnvForge/
├── backend/            # FastAPI backend (API, Compatibility Engine, Templates)
├── cli/                # envforge-agent standalone CLI
├── docs/               # Architecture, ADRs, Workflows, Specs
├── .github/            # CI workflows, Issue Templates
└── docker-compose.yml
```

## How to Add Profiles

To add a new ML environment profile (e.g., JAX, TensorRT):
1. Review the [PROFILE_SPEC.md](./docs/PROFILE_SPEC.md) for the required schema.
2. Add your profile to `backend/seeds/profiles.yaml`.
3. Validate your profile using the validation script:
   ```bash
   python -m scripts.validate_profiles backend/seeds/profiles.yaml
   ```
4. Run the seed service (`python -m app.services.seed_service`) to test it locally.
5. Update `docs/FEATURES.md`.

## How to Add Templates

If you need a new output script format (e.g., `Makefile`):
1. Create the template in `backend/app/templates/jinja/`.
2. Register it in `TEMPLATE_MAP` inside `backend/app/templates/engine.py`.
3. Write a rendering test in `backend/tests/unit/templates/`.

## How to Test Scripts

We require high test coverage because generated scripts affect real systems.
- Run backend tests: `pytest tests/`
- Run CLI agent tests: `cd ../cli && pytest tests/`
- **Rule**: If you add a new CUDA version to the compatibility matrix, you *must* add a test case for it in `test_resolver.py`.

See [TESTING.md](./docs/TESTING.md) for more details.

## Pull Request Guidelines

1. Ensure all tests pass.
2. Ensure your code is formatted with `black` and `ruff`. (The pre-commit hooks installed in Step 4 will handle this automatically upon `git commit`).
3. Ensure type checking passes (`mypy app/`).
4. Update relevant documentation in the `docs/` folder.
5. Fill out the Pull Request template completely.

## Commit Style

We follow [Conventional Commits](https://www.conventionalcommits.org/).

Examples:
- `feat(api): add new profile endpoint`
- `fix(agent): handle missing WMI gracefully on Windows`
- `docs: update ROADMAP.md for phase 2`
- `test(core): add edge cases for CompatibilityResolver`

## Branching Strategy

- `main` is the primary development branch.
- Feature branches: `feat/your-feature-name`
- Bugfix branches: `fix/your-bug-name`

## Getting Help
If you need help, please open an issue with the `question` label, or check out [SUPPORT.md](./SUPPORT.md).
