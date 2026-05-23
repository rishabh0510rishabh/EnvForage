# CLI Reference

The `envforge-agent` is a standalone command-line tool that inspects your ML environment hardware and software configurations.

## Installation
```bash
pip install envforge-agent
```

## Global Options
- `--version`: Show the version and exit.
- `--help`: Show the help message and exit.

---

## 1. `envforge diagnose`

Scans your local environment (OS, CPU, RAM, GPU, CUDA, ROCm, cuDNN, Python) and generates a structured `DiagnosticReport`.

### Usage
```bash
envforge diagnose [OPTIONS]
```

### Options
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Save the JSON report to the specified file path. |
| `--send` | Send the report directly to the EnvForge API for compatibility analysis. |
| `--api-url TEXT` | The base URL of the EnvForge API. Defaults to `http://localhost:8000`. Can also be set via `ENVFORGE_API_URL`. |
| `-q, --quiet` | Suppress all human-readable terminal output and only print the raw JSON to stdout (useful for piping). |

### Example
```bash
# Save to file
envforge diagnose --output my_report.json

# Send to API for immediate analysis
envforge diagnose --send
```

---

## 2. `envforge verify`

Checks if your *current* system configuration meets the requirements for a specific EnvForge ML profile. 

### Usage
```bash
envforge verify --profile <PROFILE_SLUG> [OPTIONS]
```

### Options
| Option | Description |
|--------|-------------|
| `-p, --profile TEXT` | **Required.** The profile slug to verify against (e.g., `pytorch-cuda`, `tf-gpu`). |
| `--api-url TEXT` | The base URL of the EnvForge API. |

### Example
```bash
envforge verify --profile yolov8
# Output: ✓ COMPATIBLE — yolov8 is compatible with this system.
```

---

## 3. `envforge fix`

Reads a previously saved diagnostic report, sends it to the API, and generates a repair/setup script tailored to bridge the gap between your current system and the target profile.

### Usage
```bash
envforge fix --report <PATH> --profile <PROFILE_SLUG> [OPTIONS]
```

### Options
| Option | Description |
|--------|-------------|
| `-r, --report PATH` | **Required.** Path to the saved `DiagnosticReport` JSON file. |
| `-p, --profile TEXT` | **Required.** The profile slug to generate a script for. |
| `--api-url TEXT` | The base URL of the EnvForge API. |

### Example
```bash
envforge fix --report my_report.json --profile pytorch-cuda
# Outputs the generated bash/powershell script directly to the terminal.
```
## Troubleshooting

See `../TROUBLESHOOTING.md` for common errors, connection issues, and environment fixes.