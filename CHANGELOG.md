# Changelog
 
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
 
## [Unreleased]
 

## [1.0.2] - 2026-06-02

### Added
- **Vercel Speed Insights**: Added Vercel speed insights to the frontend.
- **WSL2 Diagnostics**: Add WSL2 GPU passthrough diagnostics and warning before provisioning.
- **Dynamic Versioning**: Use dynamic version string from `__init__.py` for the CLI agent to prevent PyPI publish errors.

### Fixed
- **Backend Error**: Resolved backend production errors.
- **Profiles Metadata**: Fixed null metadata handling in profiles.

## [1.0.1] - 2026-05-30

### Added
- **Frontend Containerization & Orchestration:**
  - Added a multi-stage `Dockerfile` and `.dockerignore` for the Next.js frontend application.
  - Configured Next.js standalone output mode in `next.config.ts` for optimized production container execution.
  - Integrated the containerized frontend into `docker-compose.yml` (development) and `docker-compose.prod.yml` (production).
  - Updated the GitHub release workflow (`release.yml`) to build and push the frontend image to GitHub Container Registry on tag releases.
- **uv Package Manager Support:**
  - Added `use_uv` boolean field to `GenerationRequest` schema — when `true`, generated scripts bootstrap and use `uv` instead of `pip` for significantly faster package installation.
  - Updated `setup_windows.ps1.j2` to bootstrap `uv` via `Invoke-RestMethod` and conditionally use `uv pip install`.
  - Updated `setup_linux.sh.j2` to bootstrap `uv` via `curl` and conditionally use `uv pip install` across all install paths (CUDA, non-CUDA, CPU-only).
### Added
- **Helm Chart for Kubernetes Deployment:**
  - Added `helm/envforge/` chart with templates for backend Deployment, Redis Deployment, Services, Ingress, and ConfigMap.
  - Parameterized via `values.yaml` — image, ports, replicas, env vars, and Redis config are all overridable.
  - Non-root `securityContext` (`runAsNonRoot: true`) applied to backend Deployment, consistent with Dockerfile hardening.
  - Liveness and readiness probes configured on `/health`.
### Fixed
- **Unbounded String Fields in Diagnostic Schema (`schemas/diagnostic.py`):**
  - String fields in the diagnostic report schema accepted values with no upper length bound. Because these reports are persisted to PostgreSQL (including denormalized `VARCHAR` columns) and processed through Pydantic validation/serialization, oversized values from a malicious client or buggy agent could fail at persist time, cause memory pressure, or pollute logs.
  - Added `max_length` constraints to the affected fields: `OSInfo.name` (128), `OSInfo.version` (32), `OSInfo.architecture` (32), `CPUInfo.brand` (256), `GPUInfo.name` (256), `GPUInfo.driver_version` (32), `PythonInfo.version` (20), and `PythonInfo.path` (512). Oversized values are now rejected with a `422` at the API boundary instead of reaching the database.
  - Added 18 unit tests in `test_diagnostic_schema.py` covering boundary-length acceptance, over-length rejection (`string_too_long`), preservation of the optional `driver_version` default, and acceptance of representative real-world values. (#439)
- **Rate Limiter Redis Fallback (`rate_limit.py`):**
  - Redis `ConnectionError` or `TimeoutError` during `RedisBackend.is_allowed()` previously bubbled up as an unhandled exception, causing a **500 Internal Server Error** on every rate-limited endpoint while Redis was unreachable.
  - `RateLimiter.__call__` now catches these errors, logs a `WARNING`, and transparently falls back to a shared `_fallback_backend` (`InMemoryBackend`) singleton so requests continue to be served.
  - `redis.exceptions` is imported lazily to keep the module functional in InMemoryBackend-only deployments where the `redis` package is not installed.
  - Non-Redis exceptions are re-raised so unrelated bugs are not silently swallowed.
  - Added 4 unit tests in `test_rate_limit.py` covering `ConnectionError` fallback, `TimeoutError` fallback, non-Redis re-raise, and verifying the request is allowed (not 429) after fallback.
## [1.0.0] - 2026-05-22
 
### Added
- **v1.0.0 Stable Release.**
  - Official launch of the stable `v1.0.0` release of the EnvForge platform, consolidating all CLI, backend, frontend, and AI troubleshooting features.
  - End-to-end integration of AI-assisted environment troubleshooting, system diagnostic reporting, and custom shell setup script generation.
- **Conda Environment Configuration:**
  - Added support for generating and exporting `environment.yml` files for Anaconda/Miniconda envs.
- **Security Hardening & Code Scanning:**
  - Integrated GitHub CodeQL static analysis workflows to automatically scan Python (backend/CLI) and JavaScript/TypeScript (frontend) code for vulnerabilities.
  - Configured Dependabot for automated weekly updates to node modules, Python pip dependencies, and GitHub Actions.
  - Added pre-commit security hooks to check for private keys, large files, and merge conflicts locally.
### Fixed
- **Frontend Build & Compilation Stability:**
  - Resolved all compilation, type, and linting errors across the Next.js frontend application.
  - Fixed TypeScript compiler errors in `generate/page.tsx` related to `cuda_versions` and `python_versions` arrays possibly being undefined.
  - Resolved ESLint unused variable warnings in `api.ts`, `troubleshoot/page.tsx`, and `diagnose/page.tsx`.
  - Moved nested components in `troubleshoot/page.tsx` to the file-level scope to satisfy React 19/Next.js 16 rules.
  - Fixed Next.js client hydration and theme synchronization warnings in `providers.tsx` by declaring `applyTheme` before utilization and configuring appropriate suppression.
  - Replaced native `<a>` elements with Next.js client-side `<Link>` tags across the layout.
- **CLI Output Flag Testing:**
  - Integrated unit tests for the CLI `diagnose --output` parameter to ensure correct file generation formatting.
## [0.5.0] - 2026-05-16
 
### Added
- **Phase 6 — Production Infrastructure.**
  - `docker-compose.prod.yml`: production Compose with PostgreSQL, Redis, and
    the FastAPI API service. DB and Redis ports not exposed to host. All secrets
    via env vars. Services use `restart: always` and healthchecks.
  - `RedisBackend` in `rate_limit.py`: implements `RateLimitBackend` ABC using
    a Redis sorted set (sliding window). Auto-selected when `REDIS_URL` is set,
    falls back to `InMemoryBackend` in development. Fixes rate limit correctness
    across multiple uvicorn workers.
  - `redis_url` config field in `config.py`: optional (`None` by default),
    no changes required to existing dev/test environments.
  - `.env.prod` template for production secrets.
### Fixed
- `FRAMEWORK_CUDA_SUPPORT["tensorflow"]["2.15.0"]` corrected from `"12.1"` to
  `"12.2"` — TF 2.15 ships with CUDA 12.2, not 12.1.
- `PYTHON_MATRIX["tensorflow"]["2.15.0"]["supported_cuda"]` corrected to match.
### Added (Compatibility Matrix)
- CUDA 12.2 and 12.3 entries added to `CUDA_MATRIX` and `cuda_matrix.yaml`.
- TF 2.16.0, 2.16.1, 2.17.0, 2.18.0 added to `FRAMEWORK_CUDA_SUPPORT` and
  `PYTHON_MATRIX` with CUDA 12.3 and Python 3.9–3.12 support.
  Resolves TODO left in Phase 1.
## [0.4.0] - 2026-05-14
 
### Added
- **Phase 4 — Part 1**: OpenRouter LLM Provider.
  - `OpenRouterProvider` class implementing `LLMProvider` ABC with async HTTP, JSON mode enforcement, exponential backoff retry (3 attempts), Pydantic response parsing, and token usage tracking.
  - Provider factory `get_provider()` — reads `ENVFORGE_LLM_PROVIDER` env var and instantiates the correct provider with lazy imports.
  - New config fields: `ai_max_tokens` (default 2048), `ai_temperature` (default 0.3).
  - ADR-009: OpenRouter as Primary LLM Gateway.
- **Phase 4 — Part 2**: Prompt Engineering System.
  - System prompt constants with non-negotiable safety rules, JSON-only output enforcement, and available repair template IDs.
  - `TroubleshootPromptBuilder` class — converts DiagnosticReport + profile context into structured LLM user messages with CUDA matrix injection and prompt injection sanitisation.
  - `TroubleshootRequest` Pydantic model — structured input contract for the AI troubleshoot endpoint.
  - `LLMResponseMeta` model for audit logging (provider, model, token usage).
- **Phase 4 — Part 3**: Troubleshoot Service + API Endpoint.
  - `AITroubleshootService` orchestrator — full pipeline: prompt build → LLM call → safety filter → DB persist → audit log.
  - `POST /api/v1/troubleshoot` endpoint with structured error handling (503 for LLM errors, 500 for safety violations).
  - Registered troubleshoot router in FastAPI app.
- **Phase 4 — Part 4**: Repair Script Generation.
  - `RepairService` — maps AI-suggested template IDs to Jinja2 repair scripts, renders with validated params, safety-filters output.
  - 5 repair Jinja2 templates: `repair_cuda_upgrade`, `repair_python_install`, `repair_driver_update`, `repair_venv_recreate`, `repair_pip_reinstall`.
  - `POST /api/v1/repair` endpoint — generates repair scripts from template ID + params.
  - `GET /api/v1/repair/templates` endpoint — lists available repair templates.
  - All repair scripts include user confirmation prompts before making changes.
- **Phase 4 — Part 5**: Frontend API Types.
  - `backend/app/schemas/ai.py` — API-layer Pydantic schemas for troubleshoot and repair endpoints.
  - `frontend/src/types/index.ts` — Added `TroubleshootRequest`, `TroubleshootResponse`, `SuggestedFix`, `RepairRequest`, `RepairResponse`, `RepairTemplateInfo` TypeScript interfaces.
  - `frontend/src/services/api.ts` — Added `troubleshoot()`, `generateRepair()`, `getRepairTemplates()` API methods with structured error handling.
- **Phase 4 — Part 6**: Frontend Chat UI.
  - `frontend/src/app/troubleshoot/page.tsx` — Full AI Troubleshoot page with:
    - Diagnostic JSON input with sample data prefill
    - Profile selector and issue description field
    - Expandable fix cards with severity badges (CRITICAL/WARNING/INFO)
    - Diagnostic command display with one-click copy
    - Repair script generation, preview, copy, and download (.sh)
    - Animated confidence bar and premium glassmorphism design
  - Added "AI Troubleshoot" nav link to global layout.
- **Phase 4 — Part 7**: Rate Limiting.
  - In-memory sliding-window rate limiter with abstract `RateLimitBackend` (swappable for Redis).
  - Pre-configured limits: AI troubleshoot (10/min), repair (20/min), general (60/min).
  - Applied to `POST /api/v1/troubleshoot` and `POST /api/v1/repair` as FastAPI dependencies.
  - Standard HTTP 429 responses with `Retry-After` header.
  - X-Forwarded-For support for proxy deployments.
  - New config fields: `rate_limit_ai_rpm`, `rate_limit_repair_rpm`, `rate_limit_general_rpm`.
- **Phase 4 — Part 8**: Tests & Integration.
  - Comprehensive unit test suite for AI components (`test_models.py`, `test_prompts.py`, `test_rate_limit.py`, `test_repair_service.py`, `test_system_prompts.py`).
  - Integration tests for the full repair pipeline (`test_ai_pipeline.py`) validating prompt generation, template rendering, and safety filter execution.
  - 100% pass rate on 66 test cases.
## [0.3.0] - 2026-05-14
 
### Added
- **Phase 3 Complete:** Next.js Frontend Web Application.
- Interactive Profile Browser displaying environment templates, capabilities, and pre-configured packages.
- Script Generation Wizard with dynamic dependency locking (Python/CUDA version auto-population based on profile restrictions).
- Diagnostic Dashboard with hardware overview cards, profile compatibility checker, structured issue rendering with severity badges, and one-click navigation to the Script Wizard.
- API client wrapper for seamless communication with the FastAPI backend.
- Vercel deployment configuration for edge-optimized hosting.
- Documentation updates for Phase 3 (Architecture, Workflows, Script Wizard Feature Doc, Diagnostic Dashboard Feature Doc).
- ADR-007: Dynamic UI Form Validation for Compatibility Engine.
- ADR-008: Safety Filter Negative Lookahead for Docker Cleanup Commands.
### Fixed
- Re-aligned frontend `PackageDef` interface with backend `PackageSpecSchema` to ensure accurate package rendering.
- Re-aligned frontend `ScriptGenerationResponse` interface — replaced stale `files_generated: string[]` with correct `scripts: ScriptPreview[]` structure to prevent `Cannot read properties of undefined` crash on results page.
- Re-aligned frontend `DiagnosticResponse` interface — replaced stale `{compatible, errors}` with correct `{report_id, compatible_profiles, issues, recommendations}` structure to match backend `DiagnoseResponse`.
- Resolved `422 Unprocessable Content` API error by adding strict `python_version` and `cuda_version` state tracking to the generation wizard.
- Fixed 500 Internal Server errors during profile fetching by enabling `from_attributes = True` on backend ORM schemas.
- Fixed Safety Filter false positive: regex `rm\s+-[rRf]{1,3}\s+/` was blocking legitimate Docker `rm -rf /var/lib/apt/lists/*` cleanup. Narrowed to `rm\s+-[rRf]{1,3}\s+/(?!\w)` using a negative lookahead.
- Fixed doubled download URL (`/api/v1/api/v1/...`) by stripping the `/api/v1` prefix from the base URL before appending the backend's `download_url`.
- Added null-safety guards for `profile.description` and `profile.tags` on the profiles listing page to prevent crashes when these optional fields are null.
- Removed trailing slashes in Vercel `NEXT_PUBLIC_API_URL` to fix `Failed to fetch` errors in production.
## [0.2.0] - 2026-05-06
 
### Added
- **Phase 2 Complete:** CLI Diagnostic Agent (`envforge-agent`).
- OS detection for Windows, Linux, and WSL2.
- GPU detection via `nvidia-smi`.
- CUDA toolkit, cuDNN, and NCCL version detection.
- Python installation scanner.
- RAM and CPU profiling.
- CLI commands: `envforge diagnose`, `envforge verify`, and `envforge fix`.
- Test suite with multi-platform fixtures.
- Documentation updates for CLI Agent deep-dive.
## [0.1.0] - 2026-05-06
 
### Added
- **Phase 1 Complete:** Core Backend implementation.
- FastAPI server with async PostgreSQL database (SQLAlchemy 2.0).
- Pure, deterministic Compatibility Engine for resolving package versions.
- Jinja2 Template Engine with a strict regex-based `SafetyFilter`.
- Generation of `setup.sh`, `setup.ps1`, `requirements.txt`, `Dockerfile`, and `devcontainer.json`.
- REST API endpoints for profiles, diagnostics, and script generation.
- Idempotent YAML seed service with 6 starter profiles (e.g., `pytorch-cuda`, `yolov8`).
- AI Layer skeleton with mock provider and Pydantic schemas.
- Comprehensive documentation suite (Architecture, ADRs, Workflows).