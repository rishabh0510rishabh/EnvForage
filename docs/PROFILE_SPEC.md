# Environment Profile Specification

This document explains how to construct an ML Environment Profile for EnvForage.

Profiles are stored as YAML in `backend/seeds/profiles.yaml` and loaded into the PostgreSQL database on startup.

## Profile Structure

A complete profile definition looks like this:

```yaml
- slug: "pytorch-cuda"
  name: "PyTorch CUDA"
  description: "Standard PyTorch environment with CUDA acceleration."
  tags: ["machine-learning", "pytorch", "gpu"]
  os_support: ["LINUX", "WSL"]
  cuda_required: true
  python_versions: ["3.10", "3.11", "3.12"]
  cuda_versions: ["11.8", "12.1", "12.4"]
  status: "ACTIVE"
  packages:
    - name: "torch"
      version: "2.1.2"
      is_core: true
      cuda_variant_required: true
    - name: "torchvision"
      version: "0.16.2"
      is_core: false
      cuda_variant_required: true
```

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `string` | Unique identifier (e.g., `tf-gpu`, `yolov8`). Used in API requests. |
| `name` | `string` | Human-readable display name. |
| `description` | `string` | Brief explanation of what the profile is for. |
| `tags` | `list[string]` | Searchable keywords (e.g., `gpu`, `llm`, `audio`). |
| `os_support` | `list[string]` | Allowed OS targets. Valid: `LINUX`, `WSL`, `WIN`. |
| `cuda_required` | `boolean` | If `true`, generation fails if no CUDA version is detected/specified. |
| `python_versions` | `list[string]` | Supported minor versions. E.g., `["3.10", "3.11"]`. |
| `cuda_versions` | `list[string]` | Supported CUDA toolkits. Can be `null` if `cuda_required` is `false`. |
| `status` | `string` | `ACTIVE` or `DEPRECATED`. |

### Package Definitions

The `packages` list defines the dependencies to install.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | PyPI package name (e.g., `torch`, `tensorflow`). |
| `version` | `string` | Exact version constraint (e.g., `2.1.2`). No floating `latest` allowed. |
| `is_core` | `boolean` | `true` if this package defines the environment's primary framework. |
| `cuda_variant_required` | `boolean` | `true` if the pip install string requires a CUDA suffix (e.g., `+cu118`). Handled by the Compatibility Engine. |

## Adding a New Profile

1. Add your YAML block to `backend/seeds/profiles.yaml`.
2. Ensure the combination of Framework + CUDA + Python versions exists in the Compatibility Matrix (`backend/seeds/cuda_matrix.yaml` or `app/compatibility/matrix/`).
3. Run the profile validation script to check for schema and logical errors:
   ```bash
   python -m scripts.validate_profiles backend/seeds/profiles.yaml
   ```
4. Run `python -m app.services.seed_service` to ingest the new profile into your local dev database.
