# TROUBLESHOOTING.md

# Troubleshooting Guide

Common problems and fixes when using EnvForage CLI.

---

## 1. `EnvForage is not currently supported on macOS`

### Error
```bash
[ERROR] EnvForage is not currently supported on macOS.
```

### Cause
The CLI explicitly blocks macOS execution.

### Fix
Use one of the supported environments:
- Linux
- Windows + WSL2

---

## 2. `Cannot connect to API`

### Error
```bash
[ERROR] Cannot connect to http://localhost:8000/api/v1/diagnose
```

### Cause
Backend API server is not running or `ENVFORAGE_API_URL` is incorrect.

### Fix
Start the backend server first.

Example:
```bash
uvicorn app.main:app --reload
```

Or set the correct API URL:

```bash
export ENVFORAGE_API_URL=http://your-server:8000
```

Windows PowerShell:

```powershell
$env:ENVFORAGE_API_URL="http://your-server:8000"
```

---

## 3. CUDA not detected

### Symptom
CLI output shows:

```bash
CUDA: Not detected
```

### Cause
EnvForage checks CUDA using:
- `nvcc --version`
- `/usr/local/cuda/version.txt`
- `CUDA_PATH` / `CUDA_HOME`
- `nvidia-smi`

None returned a valid result.

### Fix

Verify CUDA installation:

```bash
nvcc --version
```

Verify NVIDIA driver:

```bash
nvidia-smi
```

If CUDA is installed but not found, set environment variables.

Linux:

```bash
export CUDA_HOME=/usr/local/cuda
```

Windows:

```powershell
$env:CUDA_PATH="C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x"
```

---

## 4. PyTorch import failed during verification

### Error
```bash
FAIL: PyTorch import failed — is it installed?
```

### Cause
`envforage verify` could not import `torch`.

### Fix

Install PyTorch in the active environment.

Example:

```bash
pip install torch
```

Verify installation:

```bash
python -c "import torch; print(torch.__version__)"
```

---

## 5. CUDA unavailable for GPU profile

### Error
```bash
PyTorch installed but CUDA not available
```

### Cause
PyTorch loaded successfully but:

```python
torch.cuda.is_available()
```

returned `False`.

### Fix

Check GPU visibility:

```bash
nvidia-smi
```

Check CUDA support inside PyTorch:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Install a CUDA-compatible PyTorch build if required.

---

## 6. Invalid diagnostic report file

### Error
```bash
Failed to parse report file
```

### Cause
`envforage fix` received malformed or incompatible JSON.

### Fix

Generate a fresh report:

```bash
envforage diagnose --output report.json
```

Then retry:

```bash
envforage fix --report report.json --profile pytorch-cuda
```

---

## 7. Verification timed out

### Error
```bash
Verification timed out
```

### Cause
The verification subprocess exceeded the 15-second timeout.

### Fix

Check your Python environment and PyTorch installation.

Test manually:

```bash
python -c "import torch"
```

---

## 8. `ollama: command not found`

### Cause
Ollama is not installed or missing from PATH.

### Fix

Install Ollama and restart the terminal.

Verify installation:

```bash
ollama --version
```

---

## 9. Docker connection issues

### Error
```bash
docker-compose: connection refused
```

### Fix

Ensure Docker Desktop / Docker daemon is running.

Start services:

```bash
docker-compose up -d
```

---

## 10. Module import errors after installation

### Error
```bash
ModuleNotFoundError
```

### Fix

Activate the virtual environment first.

Linux / WSL:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```