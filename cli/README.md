# envforage

> Standalone CLI diagnostic agent for the [EnvForage](https://github.com/rishabh0510rishabh/EnvForage) platform.

Inspects your local ML environment and reports what's installed, what's compatible,
and what's broken — without requiring a network connection.

## Install

```bash
pip install envforage
```

## Commands

```bash
# Inspect your environment (output to terminal)
envforage diagnose

# Save report to JSON file
envforage diagnose --output report.json

# Send report to EnvForage API for compatibility analysis
envforage diagnose --send --api-url https://api.envforage.dev

# Check if a specific profile is compatible with your system
envforage verify --profile pytorch-cuda

# Generate a repair script from a saved diagnostic report
envforage fix --report report.json
```

## What it detects

| Category | Details |
|---|---|
| OS | Name, version, architecture, WSL version |
| CPU | Brand, physical cores, logical threads |
| RAM | Total GB, available GB |
| GPU | Name, VRAM, driver version (via nvidia-smi) |
| CUDA | Installed version, toolkit path, cuDNN version |
| Python | All installed versions, active venv, pip version |

## Output format

All commands output `DiagnosticReport` JSON compatible with `POST /api/v1/diagnose`.

```json
{
  "agent_version": "2.0.0",
  "os": { "name": "Ubuntu 22.04", "version": "22.04", "architecture": "x86_64" },
  "cpu": { "brand": "Intel Core i9-13900K", "cores": 24, "threads": 32 },
  "ram": { "total_gb": 64.0, "available_gb": 48.2 },
  "gpus": [{ "name": "NVIDIA RTX 4090", "vram_gb": 24.0, "driver_version": "535.54", "index": 0 }],
  "cuda": { "version": "12.1", "toolkit_path": "/usr/local/cuda-12.1", "cudnn_version": "8.9.0" },
  "python_installations": [{ "version": "3.11.9", "path": "/usr/bin/python3.11", "is_venv": false }],
  "active_python": { "version": "3.11.9", "path": "/usr/bin/python3.11", "is_venv": false }
}
```

## Platform support

| Platform | Status |
|---|---|
| Linux (Ubuntu, Debian, Fedora, Arch) | ✅ Full support |
| Windows 10/11 | ✅ Full support |
| WSL2 | ✅ Full support |
| macOS | ❌ Out of scope (no CUDA) |

## Troubleshooting

For common CLI, API, and environment issues, see:

`../TROUBLESHOOTING.md`
