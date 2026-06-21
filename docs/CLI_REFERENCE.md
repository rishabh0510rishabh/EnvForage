# CLI Reference

The `envforage` is a standalone command-line tool that inspects your ML environment hardware and software configurations.

## Installation
```bash
pip install envforage
```

## Global Options
- `--version`: Show the version and exit.
- `--help`: Show the help message and exit.

---

## 1. `envforage diagnose`

Scans your local environment (OS, CPU, RAM, GPU, CUDA, ROCm, cuDNN, Python) and generates a structured `DiagnosticReport`.

### Usage
```bash
envforage diagnose [OPTIONS]
```

### Options
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Save the report to the specified file path. |
| `-f, --format [json\|yaml\|markdown]` | Output format for the diagnostic report. Defaults to `json`. |
| `--send` | Send the report directly to the EnvForage API for compatibility analysis. Requires `--format json`. |
| `--api-url TEXT` | The base URL of the EnvForage API. Defaults to `http://localhost:8000`. Can also be set via `ENVFORAGE_API_URL`. |
| `-q, --quiet` | Suppress all human-readable terminal output and only print the raw report to stdout. |
| `--sarif` | Output diagnostics in SARIF 2.1.0 format for CI/CD pipeline integrations. |
| `-t, --timeout INT` | Timeout in seconds for each detector subprocess call. Defaults to `30`. |

> **WSL2 Note**: On WSL2 systems, `envforage diagnose` automatically checks GPU passthrough health (`/dev/dxg`, `nvidia-smi`, NVIDIA container toolkit) and warns if GPU acceleration is unavailable inside WSL2.

### Example
```bash
# Save JSON to file
envforage diagnose --output report.json

# Output as markdown
envforage diagnose --format markdown

# Save markdown report to file
envforage diagnose --format markdown --output report.md

# Output as YAML
envforage diagnose --format yaml

# Send to API for immediate analysis
envforage diagnose --send

# CI/CD SARIF output
envforage diagnose --sarif
```

---

## 2. `envforage verify`

Checks if your *current* system configuration meets the requirements for a specific EnvForage ML profile. 

### Usage
```bash
envforage verify --profile <PROFILE_SLUG> [OPTIONS]
```

### Options
| Option | Description |
|--------|-------------|
| `-p, --profile TEXT` | **Required.** The profile slug to verify against (e.g., `pytorch-cuda`, `tf-gpu`). |
| `--api-url TEXT` | The base URL of the EnvForage API. |

### Example
```bash
envforage verify --profile yolov8
# Output: ✓ COMPATIBLE — yolov8 is compatible with this system.
```

---

## 3. `envforage fix`

Reads a previously saved diagnostic report, sends it to the API, and generates a repair/setup script tailored to bridge the gap between your current system and the target profile.

### Usage
```bash
envforage fix --report <PATH> --profile <PROFILE_SLUG> [OPTIONS]
```

### Options
| Option | Description |
|--------|-------------|
| `-r, --report PATH` | **Required.** Path to the saved `DiagnosticReport` JSON file. |
| `-p, --profile TEXT` | **Required.** The profile slug to generate a script for. |
| `--api-url TEXT` | The base URL of the EnvForage API. |

### Example
```bash
envforage fix --report my_report.json --profile pytorch-cuda
# Outputs the generated bash/powershell script directly to the terminal.
```
## Troubleshooting

See `../TROUBLESHOOTING.md` for common errors, connection issues, and environment fixes.