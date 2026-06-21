# EnvForage — Project Structure

> **Version**: 2.0.0
> **Status**: Production
> **Last Updated**: 2026-06-18

This document defines the canonical folder structure for EnvForage.
All contributors should respect this structure and place new files accordingly.

---

## Complete Folder Structure

```
EnvForage/
│
├── README.md                          # Project overview + quick start
├── CONTRIBUTING.md                    # Contributor guide
├── LICENSE
├── .gitignore
├── docker-compose.yml                 # Dev stack (API + DB + frontend)
├── docker-compose.prod.yml            # Production stack
│
├── docs/                              # All project documentation
│   ├── ARCHITECTURE.md
│   ├── FEATURES.md
│   ├── WORKFLOW.md
│   ├── API_DESIGN.md
│   ├── COMPATIBILITY_ENGINE.md
│   ├── TEMPLATE_SYSTEM.md
│   ├── AI_LAYER.md
│   ├── DATABASE_SCHEMA.md
│   ├── decisions/                     # Architecture Decision Records (ADRs)
│   │   ├── ADR-001-rest-over-graphql.md
│   │   ├── ADR-002-structured-ai-output.md
│   │   └── ADR-003-jinja2-template-engine.md
│   ├── features/                      # Per-feature deep-dive docs
│   │   ├── script-generation.md
│   │   ├── cli-agent.md
│   │   └── ai-troubleshooting.md
│   └── workflows/                     # Step-by-step workflow guides
│       ├── dev-setup.md
│       └── adding-a-profile.md
│
├── backend/                           # FastAPI Python backend
│   ├── Dockerfile
│   ├── pyproject.toml                 # PEP 517 project config (replaces setup.py)
│   ├── .env.example
│   ├── alembic.ini
│   │
│   ├── alembic/                       # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py        # Initial schema migration
│   │
│   ├── seeds/                         # Seed data (YAML fixtures)
│   │   ├── profiles.yaml
│   │   ├── cuda_matrix.yaml
│   │   └── framework_matrix.yaml
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py                    # FastAPI app factory
│       ├── config.py                  # Settings (pydantic-settings)
│       ├── database.py                # SQLAlchemy async engine + session
│       │
│       ├── models/                    # SQLAlchemy ORM models
│       │   ├── __init__.py
│       │   ├── profile.py
│       │   ├── script_job.py
│       │   ├── diagnostic.py
│       │   └── ai_session.py
│       │
│       ├── schemas/                   # Pydantic request/response schemas
│       │   ├── __init__.py
│       │   ├── profile.py
│       │   ├── script.py
│       │   ├── diagnostic.py
│       │   ├── verification.py
│       │   └── ai.py
│       │
│       ├── api/                       # Route handlers (thin controllers)
│       │   ├── __init__.py
│       │   ├── deps.py                # FastAPI dependency injectors
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── profiles.py
│       │       ├── scripts.py
│       │       ├── diagnose.py
│       │       ├── verify.py
│       │       └── troubleshoot.py
│       │
│       ├── services/                  # Business logic layer
│       │   ├── __init__.py
│       │   ├── profile_service.py
│       │   ├── script_service.py
│       │   ├── diagnostic_service.py
│       │   ├── verification_service.py
│       │   └── ai_service.py
│       │
│       ├── compatibility/             # Compatibility Engine (pure logic)
│       │   ├── __init__.py
│       │   ├── resolver.py
│       │   ├── errors.py
│       │   ├── models.py
│       │   └── matrix/
│       │       ├── cuda.py
│       │       ├── python.py
│       │       └── os_rules.py
│       │
│       ├── templates/                 # Template Engine
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── safety.py
│       │   ├── models.py
│       │   └── jinja/
│       │       ├── setup/
│       │       │   ├── setup_linux.sh.j2
│       │       │   ├── setup_windows.ps1.j2
│       │       │   └── setup_wsl.sh.j2
│       │       ├── config/
│       │       │   ├── requirements.j2
│       │       │   ├── dockerfile.j2
│       │       │   └── devcontainer.j2
│       │       ├── verify/
│       │       │   ├── verify_torch.sh.j2
│       │       │   ├── verify_tf.sh.j2
│       │       │   └── verify_opencv.sh.j2
│       │       └── repair/
│       │           ├── repair_cuda_upgrade.sh.j2
│       │           └── repair_driver_update.sh.j2
│       │
│       └── ai/                        # AI Reasoning Layer
│           ├── __init__.py
│           ├── service.py
│           ├── safety.py
│           ├── models.py
│           ├── providers/
│           │   ├── base.py
│           │   ├── openai.py
│           │   ├── openrouter.py
│           │   ├── ollama.py
│           │   └── mock.py
│           └── prompts/
│               ├── system.py
│               └── troubleshoot.py
│
├── tests/                             # Backend tests (pytest)
│   ├── conftest.py
│   ├── unit/
│   │   ├── compatibility/
│   │   │   ├── test_resolver.py
│   │   │   ├── test_cuda_matrix.py
│   │   │   └── test_python_matrix.py
│   │   ├── templates/
│   │   │   ├── test_engine.py
│   │   │   ├── test_safety.py
│   │   │   └── snapshots/
│   │   └── ai/
│   │       ├── test_safety.py
│   │       └── test_service.py
│   └── integration/
│       ├── test_profiles_api.py
│       ├── test_scripts_api.py
│       └── test_troubleshoot_api.py
│
├── cli/                               # CLI Diagnostic Agent (standalone package)
│   ├── Dockerfile
│   ├── pyproject.toml                 # Separate package: envforage
│   ├── README.md
│   └── envforage/
│       ├── __init__.py
│       ├── __main__.py                # Entry: python -m envforage
│       ├── cli.py                     # Click CLI commands
│       ├── detectors/
│       │   ├── __init__.py
│       │   ├── os_detector.py
│       │   ├── gpu_detector.py
│       │   ├── cuda_detector.py
│       │   ├── python_detector.py
│       │   └── driver_detector.py
│       ├── schemas.py                 # DiagnosticReport Pydantic model
│       ├── report.py                  # Report builder + formatter
│       └── tests/
│           ├── test_detectors.py
│           └── fixtures/
│               ├── windows_gpu.json
│               ├── linux_no_cuda.json
│               └── wsl_cuda.json
│
├── frontend/                          # Next.js Web Application
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   ├── .env.local.example
│   ├── public/
│   │   └── favicon.ico
│   └── src/
│       ├── app/                       # Next.js App Router
│       │   ├── layout.tsx
│       │   ├── page.tsx               # Home / landing
│       │   ├── profiles/
│       │   │   ├── page.tsx           # Profile browser
│       │   │   └── [id]/
│       │   │       └── page.tsx       # Profile detail
│       │   ├── generate/
│       │   │   └── page.tsx           # Script generation wizard
│       │   ├── diagnose/
│       │   │   └── page.tsx           # Diagnostic report upload + view
│       │   └── troubleshoot/
│       │       └── page.tsx           # AI troubleshooting interface
│       │
│       ├── components/
│       │   ├── ui/                    # Base UI components (buttons, cards, etc.)
│       │   ├── profiles/              # Profile-specific components
│       │   ├── scripts/               # Script preview + download components
│       │   ├── diagnostic/            # Diagnostic report components
│       │   └── ai/                    # AI chat + fix display components
│       │
│       ├── lib/
│       │   ├── api/                   # Typed API client
│       │   │   ├── client.ts
│       │   │   ├── profiles.ts
│       │   │   ├── scripts.ts
│       │   │   ├── diagnose.ts
│       │   │   └── troubleshoot.ts
│       │   └── types/                 # Shared TypeScript types (generated from OpenAPI)
│       │       └── api.ts
│       │
│       └── styles/
│           └── globals.css
│
└── .github/
    └── workflows/
        ├── ci.yml                     # Lint + test + build on PR
        └── release.yml                # Release automation
```

---

## Key Structural Rules

1. **`app/api/`**: Only route handlers. No business logic. Max 20 lines per handler.
2. **`app/services/`**: All business logic. Services call compatibility engine, templates, AI.
3. **`app/compatibility/`**: Pure functions only. No database calls, no HTTP calls.
4. **`app/templates/`**: Rendering only. Template Engine does NOT call services.
5. **`app/ai/`**: AI reasoning only. AI providers do NOT write to the database.
6. **`cli/`**: Completely standalone. Does NOT import from `backend/app/`.
7. **`tests/unit/`**: No database, no network, no file system (mock all I/O).
8. **`tests/integration/`**: May use test database (in-memory SQLite or Docker PostgreSQL).
