# EnvForage — Template System Design

> **Version**: 2.0.0
> **Status**: Production
> **Last Updated**: 2026-06-18

---

## Purpose

The Template System is responsible for rendering setup scripts and configuration
files from validated `EnvironmentProfile` + `ResolvedEnvironment` data. It uses
Jinja2 as the template engine.

Templates are:
- **Version-pinned**: No `latest` tags, no floating versions
- **Safe**: No destructive commands; no `rm -rf`, `format`, `DROP TABLE`
- **Readable**: Templates should be easy for contributors to understand and edit
- **Testable**: Every template has a corresponding rendering test

---

## Template Types

| Template | Output File | Target OS |
|----------|-------------|-----------|
| `setup_linux.sh.j2` | `setup.sh` | Linux, WSL |
| `setup_windows.ps1.j2` | `setup.ps1` | Windows |
| `requirements.j2` | `requirements.txt` | All |
| `dockerfile.j2` | `Dockerfile` | All (containerized) |
| `devcontainer.j2` | `devcontainer.json` | VS Code Dev Containers |
| `verify_torch.sh.j2` | `verify.sh` | Linux/WSL (PyTorch) |
| `verify_tf.sh.j2` | `verify.sh` | Linux/WSL (TensorFlow) |

---

## Template Context Model

All templates receive a `TemplateContext` object:

```python
class TemplateContext(BaseModel):
    profile: EnvironmentProfile
    resolved: ResolvedEnvironment
    target_os: OSTarget
    generated_at: datetime
    envforage_version: str
    warnings: list[str]
```

`ResolvedEnvironment` contains the final, validated package list with pinned versions.

---

## Template Structure

### `setup_linux.sh.j2` (Skeleton)

```jinja2
#!/bin/bash
# ============================================================
# EnvForage Generated Setup Script
# Profile  : {{ profile.name }}
# OS Target: Linux / WSL
# Generated: {{ generated_at.strftime('%Y-%m-%d %H:%M UTC') }}
# EnvForage : v{{ envforage_version }}
# WARNING  : Do not modify — regenerate from EnvForage instead
# ============================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ---- Pre-flight checks ----
check_command() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "ERROR: $1 is required but not installed." >&2
        exit 1
    }
}
check_command python3
check_command pip3

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$PYTHON_VERSION" != "{{ resolved.python_version }}" ]]; then
    echo "ERROR: Python {{ resolved.python_version }} required. Found: $PYTHON_VERSION"
    exit 1
fi

# ---- Package Installation ----
pip3 install \
{%- for pkg in resolved.packages %}
    {{ pkg.name }}=={{ pkg.version }} \
{%- endfor %}

echo "✓ EnvForage setup complete for profile: {{ profile.name }}"
```

### `requirements.j2` (Skeleton)

```jinja2
# ============================================================
# EnvForage Generated requirements.txt
# Profile  : {{ profile.name }}
# Generated: {{ generated_at.strftime('%Y-%m-%d') }}
# ============================================================

{%- for pkg in resolved.packages %}
{{ pkg.name }}=={{ pkg.version }}
{%- endfor %}
```

---

## Safety Rules (Enforced at Render Time)

The `TemplateRenderer` validates rendered output before returning it:

```python
FORBIDDEN_PATTERNS = [
    r"rm\s+-rf\s+/",         # Never rm -rf /
    r"format\s+[A-Z]:",      # Never format drives (Windows)
    r"DROP\s+TABLE",          # Never SQL destructive ops
    r"mkfs\.",                # Never filesystem format
    r":(){:|:&};:",           # Fork bomb pattern
]
```

If any forbidden pattern is detected in the rendered output, rendering raises
`UnsafeTemplateError` and the script is NOT returned to the client.

---

## Module Structure (Planned)

```
backend/
└── app/
    └── templates/
        ├── engine.py              # TemplateRenderer class
        ├── safety.py              # Safety filter & forbidden patterns
        ├── models.py              # TemplateContext, RenderResult
        ├── jinja/                 # Jinja2 template files
        │   ├── setup/
        │   │   ├── setup_linux.sh.j2
        │   │   ├── setup_windows.ps1.j2
        │   │   └── setup_macos.sh.j2   (future)
        │   ├── config/
        │   │   ├── requirements.j2
        │   │   ├── dockerfile.j2
        │   │   └── devcontainer.j2
        │   └── verify/
        │       ├── verify_torch.sh.j2
        │       ├── verify_tf.sh.j2
        │       └── verify_opencv.sh.j2
        └── tests/
            ├── test_engine.py
            ├── test_safety.py
            └── snapshots/          # Expected rendered outputs for snapshot tests
```

---

## Rendering Pipeline

```
GenerationRequest
       │
       ▼
CompatibilityEngine.resolve() → ResolvedEnvironment
       │
       ▼
TemplateContext.build()
       │
       ▼
TemplateRenderer.render(template_name, context)
       │
       ├── Jinja2 Environment.get_template()
       ├── template.render(context.dict())
       ├── SafetyFilter.validate(rendered_output)  ← raises UnsafeTemplateError if fails
       │
       ▼
RenderResult { filename, content, warnings }
       │
       ▼
ZipBundler.bundle([render_results]) → bytes
       │
       ▼
API returns download URL
```

---

## Template Variables Reference

| Variable | Type | Description |
|----------|------|-------------|
| `profile.name` | str | Human-readable profile name |
| `profile.id` | str | Profile slug |
| `resolved.python_version` | str | e.g., `"3.11"` |
| `resolved.cuda_version` | str | e.g., `"12.1"` |
| `resolved.packages` | list | `[{name, version}]` |
| `target_os` | OSTarget | `LINUX`, `WSL`, `WIN` |
| `generated_at` | datetime | UTC generation timestamp |
| `envforage_version` | str | EnvForage version |
| `warnings` | list[str] | Non-fatal compatibility warnings |

---

## Snapshot Testing

Every template must have snapshot tests:
1. Render with a known `TemplateContext`
2. Compare output to stored snapshot
3. If snapshot changes, contributor must explicitly approve the diff

This prevents silent regressions in generated script content.

---

## Future Improvements

- Template marketplace: community-contributed templates
- Template preview API endpoint (`POST /templates/preview`)
- YAML-based template metadata (tags, OS support, required vars)
- Conda `environment.yml` output format
- Makefile output for complex multi-step setups
