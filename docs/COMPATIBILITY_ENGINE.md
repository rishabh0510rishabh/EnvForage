# EnvForage — Compatibility Engine Design

> **Version**: 2.0.0
> **Status**: Production
> **Last Updated**: 2026-06-18

---

## Purpose

The Compatibility Engine is the core decision-making module of EnvForage.
It determines which package versions, CUDA versions, driver versions, and
Python versions are mutually compatible given a set of constraints.

It is:
- **Pure**: No I/O, no network calls, no side effects
- **Deterministic**: Same inputs always produce same outputs
- **Explicit**: All incompatibilities are surfaced with clear error messages
- **Tested**: 100% unit test coverage target

---

## Responsibilities

1. Resolve the best compatible set of versions for a given `EnvironmentProfile` + constraints
2. Validate user-provided version overrides against the compatibility matrix
3. Surface precise `IncompatibilityError` with actionable messages
4. Provide "what-if" queries (e.g., "Can I use PyTorch 2.2 with CUDA 11.8?")

---

## Core Data Model

### CUDA Compatibility Matrix

This matrix encodes: for a given CUDA version, what is the minimum required
NVIDIA driver version and which frameworks are supported.

```
CUDA Version → {
    min_driver_version: str,
    supported_frameworks: {
        "torch": ["2.0.x", "2.1.x"],
        "tensorflow": ["2.13.x", "2.14.x"],
        "tensorrt": ["8.6.x"],
        "cudnn": ["8.9.x", "9.0.x"]
    }
}
```

### ROCm Compatibility Matrix (NEW)

This matrix encodes: for a given ROCm version, what is the minimum required
Linux kernel/driver version and supported GCN architectures.

```
ROCm Version → {
    min_driver_linux: str,
    supported_gpus: list[str],
    supported_frameworks: {
        "torch": ["2.0.x", "2.1.x"],
        "tensorflow": ["2.13.x"]
    }
}
```

### Example Matrix (Partial, for documentation)

| CUDA | Min Driver | PyTorch | TensorFlow | cuDNN |
|------|-----------|---------|------------|-------|
| 11.8 | 520.61.05 | 2.0, 2.1 | 2.13, 2.14 | 8.7, 8.9 |
| 12.1 | 525.85.12 | 2.1, 2.2 | 2.15 | 8.9, 9.0 |
| 12.4 | 550.54.14 | 2.3, 2.4 | — | 9.1 |

> **Important**: These are architectural examples. Real values MUST come from official
> NVIDIA and framework documentation. Use TODO markers if uncertain.

### Python Compatibility Matrix

```
Framework Version → {
    min_python: str,
    max_python: str,
    supported_python: list[str]
}
```

| Package | Min Python | Max Python | Supported |
|---------|-----------|-----------|-----------|
| torch 2.1 | 3.8 | 3.11 | 3.8, 3.9, 3.10, 3.11 |
| torch 2.2 | 3.8 | 3.11 | 3.8, 3.9, 3.10, 3.11 |
| tensorflow 2.13 | 3.8 | 3.11 | 3.8–3.11 |
| tensorflow 2.15 | 3.9 | 3.11 | 3.9–3.11 |

---

## Resolution Algorithm

```
function resolve(profile, constraints):

  1. Load CUDA matrix for requested cuda_version OR ROCm matrix for rocm_version
     → If version not found: raise UnknownVersionError

  2. Validate driver_version >= matrix[cuda_version].min_driver
     → If fails: raise IncompatibilityError with required driver

  3. For each package in profile.packages:
     a. Determine candidate versions compatible with cuda_version
     b. Apply user overrides (if any)
     c. Validate override is in candidate set → raise if not
     d. Select latest compatible version (deterministic: sort descending, pick first)

  4. Validate all selected packages against Python version constraints
     → Intersection of supported Python sets
     → If empty intersection: raise IncompatibilityError

  5. Return ResolvedEnvironment {
       packages: [{ name, version }],
       python_version: str,
       cuda_version: str,
       notes: [str]
     }
```

---

## Error Design

All errors are structured and include actionable context.

```python
class IncompatibilityError(Exception):
    component: str       # e.g., "cuda", "torch", "python"
    constraint: str      # what was required
    detected: str        # what was found / requested
    suggestion: str      # human-readable fix hint
    docs_url: str        # link to official docs if available
```

Example:
```
IncompatibilityError(
    component="cuda",
    constraint="CUDA >= 11.8 required for torch 2.1",
    detected="CUDA 11.6",
    suggestion="Upgrade CUDA toolkit to 11.8 or select torch 2.0.x",
    docs_url="https://pytorch.org/get-started/locally/"
)
```

---

## Module Structure (Planned)

```
backend/
└── app/
    └── compatibility/
        ├── __init__.py
        ├── resolver.py          # CompatibilityResolver class
        ├── matrix/
        │   ├── cuda.py          # CUDA ↔ driver ↔ framework matrix
        │   ├── rocm.py          # ROCm ↔ driver ↔ framework matrix
        │   ├── python.py        # Python ↔ framework matrix
        │   └── os_rules.py      # OS-specific constraints
        ├── errors.py            # IncompatibilityError + subtypes
        ├── models.py            # ResolvedEnvironment, Constraint, etc.
        └── tests/
            ├── test_resolver.py
            ├── test_cuda_matrix.py
            └── test_python_matrix.py
```

---

## OS-Specific Rules

| Rule | WIN | WSL | LINUX |
|------|-----|-----|-------|
| CUDA GPU passthrough requires WSL2 | N/A | ✓ | N/A |
| PowerShell scripts only | ✓ | ✗ | ✗ |
| Bash scripts only | ✗ | ✓ | ✓ |
| WinGet package manager | ✓ | ✗ | ✗ |
| apt-get available | ✗ | ✓ | ✓ |
| NVIDIA driver on host required for WSL GPU | N/A | ✓ | N/A |

---

## Data Storage Strategy

- Compatibility matrices are stored in PostgreSQL (easy to update without code changes)
- A local YAML snapshot is bundled with the CLI agent for offline use
- Matrix data is versioned; old matrices are archived, not deleted
- Admin endpoint (Phase 6): `PUT /admin/matrix/cuda` to update matrix entries

---

## Testing Strategy

Every compatibility rule must have:
1. A positive test (valid combination → resolves successfully)
2. A negative test (invalid combination → correct IncompatibilityError raised)
3. An edge case test (e.g., exact boundary version)

No test may use mocks for the matrix data itself — matrix data is the ground truth.

---

## Future Improvements

- Conda environment resolution (Phase 6+)
- ROCm (AMD) support (Implemented in v0.1.1)
- ONNX Runtime compatibility
- Automatic matrix update from official release feeds (RSS/PyPI)
