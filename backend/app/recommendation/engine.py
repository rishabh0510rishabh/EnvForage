"""
Deterministic rule-based ML Framework Recommendation Engine.

Accepts a DiagnosticReportSchema and returns ranked profile recommendations
based on detected hardware. No LLM calls — per AI_USAGE_POLICY.md.
"""

from __future__ import annotations

from typing import Any

from app.schemas.diagnostic import DiagnosticReportSchema


def recommend_profiles(report: DiagnosticReportSchema) -> dict[str, Any]:
    """
    Analyze a diagnostic report and return recommended ML profiles with warnings.

    Returns:
        dict with keys:
            - recommended_profiles: list[dict] with name, reason, rank
            - warnings: list[str]
    """
    warnings: list[str] = []
    profiles: list[dict[str, Any]] = []

    has_gpu = len(report.gpus) > 0
    max_vram = _get_max_vram(report)
    total_ram = report.ram.total_gb
    is_apple_silicon = _is_apple_silicon(report)

    if total_ram < 8:
        warnings.append(
            "Low system RAM (<8 GB). Heavy ML workloads may fail or swap heavily. "
            "Consider cpu-only lightweight profiles."
        )

    if is_apple_silicon:
        profiles.append({
            "name": "pytorch-mps",
            "reason": "Apple Silicon detected — PyTorch MPS backend provides GPU acceleration",
            "rank": 1,
        })
        profiles.append({
            "name": "cpu-only",
            "reason": "Fallback for frameworks without MPS support",
            "rank": 2,
        })
    elif not has_gpu:
        profiles.append({
            "name": "cpu-only",
            "reason": "No GPU detected — use CPU-based frameworks (PyTorch CPU, TensorFlow CPU)",
            "rank": 1,
        })
        profiles.append({
            "name": "sklearn",
            "reason": "Scikit-learn works well on CPU-only systems",
            "rank": 2,
        })
    elif max_vram is not None and max_vram < 4:
        warnings.append(
            f"Low GPU VRAM ({max_vram:.1f} GB). Large models will not fit. "
            "Recommending lightweight GPU profiles."
        )
        profiles.append({
            "name": "yolov8-nano",
            "reason": "Lightweight model optimized for low-VRAM GPUs (<4 GB)",
            "rank": 1,
        })
        profiles.append({
            "name": "sklearn",
            "reason": "CPU-based ML — avoids VRAM limitations",
            "rank": 2,
        })
    elif max_vram is not None and max_vram <= 8:
        profiles.append({
            "name": "pytorch-cuda",
            "reason": f"GPU with {max_vram:.1f} GB VRAM — suitable for PyTorch CUDA workloads",
            "rank": 1,
        })
        profiles.append({
            "name": "yolov8",
            "reason": "YOLOv8 runs well on 4–8 GB VRAM GPUs",
            "rank": 2,
        })
    else:
        vram_label = f"{max_vram:.1f} GB" if max_vram is not None else "unknown"
        profiles.append({
            "name": "tf-gpu",
            "reason": f"High-VRAM GPU ({vram_label}) — TensorFlow GPU for large models",
            "rank": 1,
        })
        profiles.append({
            "name": "pytorch-cuda",
            "reason": "PyTorch CUDA — excellent for high-VRAM training and research",
            "rank": 2,
        })
        profiles.append({
            "name": "yolov8",
            "reason": "YOLOv8 with full model variants on high-VRAM GPU",
            "rank": 3,
        })

    return {
        "recommended_profiles": profiles,
        "warnings": warnings,
    }


def _get_max_vram(report: DiagnosticReportSchema) -> float | None:
    """Return the maximum VRAM across all detected GPUs, or None if unknown."""
    vrams = [gpu.vram_gb for gpu in report.gpus if gpu.vram_gb is not None]
    return max(vrams) if vrams else None


def _is_apple_silicon(report: DiagnosticReportSchema) -> bool:
    """Detect Apple Silicon from OS and CPU info."""
    os_name = report.os.name.lower()
    cpu_brand = report.cpu.brand.lower()
    is_macos = "macos" in os_name or "darwin" in os_name or "mac os" in os_name
    is_arm_apple = "apple" in cpu_brand or "m1" in cpu_brand or "m2" in cpu_brand or "m3" in cpu_brand or "m4" in cpu_brand
    return is_macos and is_arm_apple
