# EnvForge 🛠️

> **Production-Grade ML Environment Provisioning Platform**

EnvForge is a developer tooling platform that generates intelligent, safe, and deterministic ML/AI environment setup scripts for Windows, WSL, Linux, and CUDA systems.

Stop wrestling with CUDA version mismatches, Python dependency hell, and OS-specific setup quirks. EnvForge detects your hardware and generates the exact setup script you need for your chosen ML framework.

---

## 👥 Contributors

A massive thank you to all the developers who have contributed code, resolved issues, and helped shape EnvForge into a production-grade ML environment provisioning platform!

<a href="https://github.com/rishabh0510rishabh/EnvForage/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=rishabh0510rishabh/EnvForage" alt="Contributors Grid" style="max-width: 100%; border-radius: 8px;" />
</a>

*Made with [contrib.rocks](https://contrib.rocks).*

---

## 📑 Table of Contents
- [Project Overview](#project-overview)
- [Contributors](#contributors)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Documentation Links](#documentation-links)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

---

## 🎯 Project Overview

**Deterministic logic > AI generation.**
Because scripts affect real systems, EnvForge relies on a strictly deterministic **Compatibility Engine** to resolve versions. It never guesses package versions or writes destructive shell commands. 

EnvForge helps users:
* Generate environment setup scripts (`setup.sh`, `setup.ps1`, `Dockerfile`)
* Install compatible ML frameworks (TensorFlow, PyTorch, YOLO, etc.)
* Verify existing environments
* Diagnose setup issues across OS, GPU, and Python boundaries

---

## ✨ Features

- **Environment Profiles**: Out-of-the-box configurations for `pytorch-cuda`, `tf-gpu`, `yolov8`, and more.
- **Hardware Introspection**: A standalone CLI agent (`envforge-agent`) that detects OS, RAM, GPU, VRAM, and CUDA details without an internet connection.
- **Safety First**: Every generated script passes through a regex-based `SafetyFilter` that strictly blocks dangerous commands (e.g., `rm -rf /`, `mkfs`).
- **Idempotent Setup**: Scripts verify prerequisites before installing anything.
- **RESTful API**: Fast, async backend built on FastAPI and PostgreSQL.

---

## 🏗️ Architecture

EnvForge is built with a modular, scalable architecture.

1. **CLI Diagnostic Agent**: Inspects local hardware and emits a structured JSON `DiagnosticReport`.
2. **API Layer**: FastAPI handles incoming requests and orchestrates logic.
3. **Compatibility Engine**: A pure-Python module holding the "Engineering Moat" — the CUDA and Framework compatibility matrices.
4. **Template Engine**: Renders Jinja2 templates (`.sh`, `.ps1`, `Dockerfile`) based on the resolved environment.
5. **Safety Filter**: Scans rendered output to block destructive actions.

For more details, see [ARCHITECTURE.md](./docs/ARCHITECTURE.md).

---

## 🚀 Quick Start

### 1. Install the CLI Agent
Inspect your environment without needing the backend!
```bash
pip install envforge-agent
envforge diagnose
```

### 2. Run the Backend (Docker)
```bash
git clone https://github.com/rishabh0510rishabh/EnvForage.git
cd EnvForage
docker-compose up -d
```
The API is now running at `http://localhost:8000`.

### 3. Generate a Script
Generate a PyTorch CUDA setup script for Linux:
```bash
curl -X POST http://localhost:8000/api/v1/scripts/generate \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "pytorch-cuda", "target_os": "LINUX", "output_formats": ["setup.sh"]}'
```

---

## 📚 Documentation Links

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | High-level system overview and component boundaries |
| [COMPATIBILITY_ENGINE.md](./docs/COMPATIBILITY_ENGINE.md) | Core logic: CUDA mappings and framework rules |
| [WORKFLOW.md](./docs/WORKFLOW.md) | Script generation, diagnosis, and repair flows |
| [AI_USAGE_POLICY.md](./docs/AI_USAGE_POLICY.md) | Where AI is allowed vs where deterministic logic is required |
| [SCRIPT_SAFETY.md](./docs/SCRIPT_SAFETY.md) | Prohibited commands and rollback philosophy |
| [CLI_REFERENCE.md](./docs/CLI_REFERENCE.md) | Commands for `envforge diagnose`, `verify`, and `fix` |
| [API_DESIGN.md](./docs/API_DESIGN.md) | REST endpoints, schemas, and validation rules |
| [PROFILE_SPEC.md](./docs/PROFILE_SPEC.md) | How to build and define new ML profiles |

---

## 🤝 Contributing

We love open source! Please read our [Contributing Guide](./CONTRIBUTING.md) to learn about:
- Local development setup
- Our branching and commit message strategy
- How to add new templates or profiles
- Writing tests for the Compatibility Engine

---

## 🗺️ Roadmap

- **Phase 1**: Core Backend (Compatibility Engine, Template Engine) ✅
- **Phase 2**: CLI Diagnostic Agent (`envforge-agent`) ✅
- **Phase 3**: Next.js Frontend Web App ✅
- **Phase 4**: AI Troubleshooting Layer ✅
- **Phase 5**: Environment Verification ✅
- **Phase 6**: Polish & Production Readiness ✅

See the full [ROADMAP.md](./docs/ROADMAP.md) for details.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
