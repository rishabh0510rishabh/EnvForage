# Script Generation — Feature Deep-Dive

> **Feature**: Script Generation
> **Status**: ✅ Implemented (Phase 1)
> **Last Updated**: 2026-05-06

---

## Purpose

Script generation is the core output of EnvForage. Given a user's selected
environment profile and target configuration, EnvForage generates a set of
downloadable, ready-to-run scripts that provision a compatible ML environment.

Scripts are:
- **Version-pinned**: Every package is an exact version — no `latest` or floating ranges
- **Pre-flight checked**: Scripts verify prerequisites before installing anything
- **Safety-filtered**: 15 forbidden shell patterns are blocked at render time
- **Auditable**: Every generation job is persisted to the database

---

## Architecture

```
API Layer (thin controller)
        │ GenerationRequest (Pydantic, validated)
        ▼
ProfileService.get_profile_by_slug()
        │ EnvironmentProfile + PackageConstraints
        ▼
CompatibilityResolver.resolve()
        │ ResolvedEnvironment { packages[], python_version, cuda_version, warnings[] }
        ▼
TemplateContext.build()
        │
        ▼
TemplateRenderer.render_all(output_formats)
        │
        ├── For each format:
        │     Jinja2 Environment.get_template(template_path)
        │     template.render(**context.to_dict())
        │     SafetyFilter.validate(rendered_content)  ← raises SafetyViolationError if blocked
        │
        ▼
ScriptGenerationJob + GeneratedScript persisted to PostgreSQL
        │
        ▼
GenerationResponse { job_id, scripts[], resolved_packages[], warnings[], download_url }
```

---

## Key Files

| File | Responsibility |
|------|---------------|
| `app/api/v1/scripts.py` | Route handler (thin) — validates request, calls service |
| `app/services/script_service.py` | Orchestration — chains resolver → renderer → DB |
| `app/compatibility/resolver.py` | Pure version resolution logic |
| `app/templates/engine.py` | Jinja2 template rendering |
| `app/templates/safety.py` | Forbidden pattern safety filter |
| `app/templates/models.py` | `TemplateContext`, `RenderResult` |
| `app/schemas/script.py` | `GenerationRequest`, `GenerationResponse` |
| `app/models/script_job.py` | ORM: `ScriptGenerationJob`, `GeneratedScript` |

---

## Template Map

| User requests | Template file | Description |
|---|---|---|
| `"setup.sh"` | `jinja/setup/setup_linux.sh.j2` | Bash for Linux/WSL |
| `"setup.ps1"` | `jinja/setup/setup_windows.ps1.j2` | PowerShell for Windows |
| `"requirements.txt"` | `jinja/config/requirements.j2` | pip requirements |
| `"Dockerfile"` | `jinja/config/dockerfile.j2` | Docker image |
| `"devcontainer.json"` | `jinja/config/devcontainer.j2` | VS Code dev container |
| `"verify_torch.sh"` | `jinja/verify/verify_torch.sh.j2` | PyTorch CUDA check |

---

## Template Context Variables

All Jinja2 templates receive these variables via `TemplateContext.to_dict()`:

| Variable | Type | Example |
|----------|------|---------|
| `profile.id` | `str` | `"pytorch-cuda"` |
| `profile.name` | `str` | `"PyTorch CUDA"` |
| `python_version` | `str` | `"3.11"` |
| `cuda_version` | `str \| None` | `"11.8"` or `None` |
| `target_os` | `str` | `"LINUX"` |
| `packages[]` | `list[dict]` | `[{name, version, cuda_variant, pip_spec}]` |
| `packages[].pip_spec` | `str` | `"torch==2.1.2+cu118"` |
| `warnings[]` | `list[str]` | `["WSL2 requires host NVIDIA driver"]` |
| `generated_at` | `str` | `"2026-05-06 14:30 UTC"` |
| `envforage_version` | `str` | `"1.0.0"` |

---

## Safety Filter

**File**: `app/templates/safety.py`

Every rendered template output is scanned before being returned to the client.
If any forbidden pattern is matched, `SafetyViolationError` is raised and
the script is **not** returned.

```python
FORBIDDEN_PATTERNS = [
    (r"rm\s+-[rRf]{1,3}\s+/",          "Recursive delete of root"),
    (r"rm\s+-[rRf]{1,3}\s+\$HOME",      "Recursive delete of home"),
    (r"rm\s+-[rRf]{1,3}\s+~",           "Recursive delete (tilde)"),
    (r"mkfs\.",                          "Filesystem format"),
    (r"format\s+[A-Za-z]:",             "Windows drive format"),
    (r":(\s*)\(\s*\)\s*\{.*\|.*&",      "Fork bomb"),
    (r"dd\s+if=",                        "Raw disk write"),
    (r">\s*/dev/sd[a-z]",               "Direct disk overwrite"),
    (r"shutdown\s+(/s|/r|-h|-r)",       "System shutdown"),
    (r"DROP\s+DATABASE",                 "SQL DB destruction"),
    (r"DROP\s+TABLE",                    "SQL table destruction"),
    (r"TRUNCATE\s+TABLE",               "SQL table truncation"),
    (r"curl\s+.*\|\s*(ba)?sh",          "Curl-pipe-to-shell"),
    (r"wget\s+.*-O-\s*\|\s*(ba)?sh",   "Wget-pipe-to-shell"),
    (r"eval\s+\$\(",                     "Eval of subshell"),
    (r"base64\s+--decode\s*\|.*sh",    "Base64 decode-exec"),
]
```

> **To add a new forbidden pattern**: Add to `FORBIDDEN_PATTERNS` in `safety.py`
> AND add a corresponding test in `tests/unit/templates/test_safety.py`.

---

## Error Handling

All errors are returned as structured JSON, never plain text:

```json
// 409 INCOMPATIBLE_VERSIONS
{
  "error": {
    "code": "INCOMPATIBLE_VERSIONS",
    "component": "cuda",
    "constraint": "torch 2.1.0 supports CUDA: 11.8, 12.1",
    "detected": "CUDA 12.4",
    "suggestion": "Use CUDA 12.1 or select torch 2.4.0",
    "docs_url": "https://pytorch.org/get-started/locally/"
  }
}

// 409 UNSUPPORTED_OS
{
  "error": {
    "code": "UNSUPPORTED_OS",
    "message": "Profile 'pytorch-cuda' does not support OS 'WIN'. Supported: LINUX, WSL",
    "details": { "profile": "pytorch-cuda", "requested_os": "WIN", "supported_os": ["LINUX", "WSL"] }
  }
}
```

---

## Database Persistence

Every generation job is persisted regardless of success/failure:

```
script_generation_jobs (one per API call)
    │
    └── generated_scripts (one per output format)
```

**Retention policy**: Jobs are retained for 30 days (Phase 6 cleanup job).
**Download URL**: `GET /api/v1/scripts/{job_id}/download` returns a ZIP with all scripts
and a `MANIFEST.txt` containing job metadata.

---

## Adding a New Template (Contributor Guide)

1. Create `backend/app/templates/jinja/<category>/<name>.j2`
2. Add entry to `TEMPLATE_MAP` in `app/templates/engine.py`
3. Add at minimum one test in `tests/unit/templates/` with snapshot comparison
4. Document the new template in this file and in `docs/TEMPLATE_SYSTEM.md`
5. If the template is for a new output format, add it to `OutputFormat` in `app/schemas/script.py`

---

## Future Improvements

- Snapshot tests for all templates (ensure rendered output doesn't silently change)
- Template preview endpoint: `POST /api/v1/templates/preview` (returns rendered content without persisting)
- `Makefile` output format for complex multi-step setups
- Conda `environment.yml` output format
- Streaming script delivery (Server-Sent Events for large bundles)
