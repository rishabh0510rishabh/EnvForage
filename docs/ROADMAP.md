# EnvForge — Development Roadmap

> **Version**: 1.0.0
> **Status**: All Phases Complete (v1.0.0 Release Ready)
> **Last Updated**: 2026-05-21

---

## Phase 0 — Foundation ✅ Complete

**Goal**: Establish project structure, documentation, and base configurations.

### Deliverables
- [x] High-level architecture design
- [x] Folder structure scaffolding
- [x] Database schema design
- [x] Compatibility engine design
- [x] Template system design
- [x] Documentation strategy
- [x] Development environment setup (Docker Compose)
- [x] `.gitignore`, `pyproject.toml`, `Dockerfile`
- [x] CI/CD pipeline skeleton (GitHub Actions) — *Phase 6*
- [x] Contributor guide (CONTRIBUTING.md) — *Phase 6*

**Exit Criteria**: Any contributor can clone and run the dev stack locally. ✅

---

## Phase 1 — Core Backend ✅ Complete

**Goal**: Working FastAPI backend with compatibility engine and static profiles.

### 1.1 — Data Layer
- [x] PostgreSQL schema migrations (Alembic) — `0001_initial.py` (10 tables)
- [x] SQLAlchemy 2.0 async ORM models (all entities)
- [x] Seed data: 6 environment profiles (`seeds/profiles.yaml`)
- [x] CUDA compatibility matrix seed data (`seeds/cuda_matrix.yaml`)
- [x] Idempotent seed service (`app/services/seed_service.py`)

### 1.2 — Compatibility Engine
- [x] `CompatibilityResolver` class — pure logic, no I/O
- [x] CUDA ↔ Driver ↔ cuDNN version matrix (11.8, 12.1, 12.4)
- [x] Python ↔ Framework version matrix (torch 2.0–2.4, tf 2.13–2.15)
- [x] OS-specific constraint rules (WSL GPU note, TF Windows note)
- [x] Structured error types: `IncompatibilityError`, `UnknownVersionError`, `UnsupportedOSError`
- [x] 11 unit tests (positive, negative, edge cases)

### 1.3 — Template Engine
- [x] Jinja2 template loader (`TemplateRenderer`)
- [x] `setup.sh` template (Linux/WSL) with pre-flight checks
- [x] `setup.ps1` template (Windows PowerShell)
- [x] `requirements.txt` template
- [x] `Dockerfile` template (CPU and CUDA variants)
- [x] `devcontainer.json` template
- [x] `verify_torch.sh` template (PyTorch CUDA verification)
- [x] Safety filter — 15 forbidden patterns (10 unit tests)

### 1.4 — API Endpoints
- [x] `GET /api/v1/profiles` — list profiles (filterable by OS, CUDA, tags)
- [x] `GET /api/v1/profiles/{slug}` — get single profile
- [x] `POST /api/v1/scripts/generate` — generate + persist scripts
- [x] `GET /api/v1/scripts/{job_id}/download` — ZIP bundle download
- [x] `POST /api/v1/diagnose` — accept CLI diagnostic report

### 1.5 — AI Layer Skeleton
- [x] `LLMProvider` ABC (pluggable provider interface)
- [x] `MockProvider` (deterministic, for testing)
- [x] `SuggestedFix` + `TroubleshootResponse` Pydantic models

**Exit Criteria**: Can generate a valid `setup.sh` for "PyTorch CUDA" via API. ✅

---

## Phase 2 — CLI Diagnostic Agent ✅ Complete

**Goal**: Standalone Python package that collects and reports system info.

### Deliverables
- [x] `envforge-agent` PyPI package structure (`cli/pyproject.toml`)
- [x] OS detection module — Linux (`/etc/os-release`), Windows (`winreg`), WSL2 detection
- [x] GPU/VRAM detection — `nvidia-smi` CSV query, multi-GPU support
- [x] CUDA version detection — `nvcc`, `version.txt`, env vars, `nvidia-smi` fallback
- [x] Python environment scanner — probes python3.8–3.12 + Windows `py` launcher
- [x] cuDNN version detection — header file parse + PyTorch fallback
- [x] WSL detection — `/proc/version`, `WSL_DISTRO_NAME` env, WSL1 vs WSL2 distinction
- [x] RAM/CPU detection — psutil + `/proc/cpuinfo` + `winreg`
- [x] Structured JSON output — `DiagnosticReport` Pydantic schema (in sync with backend)
- [x] CLI: `envforge diagnose` — rich table output, `--output`, `--send`, `--quiet` flags
- [x] CLI: `envforge verify` — check profile compatibility via API
- [x] CLI: `envforge fix` — generate repair script from saved report
- [x] 4 platform JSON fixtures: linux_gpu, wsl_cuda, linux_no_cuda, windows_gpu
- [x] 20+ unit tests: schema round-trips, mocked detector tests, ReportBuilder integration
- [x] Integration: `POST /api/v1/diagnose` endpoint on backend (Phase 1)

**Exit Criteria**: `envforge diagnose` outputs valid `DiagnosticReportSchema` JSON
on Windows, WSL2, and Ubuntu 22.04. ✅

**Exit Criteria**: `envforge diagnose` outputs valid JSON on Windows, WSL, and Ubuntu.

---

## Phase 3 — Frontend (Next.js) ✅ Complete

**Goal**: Working web UI for profile browsing and script generation.

### Deliverables
- [x] Project init with Next.js 14+ App Router, TypeScript, TailwindCSS
- [x] Design system (tokens, typography, color palette)
- [x] Home/landing page
- [x] Profile browser page with filtering
- [x] Profile detail page with metadata
- [x] Script generation wizard (multi-step form)
- [x] Script preview and download UI
- [x] Diagnostic report upload + results viewer *(Moved to Phase 4 integration)*
- [x] API client (typed, using `fetch` or `axios`)

**Exit Criteria**: End-to-end: select profile → configure → download `setup.sh`. ✅

---

## Phase 4 — AI Troubleshooting Layer [COMPLETED]

**Goal**: AI-assisted diagnosis and repair script generation.

### Deliverables
- [x] LLM provider abstraction (pluggable: OpenAI, OpenRouter, Ollama)
- [x] Structured prompt builder (diagnostic context → prompt)
- [x] `SuggestedFix` response schema (Pydantic)
- [x] Shell command safety filter
- [x] `POST /api/troubleshoot` endpoint
- [x] `POST /api/repair` endpoint (generates repair scripts)
- [x] Frontend AI chat interface
- [x] Rate limiting (in-memory, Redis-swappable)

**Exit Criteria**: Given a diagnostic JSON, AI returns structured fix suggestions.
The frontend displays these and allows generating safe, filtered repair scripts. [COMPLETED]

---

## Phase 5 — Environment Verification ✅ Complete

**Goal**: Automated verification of installed ML environments.

### Deliverables
- [x] Verification script generator (per framework)
- [x] TensorFlow GPU verification script
- [x] PyTorch CUDA verification script
- [x] OpenCV install verification
- [x] `POST /api/verify` endpoint
- [x] Verification result schema + frontend display

---

## Phase 6 — Polish & Production Readiness ✅ Complete

**Goal**: Hardening, docs, and community readiness.

### Deliverables
- [x] Full OpenAPI documentation
- [x] Rate limiting + API key management
- [x] Docker Compose (dev) + Dockerfile (prod) for all services
- [x] GitHub Actions: lint, test, build pipeline
- [x] Contributor docs + ADR library
- [x] Security audit: input sanitization, prompt injection prevention
- [x] Performance benchmarks for compatibility resolution
- [x] Public beta release

---

## Milestone Summary

| Phase | Name | Target |
|-------|------|--------|
| 0 | Foundation | Week 1 |
| 1 | Core Backend | Week 2–3 |
| 2 | CLI Agent | Week 4 |
| 3 | Frontend | Week 5–6 |
| 4 | AI Layer | Week 7–8 |
| 5 | Verification | Week 9 |
| 6 | Production | Week 10–12 |
