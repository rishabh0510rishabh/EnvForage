# Diagnostic Dashboard (Phase 3)

> **Status**: ✅ Implemented
> **Last Updated**: 2026-05-14

## Overview

The Diagnostic Dashboard is a frontend feature of the EnvForage Web Application that allows users to paste the JSON output of the CLI diagnostic agent (`envforage diagnose --quiet`) and visualize their hardware configuration, run compatibility checks against environment profiles, and navigate directly to the Script Generation Wizard for compatible profiles.

## Location

- **Frontend Route**: `/diagnose`
- **Source File**: `frontend/src/app/diagnose/page.tsx`
- **Backend Endpoint**: `POST /api/v1/diagnose`

## User Flow

```
1. User navigates to /diagnose
2. Pastes DiagnosticReport JSON into text area
3. Clicks "Analyze Report" → Client-side JSON validation
4. Hardware Overview cards rendered (OS, CPU, GPU, CUDA)
5. User selects a target profile from dropdown
6. Clicks "Run Check" → POST /api/v1/diagnose
7. Results panel shows:
   ├── Compatible Profiles (clickable → /generate?profile=xxx)
   ├── Issues with severity badges (WARNING ⚠️ / ERROR 🔴)
   │   └── Each issue includes a suggested fix
   └── Recommendations from the compatibility engine
```

## Hardware Overview Cards

The dashboard renders four hardware cards from the parsed JSON:

| Card | Data Source | Fields Displayed |
|------|-----------|------------------|
| Operating System | `report.os` | Name, architecture, WSL version |
| Processor | `report.cpu` | Brand, cores, threads |
| Graphics (GPU) | `report.gpus[0]` | Name, VRAM, driver version |
| CUDA Toolkit | `report.cuda` | Version, cuDNN version |

## Backend Response Contract

```json
// POST /api/v1/diagnose → 201 Created
{
  "report_id": "uuid",
  "compatible_profiles": ["pytorch-cuda", "yolov8", "stable-diffusion"],
  "issues": [
    {
      "severity": "WARNING",
      "component": "cuda",
      "message": "CUDA 10.2 is not in EnvForage's validated matrix.",
      "suggested_fix": "Supported CUDA versions: 11.8, 12.1",
      "docs_url": "https://docs.nvidia.com/cuda/"
    }
  ],
  "recommendations": ["pytorch-cuda with CUDA 12.1"]
}
```

## TypeScript Type Alignment

The frontend `DiagnosticResponse` interface is strictly aligned with the backend `DiagnoseResponse` Pydantic model:

```typescript
interface CompatibilityIssue {
  severity: string;    // "ERROR" | "WARNING" | "INFO"
  component: string;   // "cuda" | "driver" | "python"
  message: string;
  suggested_fix: string;
  docs_url?: string;
}

interface DiagnosticResponse {
  report_id: string;
  compatible_profiles: string[];
  issues: CompatibilityIssue[];
  recommendations: string[];
}
```

## Design Decisions

- **Client-side parsing**: JSON validation is performed in the browser before sending to the backend, giving immediate feedback on malformed input.
- **Compatibility derived from issues**: Instead of a separate `compatible` boolean, compatibility is derived from `issues.length === 0`.
- **Clickable profile chips**: Compatible profiles are rendered as styled links that navigate directly to `/generate?profile={slug}`, enabling a seamless diagnostic → generation workflow.
- **Severity-colored badges**: Issues use color-coded severity (yellow for WARNING, red for ERROR) for instant visual triage.
