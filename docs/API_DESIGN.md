# EnvForage — API Design

> **Version**: 2.0.0
> **Status**: Production
> **Last Updated**: 2026-06-18

---

## Design Principles

1. **RESTful**: Resource-oriented URLs, standard HTTP verbs
2. **Versioned**: All endpoints prefixed with `/api/v1/`
3. **Typed**: All request/response bodies defined as Pydantic models
4. **Safe**: No endpoint directly executes shell commands
5. **Documented**: Auto-generated OpenAPI/Swagger at `/api/docs`

---

## Base URL

```
Production : https://api.envforage.dev/api/v1
Development: http://localhost:8000/api/v1
```

---

## Endpoints

### Profiles

#### `GET /profiles`
List all available environment profiles.

**Query params**: `tags`, `os`, `cuda_required`, `page`, `limit`

**Response**:
```json
{
  "profiles": [
    {
      "id": "pytorch-cuda",
      "name": "PyTorch CUDA",
      "description": "...",
      "tags": ["deep-learning", "gpu"],
      "os_support": ["LINUX", "WSL", "WIN"],
      "cuda_required": true,
      "last_validated": "2025-12-01"
    }
  ],
  "total": 6,
  "page": 1
}
```

---

#### `GET /profiles/{profile_id}`
Get full profile details including package list and Python/CUDA versions.

**Response**:
```json
{
  "id": "pytorch-cuda",
  "name": "PyTorch CUDA",
  "python_versions": ["3.10", "3.11"],
  "cuda_versions": ["11.8", "12.1"],
  "packages": [
    { "name": "torch", "version": "2.1.0+cu118", "cuda": "11.8" },
    { "name": "torchvision", "version": "0.16.0" }
  ],
  "os_support": ["LINUX", "WSL"],
  "verification_script": "templates/verify/pytorch_cuda.sh.j2"
}
```

---

### Script Generation

#### `POST /scripts/generate`
Generate a set of setup scripts for a profile.

**Request**:
```json
{
  "profile_id": "pytorch-cuda",
  "target_os": "LINUX",
  "python_version": "3.11",
  "cuda_version": "12.1",
  "overrides": {
    "torch": "2.2.0"
  },
  "output_formats": ["setup.sh", "environment.yml", "Dockerfile"]
}
```

**Response**:
```json
{
  "job_id": "gen_abc123",
  "status": "completed",
  "download_url": "/scripts/gen_abc123/download",
  "preview": {
    "setup.sh": "#!/bin/bash\n# EnvForage Generated Script\n..."
  }
}
```

---

#### `GET /scripts/{job_id}/download`
Download the generated script bundle as a `.zip` file.

---

### Diagnostics

#### `POST /diagnose`
Accept a `DiagnosticReport` JSON from the CLI agent and return
a compatibility analysis.

**Request**: `DiagnosticReport` (see CLI Agent schema)

**Response**:
```json
{
  "report_id": "diag_xyz789",
  "compatible_profiles": ["pytorch-cuda", "yolov8"],
  "issues": [
    {
      "severity": "WARNING",
      "component": "cuda",
      "message": "CUDA 11.7 detected; PyTorch 2.1 requires CUDA 11.8+",
      "suggested_fix": "Upgrade CUDA toolkit to 11.8"
    }
  ],
  "recommendations": ["pytorch-cuda with cuda 11.8"]
}
```

---

### Verification

#### `POST /verify`
Submit a verification request for an installed environment.

**Request**:
```json
{
  "profile_id": "pytorch-cuda",
  "diagnostic_report_id": "diag_xyz789"
}
```

**Response**:
```json
{
  "verification_id": "ver_lmn456",
  "checks": [
    { "name": "cuda_available", "passed": true, "detail": "CUDA 12.1 detected" },
    { "name": "torch_gpu", "passed": false, "detail": "torch.cuda.is_available() returned False" }
  ],
  "overall": "FAILED"
}
```

---

### Feedback

#### `POST /feedback`
Submit user feedback, typically triggered during the uninstall flow.

**Request**:
```json
{
  "reason": "Too complex",
  "comments": "I preferred doing it manually.",
  "rating": 2
}
```

**Response**:
```json
{
  "feedback_id": "fb_123456",
  "status": "recorded"
}
```

---

### AI Troubleshooting

#### `POST /troubleshoot`
Send a diagnostic + verification context to AI for analysis.

**Request**:
```json
{
  "diagnostic_report_id": "diag_xyz789",
  "verification_id": "ver_lmn456",
  "user_description": "PyTorch cannot find GPU after CUDA install"
}
```

**Response**:
```json
{
  "session_id": "ai_session_001",
  "analysis": "The NVIDIA driver version 525.x is incompatible with CUDA 12.1...",
  "suggested_fixes": [
    {
      "step": 1,
      "title": "Update NVIDIA Driver",
      "description": "...",
      "safe_commands": ["nvidia-smi", "sudo apt install nvidia-driver-535"]
    }
  ],
  "repair_script_available": true
}
```

---

#### `POST /repair`
Generate a repair script based on AI analysis.

**Request**:
```json
{
  "session_id": "ai_session_001",
  "target_os": "LINUX",
  "approved_steps": [1, 2]
}
```

**Response**:
```json
{
  "repair_script": "#!/bin/bash\n# EnvForage Repair Script\n...",
  "warnings": ["This script will reinstall the NVIDIA driver. Close all GPU processes first."]
}
```

---

## Error Format

All errors follow this schema:
```json
{
  "error": {
    "code": "INCOMPATIBLE_VERSIONS",
    "message": "PyTorch 2.1.0 is incompatible with CUDA 11.6. Minimum required: 11.8",
    "details": { "package": "torch", "cuda_required": "11.8", "cuda_detected": "11.6" }
  }
}
```

---

## HTTP Status Codes Used

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created (job/report) |
| 400 | Bad request / validation error |
| 404 | Profile/report not found |
| 409 | Incompatibility conflict |
| 422 | Pydantic validation failure |
| 429 | Rate limited |
| 500 | Internal server error |
