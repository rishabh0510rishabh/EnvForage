# EnvForage — Workflow Documentation

> **Version**: 2.1.0
> **Status**: Stable v2.1.0
> **Last Updated**: 2026-06-18

---

## Implementation Status

| Workflow | Status | Notes |
|---------|--------|-------|
| Script Generation | ✅ Implemented | API endpoints live |
| Environment Diagnosis | ✅ Backend + Frontend | Web Diagnostic Dashboard live |
| AI Troubleshooting | 🔲 Planned | Phase 4 |
| Profile Verification | 🔲 Planned | Phase 5 |
| Contributor Workflow | ✅ Documented | Docker Compose ready |

---

## Workflow 1: Script Generation ✅

**Implemented in Phase 1.** The full pipeline — from profile selection through
compatibility resolution, template rendering, safety filtering, and ZIP download
— is operational via the API.

```
User opens EnvForage Web App (Phase 3: Implemented and deployed to Vercel)
    │
    ▼
GET /api/v1/profiles
    Response: ProfileListResponse { profiles[], total, page, page_size }
    Supports filters: ?os=LINUX&cuda_required=true&tags=gpu
    │
    ▼
GET /api/v1/profiles/{slug}
    Example: GET /api/v1/profiles/pytorch-cuda
    Response: ProfileDetailSchema { packages[], python_versions[], ... }
    │
    ▼
POST /api/v1/scripts/generate
    Body:
    {
      "profile_id": "pytorch-cuda",
      "target_os": "LINUX",         // LINUX | WSL | WIN
      "python_version": "3.11",
      "cuda_version": "11.8",
      "overrides": {},              // optional: { "torch": "2.2.0" }
      "output_formats": ["setup.sh", "requirements.txt", "Dockerfile"]
    }
    │
    ├── CompatibilityResolver.resolve()
    │     ├── Validate OS is in profile.os_support
    │     ├── Validate CUDA version against CUDA matrix
    │     ├── Validate Python version against framework matrix
    │     ├── Apply overrides (validated)
    │     └── Collect OS-specific warnings (e.g., WSL GPU note)
    │     (Incompatibility → HTTP 409 with structured error)
    │
    ├── TemplateRenderer.render_all(output_formats, context)
    │     └── SafetyFilter.validate(rendered_content)
    │           (15 dangerous patterns blocked)
    │
    └── Persist ScriptGenerationJob + GeneratedScript to DB
    │
    Response 201:
    {
      "job_id": "uuid",
      "status": "completed",
      "resolved_packages": [{ "name": "torch", "version": "2.1.2", "cuda_variant": "cu118" }],
      "scripts": [{ "filename": "setup.sh", "content": "...", "size_bytes": 2048 }],
      "warnings": [...],
      "download_url": "/api/v1/scripts/{job_id}/download"
    }
    │
    ▼
GET /api/v1/scripts/{job_id}/download
    Response: application/zip
    Archive contains: setup.sh, requirements.txt, Dockerfile, MANIFEST.txt
```

### Error Handling

| Error | HTTP | Code | Example Cause |
|-------|------|------|--------------|
| Profile not found | 404 | `PROFILE_NOT_FOUND` | Bad slug |
| Wrong OS | 409 | `UNSUPPORTED_OS` | WIN on LINUX-only profile |
| CUDA not in matrix | 409 | `INCOMPATIBLE_VERSIONS` | CUDA 10.2 |
| Python mismatch | 409 | `INCOMPATIBLE_VERSIONS` | Python 3.7 + torch 2.1 |

---

## Workflow 2: Environment Diagnosis (Backend ✅ + Frontend ✅, CLI Agent Phase 2 ✅)

The backend `POST /api/v1/diagnose` endpoint is live and accepts structured
`DiagnosticReport` JSON. The frontend **Diagnostic Dashboard** (`/diagnose`)
provides a web UI for pasting, parsing, and verifying reports against profiles.

### Current (Phase 3) — Web Diagnostic Dashboard

```
User opens /diagnose in the EnvForage Web App
    │
    ▼
Paste DiagnosticReport JSON into the text area
(output of `envforage diagnose --quiet` or manually constructed)
    │
    ▼
Click "Analyze Report" → Client-side JSON parse + validation
    │
    ▼
Hardware Overview rendered (OS, CPU, GPU, CUDA cards)
    │
    ▼
Select Target Profile from dropdown → Click "Run Check"
    │
    ▼
POST /api/v1/diagnose
Body: DiagnosticReportSchema {
  "agent_version": "2.1.0",
  "os": { "name": "Ubuntu 22.04", "version": "22.04", "architecture": "x86_64" },
  "cpu": { "brand": "Intel Core i9", "cores": 12, "threads": 24 },
  "ram": { "total_gb": 32.0, "available_gb": 20.0 },
  "gpus": [{ "name": "NVIDIA RTX 4080", "vram_gb": 16.0, "driver_version": "535.54" }],
  "cuda": { "version": "12.1", "toolkit_path": "/usr/local/cuda-12.1" },
  "python_installations": [{ "version": "3.11.4", "path": "/usr/bin/python3.11" }],
  "active_python": { "version": "3.11.4", "path": "/usr/bin/python3.11" }
}
    │
    ▼
Backend:
  - Persists DiagnosticReport to DB (returns report_id)
  - Checks CUDA version against CUDA matrix
  - Lists compatible profiles
  - Flags issues with severity + suggested fix
    │
    ▼
Response 201:
{
  "report_id": "uuid",
  "compatible_profiles": ["pytorch-cuda", "yolov8", "stable-diffusion"],
  "issues": [
    {
      "severity": "WARNING",
      "component": "cuda",
      "message": "CUDA 10.2 not in validated matrix",
      "suggested_fix": "Upgrade to CUDA 11.8 or 12.1"
    }
  ],
  "recommendations": ["pytorch-cuda with CUDA 12.1"]
}
```

### Phase 2 — CLI Agent Flow (Planned)

```
pip install envforage
    │
    ▼
envforage diagnose
    ├── OS detection (platform, wsl_version)
    ├── CPU detection (cpuinfo / wmi)
    ├── RAM detection (psutil)
    ├── GPU detection (nvidia-smi → JSON)
    ├── CUDA detection (nvcc --version)
    ├── Python scan (all python3.x in PATH)
    └── Driver detection (nvidia-smi driver query)
    │
    ▼
DiagnosticReport JSON (stdout or --output report.json)
    │
    └── If --send flag: POST /api/v1/diagnose automatically
```

---

## Workflow 3: AI Troubleshooting (Backend ✅ — Phase 4)

The AI troubleshooting pipeline is fully implemented on the backend.
Frontend integration is Part 6 of Phase 4.

### Backend Flow

```
User submits diagnostic data + profile context
    │
    ▼
POST /api/v1/troubleshoot
{
  "diagnostic": { ... DiagnosticReport JSON ... },
  "profile_slug": "pytorch-cuda",
  "user_description": "torch.cuda.is_available() returns False"
}
    │
    ▼
AITroubleshootService pipeline:
  1. TroubleshootPromptBuilder → structured user message
     (injects CUDA matrix, profile context, sanitised user input)
  2. LLMProvider.complete(system_prompt, user_msg, TroubleshootResponse)
  3. SafetyFilter.validate(root_cause, fix descriptions, safe_commands)
  4. Persist AISession + AISuggestions to DB
  5. Write AIAuditLog (input hash, safety status, tokens, latency)
    │
    ▼
Response 201:
{
  "session_id": "uuid",
  "root_cause": "CUDA 10.2 is not supported by PyTorch 2.3...",
  "suggested_fixes": [
    {
      "step": 1,
      "title": "Upgrade CUDA toolkit",
      "description": "Your CUDA 10.2 is below the minimum...",
      "severity": "CRITICAL",
      "safe_commands": ["nvcc --version", "nvidia-smi"],
      "repair_template_id": "repair_cuda_upgrade"
    }
  ],
  "repair_script_available": true,
  "confidence": 0.85,
  "disclaimer": "AI suggestions are advisory only..."
}
```

### Repair Script Flow

```
User clicks "Generate Repair Script" on a suggested fix
    │
    ▼
POST /api/v1/repair
{
  "template_id": "repair_cuda_upgrade",
  "params": { "target_cuda_version": "12.1" }
}
    │
    ▼
RepairService:
  1. Look up Jinja2 template: repair/repair_cuda_upgrade.sh.j2
  2. Render with validated params
  3. SafetyFilter validates rendered output
    │
    ▼
Response 201:
{
  "template_id": "repair_cuda_upgrade",
  "filename": "repair_cuda_upgrade.sh",
  "content": "#!/bin/bash\n# EnvForage Repair Script...",
  "size_bytes": 2048,
  "disclaimer": "Review carefully before executing."
}
```

### Available Repair Templates

| Template ID | Description |
|-------------|-------------|
| `repair_cuda_upgrade` | Upgrade CUDA toolkit to a supported version |
| `repair_python_install` | Install or switch Python version (pyenv/system) |
| `repair_driver_update` | Check and guide NVIDIA driver update |
| `repair_venv_recreate` | Back up and recreate Python virtual environment |
| `repair_pip_reinstall` | Force-reinstall pip packages with correct versions |

### AI Providers (Pluggable via `ENVFORAGE_LLM_PROVIDER` env var)

| Provider | Status | Use Case |
|----------|--------|---------|
| `mock` | ✅ Implemented | Development / testing |
| `openrouter` | ✅ Implemented | Production — routes to 100+ models (GPT-4o, Llama 3, etc.) |
| `openai` | 🔲 Planned | Use OpenRouter with `openai/gpt-4o` model instead |
| `ollama` | 🔲 Planned | Air-gapped / local inference |

---

## Workflow 4: Profile Verification 🔲 (Phase 5)

**Not yet implemented.** The `verify_torch.sh.j2` template is implemented and
can be generated via the script generation workflow. Full verification integration
is a Phase 5 deliverable.

```
(Planned — Phase 5)

After running setup.sh:
    │
    ▼
POST /api/v1/scripts/generate
  { "output_formats": ["verify_torch.sh"] }  → Download verify_torch.sh
    │
    ▼
User runs: bash verify_torch.sh
    ├── PASS: Python 3.11 found
    ├── PASS: PyTorch import successful
    ├── PASS: CUDA available — GPU: RTX 4080
    ├── PASS: torch.version.cuda == "11.8"
    └── PASS: nvidia-smi driver found
    │
    ▼
POST /api/v1/verify (Phase 5 endpoint)
  { "profile_id": "pytorch-cuda", "diagnostic_report_id": "..." }
    │
    ▼
VerificationResult { checks[], overall_status: "PASSED" | "FAILED" | "PARTIAL" }
    │
    └── If FAILED → Workflow 3: AI Troubleshooting
```

---

## Contributor Workflow ✅

This workflow is fully operational for Phase 1.

### Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/envforage
cd EnvForage

# 2. Start dev stack (API + PostgreSQL)
docker-compose up -d
# API available at: http://localhost:8000
# OpenAPI docs at:  http://localhost:8000/api/docs

# 3. Local development (without Docker)
cd backend
pip install -e ".[dev]"
cp .env.example .env          # Edit DATABASE_URL to point to local Postgres
alembic upgrade head          # Run migrations
python -m app.services.seed_service  # Load seed profiles
uvicorn app.main:app --reload # Start API
```

### Testing

```bash
cd backend

# Run all unit tests (no database or network required)
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ --cov=app --cov-report=term-missing

# Run a specific test module
pytest tests/unit/compatibility/test_resolver.py -v
```

### Before Submitting a PR

```bash
# Format
black app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy app/

# Run tests (must all pass)
pytest tests/unit/ -v

# Update relevant docs/
# → If you changed a service: update docs/features/<feature>.md
# → If you changed architecture: update docs/ARCHITECTURE.md
# → If you made a significant design decision: add docs/decisions/ADR-XXX.md
```

### File Placement Rules

| What you're adding | Where it goes |
|---|---|
| Business logic | `backend/app/services/` |
| API route handler | `backend/app/api/v1/` (max 20 lines per handler) |
| DB model | `backend/app/models/` |
| Pydantic schema | `backend/app/schemas/` |
| Compatibility rule | `backend/app/compatibility/` |
| Jinja2 template | `backend/app/templates/jinja/` |
| Seed data | `backend/seeds/` (YAML format) |
| Unit test | `backend/tests/unit/` |
| Integration test | `backend/tests/integration/` |

> Every implemented feature must have its status updated in `docs/FEATURES.md` before the PR is merged.
