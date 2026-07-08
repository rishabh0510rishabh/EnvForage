# CLI Diagnostic Agent — Feature Deep-Dive

> **Feature**: CLI Diagnostic Agent (`envforage`)
> **Status**: ✅ Implemented
> **Last Updated**: 2026-06-18

---

## Purpose

The CLI Diagnostic Agent is a standalone Python package that inspects the local
machine's hardware and software environment and produces a structured JSON report.

This report is the primary input to EnvForage's compatibility analysis and AI
troubleshooting features.

Key design constraints:
- **Offline-first**: Works without any network connection
- **Standalone**: No dependency on the backend; can be installed alone
- **Structured output**: Always emits `DiagnosticReportSchema` JSON — never prose

---

## Package Structure (Phase 2)

```
cli/
└── envforage/
    ├── __init__.py
    ├── __main__.py          # python -m envforage
    ├── cli.py               # Click CLI: diagnose, verify, fix
    ├── detectors/
    │   ├── os_detector.py   # platform, wsl_version
    │   ├── gpu_detector.py  # nvidia-smi JSON output
    │   ├── cuda_detector.py # nvcc --version, toolkit path
    │   ├── python_detector.py  # all python3.x in PATH
    │   └── driver_detector.py  # nvidia-smi driver query
    ├── schemas.py           # DiagnosticReportSchema (Pydantic)
    ├── report.py            # ReportBuilder + JSONFormatter
    └── tests/
        ├── test_detectors.py
        └── fixtures/
            ├── windows_gpu.json
            ├── linux_no_cuda.json
            └── wsl_cuda.json
```

---

## DiagnosticReport Schema (Backend — Already Implemented)

The `DiagnosticReportSchema` Pydantic model is defined in `backend/app/schemas/diagnostic.py`
and serves as the contract between the CLI agent and the API.

```python
class DiagnosticReportSchema(BaseModel):
    agent_version: str            # "2.0.0"
    os: OSInfo
    cpu: CPUInfo
    ram: RAMInfo
    gpus: list[GPUInfo]           # Empty list if no GPU
    cuda: CUDAInfo
    python_installations: list[PythonInfo]
    active_python: PythonInfo | None

class OSInfo(BaseModel):
    name: str                     # "Ubuntu 22.04", "Windows 11"
    version: str
    architecture: str             # "x86_64"
    wsl_version: str | None       # "WSL2" or None

class GPUInfo(BaseModel):
    name: str                     # "NVIDIA RTX 4080"
    vram_gb: float | None
    driver_version: str | None    # "535.54"
    index: int = 0

class CUDAInfo(BaseModel):
    version: str | None           # "12.1" or None
    toolkit_path: str | None
    cudnn_version: str | None
    nccl_version: str | None
```

---

## CLI Interface (Planned)

```bash
# Collect diagnostic report (output to terminal)
envforage diagnose

# Save to file
envforage diagnose --output report.json

# Send to EnvForage API automatically
envforage diagnose --send --api-url https://api.envforage.dev

# Verify a specific installed profile
envforage verify --profile pytorch-cuda

# Generate a repair script from a saved report
envforage fix --report report.json
```

---

## Detection Strategy (Per Detector)

### OS Detection
```python
import platform, subprocess

# Windows
platform.system() == "Windows"
platform.version()

# WSL detection
subprocess.run(["wsl", "--version"])  # or check /proc/version for "Microsoft"
```

### GPU Detection
```python
# nvidia-smi JSON output
subprocess.run([
    "nvidia-smi",
    "--query-gpu=name,memory.total,driver_version",
    "--format=csv,noheader,nounits"
])
# Parse output per GPU (one line per GPU)
```

### CUDA Detection
```python
subprocess.run(["nvcc", "--version"])   # Parses "release X.Y" from output
# Also check: /usr/local/cuda/version.txt on Linux
# Also check: CUDA_PATH env var on Windows
```

### Python Detection
```python
import glob, subprocess
# Find all python3.x binaries in PATH
# Run `python3.x --version` and `python3.x -m pip --version` for each
```

---

## Integration Points

### Backend API Integration
The agent sends its report to `POST /api/v1/diagnose` (already implemented):

```bash
envforage diagnose --send
# Equivalent to:
envforage diagnose --output /tmp/report.json
curl -X POST https://api.envforage.dev/api/v1/diagnose \
  -H "Content-Type: application/json" \
  -d @/tmp/report.json
```

### Offline Use
Without `--send`, the agent outputs JSON to stdout. Users can:
- Inspect it directly
- Copy it into the EnvForage web UI (Phase 3)
- Pass it to `envforage fix --report report.json`

---

## Platform Support

| Platform | Target | Key Detection Method |
|----------|--------|---------------------|
| Linux | ✅ Primary | `platform`, `nvcc`, `nvidia-smi` |
| WSL2 | ✅ Primary | `/proc/version` contains "Microsoft" |
| Windows | ✅ Secondary | `wmi`, `nvidia-smi.exe`, `py` launcher |
| macOS | ❌ Out of scope | MPS GPU differs — future consideration |

---

## Phase 2 Implementation Plan

1. `cli/pyproject.toml` — separate `envforage` PyPI package
2. OS, GPU, CUDA, Python, Driver detectors
3. `ReportBuilder` — aggregates all detector outputs
4. Click CLI (`diagnose`, `verify`, `fix` commands)
5. Unit tests with JSON fixtures for each platform
6. Integration test: `envforage diagnose` → `POST /api/v1/diagnose` → valid response

**Exit Criteria**: `envforage diagnose` produces valid `DiagnosticReportSchema`
JSON on Windows, WSL2, and Ubuntu 22.04.

---

## Future Improvements

- Auto-update check for matrix compatibility
- Machine-readable SARIF output format (for CI integration)
- Quiet mode (`--quiet`) for use in CI pipelines
- Export as HTML report

---

## Progress Indicators

The CLI displays real-time progress feedback during long-running operations using `rich.progress`.

### Architecture

`ReportBuilder.build()` accepts an optional `progress_callback` parameter. Before each detector runs, the callback is invoked with a status message (e.g., "Detecting GPUs"). The CLI commands (`diagnose`, `verify`, `troubleshoot`) pass a callback that updates a `rich.progress.Progress` spinner.

```text
┌─────────────────────────────────────────┐
│  ReportBuilder.build()                  │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ detect_os│→│detect_cpu│→│detect_…│ │
│  └────┬─────┘  └────┬─────┘  └───┬───┘ │
│       │ callback     │ callback   │     │
│       ▼              ▼            ▼     │
│  ┌─────────────────────────────────┐   │
│  │  rich.progress.Progress         │   │
│  │  SpinnerColumn + TextColumn     │   │
│  │  + TimeElapsedColumn            │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Behavior

- **When active**: Spinner cycles through detector names with elapsed time
- **When disabled**: `--quiet`, `--format json`, `--format minimal`, or non-TTY output
