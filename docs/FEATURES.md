# EnvForge — Feature Specifications

> **Version**: 1.0.0
> **Status**: Phase 1, 3 & Production Infrastructure Implemented
> **Last Updated**: 2026-05-16

---

## Implementation Status

| Feature | Status | Phase |
|---------|--------|-------|
| Web Application (Frontend) | ✅ Implemented | Phase 3 |
| Environment Profiles | ✅ Implemented | Phase 1 & 3 |
| Script Generation | ✅ Implemented | Phase 1 & 3 |
| Diagnostic Report Ingestion | ✅ Implemented | Phase 1 & 3 |
| Environment Verification | 🔲 Planned | Phase 5 |
| AI Troubleshooting Layer | 🔶 In Progress | Phase 4 |
| Production Infrastructure | ✅ Implemented | Phase 6 |

---

## Feature 1: Environment Profiles

### Purpose
Pre-defined, validated configurations for common ML/AI workflows. Each profile
encapsulates all version constraints and setup parameters needed to provision a
working environment.

### Status: ✅ Implemented (Phase 1)

**Implementation**: `backend/app/models/profile.py`, `backend/app/services/profile_service.py`
**API**: `GET /api/v1/profiles`, `GET /api/v1/profiles/{slug}`
**Seed data**: `backend/seeds/profiles.yaml`

### Profiles (Phase 1 Seeded Set)

| Profile Slug | Name | Primary Framework | CUDA Required | OS Support |
|---|---|---|---|---|
| `pytorch-cuda` | PyTorch CUDA | torch 2.1.2 | Yes | LINUX, WSL |
| `tf-gpu` | TensorFlow GPU | tensorflow 2.14.0 | Yes | LINUX, WSL |
| `yolov8` | YOLOv8 | ultralytics 8.2.0 | Optional | LINUX, WSL, WIN |
| `stable-diffusion` | Stable Diffusion | diffusers 0.27.2 | Yes | LINUX, WSL |
| `opencv-beginner` | OpenCV Beginner | opencv-python 4.9.0.80 | No | LINUX, WSL, WIN |
| `llm-finetune` | LLM Fine-Tuning | peft 0.10.0 + trl 0.8.6 | Optional | LINUX, WSL |

### SQLAlchemy ORM Model

```python
class EnvironmentProfile(Base):
    __tablename__ = "environment_profiles"

    id: Mapped[uuid.UUID]           # Primary key (UUID)
    slug: Mapped[str]               # Unique identifier, e.g. "pytorch-cuda"
    name: Mapped[str]               # Display name
    description: Mapped[str | None]
    tags: Mapped[list[str] | None]  # PostgreSQL ARRAY(String)
    os_support: Mapped[list[str]]   # ["LINUX", "WSL", "WIN"]
    cuda_required: Mapped[bool]
    python_versions: Mapped[list[str]]
    cuda_versions: Mapped[list[str] | None]
    status: Mapped[str]             # "ACTIVE" | "DEPRECATED"
    last_validated: Mapped[date | None]
    created_at / updated_at / deleted_at  # Soft-delete pattern
```

### Pydantic Response Schemas

```python
# Lightweight — used in list responses
class ProfileSummarySchema(BaseModel):
    id, slug, name, description, tags, os_support, cuda_required,
    python_versions, cuda_versions, status, last_validated

# Full detail — includes package list
class ProfileDetailSchema(ProfileSummarySchema):
    packages: list[PackageSpecSchema]
    created_at, updated_at
```

### Profile Filtering (API Query Params)

| Param | Type | Example |
|-------|------|---------|
| `tags` | `list[str]` | `?tags=gpu&tags=cuda` |
| `os` | `str` | `?os=LINUX` |
| `cuda_required` | `bool` | `?cuda_required=true` |
| `page` | `int` | `?page=2` |
| `limit` | `int` | `?limit=10` |

### Implementation Notes
- Profiles stored in PostgreSQL, seeded from `seeds/profiles.yaml` (idempotent)
- Eager loading via SQLAlchemy `selectinload` for packages — avoids N+1 queries
- Soft-delete: `deleted_at` column; never hard-deleted
- Profile resolution always uses the Compatibility Engine — no hardcoded versions in templates
- Profiles are versioned; old profiles deprecated (`status = "DEPRECATED"`), not deleted

---

## Feature 2: Script Generation

### Status: ✅ Implemented (Phase 1)

**Implementation**: `backend/app/services/script_service.py`, `backend/app/templates/`
**API**: `POST /api/v1/scripts/generate`, `GET /api/v1/scripts/{job_id}/download`

### Output Artifacts (All Implemented)

| File | Template | Description |
|------|----------|-------------|
| `setup.sh` | `setup/setup_linux.sh.j2` | Bash script for Linux/WSL |
| `setup.ps1` | `setup/setup_windows.ps1.j2` | PowerShell script for Windows |
| `requirements.txt` | `config/requirements.j2` | pip requirements with pinned versions |
| `Dockerfile` | `config/dockerfile.j2` | Containerized environment |
| `devcontainer.json` | `config/devcontainer.j2` | VS Code Dev Container config |
| `verify_torch.sh` | `verify/verify_torch.sh.j2` | PyTorch CUDA verification |
| `environment.yml` | `config/environment.yml.j2` | Conda environment export |

### Generation Pipeline (Implemented)

```
POST /api/v1/scripts/generate
          │
          ▼
ProfileService.get_profile_by_slug()
          │
          ▼ (profile not found → 404)
CompatibilityResolver.resolve()
  ├── Validate OS support
  ├── Validate CUDA version (against CUDA matrix)
  ├── Validate Python version (against framework matrix)
  ├── Apply user overrides (validated)
  └── Collect OS-specific warnings
          │
          ▼ (incompatibility → 409 with structured error)
TemplateContext.build()
          │
          ▼
TemplateRenderer.render_all(output_formats)
  └── SafetyFilter.validate(rendered_output)  ← blocks 15 dangerous patterns
          │
          ▼
ScriptGenerationJob + GeneratedScript persisted to DB
          │
          ▼
GenerationResponse {
  job_id, status, resolved_packages[],
  scripts[{filename, content, size_bytes}],
  warnings[], download_url
}
```

### API Request / Response

```json
// POST /api/v1/scripts/generate
{
  "profile_id": "pytorch-cuda",
  "target_os": "LINUX",
  "python_version": "3.11",
  "cuda_version": "11.8",
  "overrides": { "torch": "2.2.2" },
  "output_formats": ["setup.sh", "requirements.txt", "Dockerfile"]
}

// 201 Created
{
  "job_id": "uuid",
  "status": "completed",
  "profile_slug": "pytorch-cuda",
  "resolved_packages": [{ "name": "torch", "version": "2.2.2", "cuda_variant": "cu118" }],
  "scripts": [{ "filename": "setup.sh", "content": "...", "size_bytes": 2048 }],
  "warnings": ["WSL2 GPU access requires NVIDIA drivers on Windows host."],
  "download_url": "/api/v1/scripts/{job_id}/download"
}
```

### Error Responses (Structured)

| Scenario | HTTP | Error Code |
|----------|------|-----------|
| Profile not found | 404 | `PROFILE_NOT_FOUND` |
| OS not supported by profile | 409 | `UNSUPPORTED_OS` |
| CUDA version not in matrix | 409 | `INCOMPATIBLE_VERSIONS` |
| Python version incompatible | 409 | `INCOMPATIBLE_VERSIONS` |
| Package override incompatible | 409 | `INCOMPATIBLE_VERSIONS` |

### Safety Rules (Implemented in `templates/safety.py`)
All 15 patterns are blocked and raise `SafetyViolationError`:

| Pattern | Example Blocked |
|---------|----------------|
| Recursive root delete | `rm -rf /` |
| Home directory delete | `rm -rf $HOME`, `rm -rf ~` |
| Filesystem format | `mkfs.ext4`, `format C:` |
| Fork bomb | `:(){:|:&};:` |
| Raw disk write | `dd if=...`, `> /dev/sda` |
| Curl-pipe-shell | `curl url \| bash` |
| Eval subshell | `eval $(...)` |
| SQL destruction | `DROP DATABASE`, `DROP TABLE` |
| System shutdown | `shutdown /s`, `shutdown -h` |
| Base64 decode-exec | `base64 --decode \| sh` |

> **Note (v0.3.0):** The root-delete pattern uses a negative lookahead `(?!\w)` to
> avoid false positives on standard Docker cleanup commands like
> `rm -rf /var/lib/apt/lists/*`. See [ADR-008](./decisions/ADR-008-safety-filter-negative-lookahead.md).

### Download
`GET /api/v1/scripts/{job_id}/download` returns a `.zip` bundle containing all
generated scripts plus a `MANIFEST.txt` with job metadata.

---

## Feature 3: Local Diagnostic Agent

### Status: 🔲 Planned (Phase 2)

**Note**: The backend `POST /api/v1/diagnose` endpoint is implemented and accepts
`DiagnosticReport` JSON. The CLI agent that produces this JSON is a Phase 2 deliverable.

### Backend Schema (Implemented)

The `DiagnosticReportSchema` Pydantic model defines the expected JSON structure:

```python
class DiagnosticReportSchema(BaseModel):
    agent_version: str
    os: OSInfo          # name, version, architecture, wsl_version
    cpu: CPUInfo        # brand, cores, threads
    ram: RAMInfo        # total_gb, available_gb
    gpus: list[GPUInfo] # name, vram_gb, driver_version
    cuda: CUDAInfo      # version, toolkit_path, cudnn_version
    python_installations: list[PythonInfo]
    active_python: PythonInfo | None
```

### CLI Interface (Planned — Phase 2)
```bash
envforge diagnose [--output FILE] [--send]
envforge verify   [--profile PROFILE_ID]
envforge fix      [--report FILE]
```

### Diagnosis Endpoint (Implemented)

`POST /api/v1/diagnose` accepts a `DiagnosticReportSchema` body and returns:
- List of compatible profile slugs
- List of `CompatibilityIssue` objects with severity, message, and fix suggestion
- Recommendations (profile + CUDA version)

> **Phase 2 NOTE**: Current diagnosis logic is a stub that checks CUDA version
> presence only. Full multi-profile compatibility analysis is a Phase 2 deliverable.

---

## Feature 4: Environment Verification

### Status: 🔲 Planned (Phase 5)

**Prerequisite**: CLI Agent (Phase 2) must be implemented first.

### Planned Checks

| Check | Method |
|-------|--------|
| TensorFlow GPU | `tf.config.list_physical_devices('GPU')` |
| PyTorch CUDA | `torch.cuda.is_available()` |
| cuDNN version | cuDNN version API |
| CUDA version match | Compare reported vs. framework expected |
| pip conflicts | `pip check` output parsing |
| Missing dependencies | Import-based verification |

**Note**: `verify_torch.sh.j2` template is already implemented in Phase 1
and can be generated. The `POST /api/v1/verify` endpoint and full integration
are Phase 5 deliverables.

---

## Feature 5: AI Troubleshooting Layer

### Status: 🔶 In Progress (Phase 4)

**Implemented files**:
- `backend/app/ai/models.py` — `SuggestedFix`, `TroubleshootResponse` Pydantic models
- `backend/app/ai/providers/base.py` — `LLMProvider` ABC + `LLMProviderError`
- `backend/app/ai/providers/mock.py` — deterministic `MockProvider` for testing
- `backend/app/ai/providers/openrouter.py` — `OpenRouterProvider` (async HTTP, JSON mode, retry, Pydantic parsing)
- `backend/app/ai/providers/__init__.py` — `get_provider()` factory function
- `backend/app/ai/prompts/system.py` — System prompt constants with safety rules and repair template IDs
- `backend/app/ai/prompts/troubleshoot.py` — `TroubleshootPromptBuilder` (diagnostic → LLM user message)
- `backend/app/ai/service.py` — `AITroubleshootService` orchestrator (pipeline: prompt → LLM → safety → persist)
- `backend/app/api/v1/troubleshoot.py` — `POST /api/v1/troubleshoot` endpoint
- `backend/app/services/repair_service.py` — `RepairService` (template ID → rendered repair script)
- `backend/app/api/v1/repair.py` — `POST /api/v1/repair` + `GET /api/v1/repair/templates`
- `backend/app/templates/jinja/repair/` — 5 repair Jinja2 templates (CUDA upgrade, Python install, driver update, venv recreate, pip reinstall)
- `backend/app/schemas/ai.py` — API-layer Pydantic schemas for AI endpoints
- `frontend/src/types/index.ts` — AI TypeScript interfaces (TroubleshootRequest, SuggestedFix, RepairResponse, etc.)
- `frontend/src/services/api.ts` — `troubleshoot()`, `generateRepair()`, `getRepairTemplates()` API methods
- `frontend/src/app/troubleshoot/page.tsx` — AI Troubleshoot page (diagnostic input, fix cards, repair scripts)
- `backend/app/middleware/rate_limit.py` — Sliding-window rate limiter (in-memory, Redis-swappable)

### AI Provider Interface

```python
class LLMProvider(ABC):
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],  # Always a Pydantic model — never raw text
    ) -> T: ...
```

### Provider Implementations

| Provider | Status | Model | Notes |
|----------|--------|-------|-------|
| `MockProvider` | ✅ Implemented | — | Deterministic responses for testing |
| `OpenRouterProvider` | ✅ Implemented | Configurable (default: `meta-llama/llama-3-8b-instruct:free`) | Routes to 100+ models via OpenRouter API. See [ADR-009](./decisions/ADR-009-openrouter-primary-gateway.md). |
| `OpenAIProvider` | 🔲 Planned | GPT-4o | Use OpenRouter with `openai/gpt-4o` model instead |
| `OllamaProvider` | 🔲 Planned | Local Llama 3 | No data leaves device |

### Provider Factory

The active provider is selected by `ENVFORGE_LLM_PROVIDER` env var and instantiated via `get_provider()`:

```python
from app.ai.providers import get_provider
provider = get_provider()  # Returns configured LLMProvider instance
result = await provider.complete(system_prompt, user_msg, TroubleshootResponse)
```

### Hard Safety Rules (Enforced in Phase 4)
- AI output is ALWAYS passed through `SafetyFilter` before exposure
- AI may NOT generate destructive commands (`rm -rf`, `format`, `DROP TABLE`, etc.)
- AI suggestions are rendered via Jinja2 templates, NOT raw LLM text
- All AI calls include a system prompt enforcing structured JSON output only

---

## Feature 6: Web Application (Frontend)

### Status: ✅ Implemented (Phase 3)

**Implementation**: `frontend/src/`
**Framework**: Next.js 14+ App Router, TypeScript, TailwindCSS

### Capabilities
- **Profile Browser**: View available environment profiles, packages, and descriptions. Includes null-safe rendering for optional fields.
- **Script Generation Wizard**: A multi-step form to configure target OS, output formats, Python, and CUDA versions. Validates selections dynamically based on the chosen profile. See [ADR-007](./decisions/ADR-007-dynamic-ui-compatibility-fields.md).
- **Diagnostic Dashboard**: Paste CLI agent JSON output to visualize hardware (OS, CPU, GPU, CUDA), run compatibility checks against any profile, and view structured issues with severity badges and suggested fixes. Compatible profiles are rendered as clickable links to the Script Wizard.
- **API Integration**: Connects securely to the FastAPI backend (`/api/v1`). All TypeScript interfaces are strictly aligned with backend Pydantic schemas.
- **Deployment**: Configured for Vercel production deployment with proper `NEXT_PUBLIC_API_URL` configuration.

---

## Feature 7: Production Infrastructure

### Status: ✅ Implemented (Phase 6)

**Files**: `docker-compose.prod.yml`, `backend/app/middleware/rate_limit.py`,
`backend/app/config.py`, `.env.prod`

### Components

| Component | Implementation |
|-----------|---------------|
| Production Compose | `docker-compose.prod.yml` — PostgreSQL 16, Redis 7, FastAPI API |
| Redis Rate Limiter | `RedisBackend` in `rate_limit.py` — sliding window via sorted set |
| Config | `redis_url` field added to `Settings`; optional, defaults to `None` |
| Secrets Template | `.env.prod` — all secrets via env vars, never hardcoded |

### Design Decisions
- DB and Redis ports are **not** exposed in production — only reachable inside
  the Compose network.
- `RedisBackend` is auto-selected when `REDIS_URL` is set. No code changes
  needed in dev — `InMemoryBackend` remains the default.
- `--reload` removed in production; `--workers 2` used instead.
- Rate limit correctness across multiple workers requires Redis — in-memory
  state is per-process and would allow 2× the intended limit with 2 workers.

---

## Future Features (Backlog)

- Multi-user workspace support (saved profiles, history)
- Profile comparison view
- Custom profile builder (drag-and-drop package selection)
- ONNX / TensorRT profile support
- ROCm (AMD GPU) profile support
- Integration with Conda environments
- GitHub Action: `envforge verify` in CI pipeline
- Automatic compatibility matrix updates from official release feeds
