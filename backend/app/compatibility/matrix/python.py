"""
Python Version Compatibility Matrix.

Maps ML framework versions to their supported Python version ranges.
Data is now dynamically generated and loaded from python_matrix_data.json.

Sources:
  - PyPI Metadata (Requires-Python) for Python version constraints.
  - PyTorch: https://pytorch.org/get-started/locally/
  - TensorFlow: https://www.tensorflow.org/install/pip#software_requirements
  - Ultralytics YOLOv8: https://docs.ultralytics.com/quickstart/
"""

import json
from pathlib import Path

from app.compatibility.models import FrameworkVersionEntry

# ── Framework Version → Python Compatibility ──────────────────────────────────

_HARDCODED_MATRIX: dict[str, list[FrameworkVersionEntry]] = {
    "torch": [
        FrameworkVersionEntry(
            framework="torch",
            version="2.0.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.7", "11.8"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.0.1",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.7", "11.8"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.1.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.1.1",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.1.2",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
            supported_rocm=["5.4.2", "5.6.0"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.2.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.2.1",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.2.2",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.3.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.4.0",
            min_python="3.8",
            max_python="3.12",
            supported_python=["3.8", "3.9", "3.10", "3.11", "3.12"],
            supported_cuda=["11.8", "12.1", "12.4"],
            supported_rocm=["6.0.0", "6.1.0"],
        ),
        FrameworkVersionEntry(
            framework="torch",
            version="2.5.0",
            min_python="3.9",
            max_python="3.13",
            supported_python=["3.9", "3.10", "3.11", "3.12", "3.13"],
            supported_cuda=["11.8", "12.1", "12.4"],
            supported_rocm=["6.2.0"],
        ),
    ],
    "tensorflow": [
        # Note: TensorFlow on Windows requires WSL2 for GPU support (TF 2.11+)
        FrameworkVersionEntry(
            framework="tensorflow",
            version="2.13.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8"],
        ),
        FrameworkVersionEntry(
            framework="tensorflow",
            version="2.14.0",
            min_python="3.9",
            max_python="3.11",
            supported_python=["3.9", "3.10", "3.11"],
            supported_cuda=["11.8"],
        ),
        FrameworkVersionEntry(
            framework="tensorflow",
            version="2.15.0",
            min_python="3.9",
            max_python="3.11",
            supported_python=["3.9", "3.10", "3.11"],
            supported_cuda=["12.1"],
        ),
        FrameworkVersionEntry(
            framework="tensorflow",
            version="2.16.0",
            min_python="3.9",
            max_python="3.13",
            supported_python=["3.9", "3.10", "3.11", "3.12", "3.13"],
            supported_cuda=["12.1"],
        ),
        # TF 2.16+ added with Python 3.13 support
    ],
    "ultralytics": [
        FrameworkVersionEntry(
            framework="ultralytics",
            version="8.0.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="ultralytics",
            version="8.1.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="ultralytics",
            version="8.2.0",
            min_python="3.8",
            max_python="3.12",
            supported_python=["3.8", "3.9", "3.10", "3.11", "3.12"],
            supported_cuda=["11.8", "12.1", "12.4"],
        ),
        FrameworkVersionEntry(
            framework="ultralytics",
            version="8.3.0",
            min_python="3.9",
            max_python="3.13",
            supported_python=["3.9", "3.10", "3.11", "3.12", "3.13"],
            supported_cuda=["11.8", "12.1", "12.4"],
        ),
    ],
    "diffusers": [
        # Hugging Face Diffusers — CUDA support comes via PyTorch dependency.
        # Source: https://huggingface.co/docs/diffusers/installation
        # Source: https://github.com/huggingface/diffusers/releases
        FrameworkVersionEntry(
            framework="diffusers",
            version="0.21.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.7", "11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="diffusers",
            version="0.24.0",
            min_python="3.8",
            max_python="3.11",
            supported_python=["3.8", "3.9", "3.10", "3.11"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="diffusers",
            version="0.25.0",
            min_python="3.8",
            max_python="3.12",
            supported_python=["3.8", "3.9", "3.10", "3.11", "3.12"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="diffusers",
            version="0.26.0",
            min_python="3.8",
            max_python="3.12",
            supported_python=["3.8", "3.9", "3.10", "3.11", "3.12"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="diffusers",
            version="0.27.0",
            min_python="3.8",
            max_python="3.12",
            supported_python=["3.8", "3.9", "3.10", "3.11", "3.12"],
            supported_cuda=["11.8", "12.1"],
        ),
        FrameworkVersionEntry(
            framework="diffusers",
            version="0.27.2",
            min_python="3.8",
            max_python="3.12",
            supported_python=["3.8", "3.9", "3.10", "3.11", "3.12"],
            supported_cuda=["11.8", "12.1"],
        ),
    ],
}
MATRIX_JSON_PATH = Path(__file__).resolve().parent / "python_matrix_data.json"

with open(MATRIX_JSON_PATH) as f:
    _raw_data = json.load(f)

PYTHON_MATRIX: dict[str, list[FrameworkVersionEntry]] = dict(_HARDCODED_MATRIX)
for _framework, _entries in _raw_data.items():
    PYTHON_MATRIX[_framework] = [FrameworkVersionEntry(**kwargs) for kwargs in _entries]


def get_framework_versions(framework: str) -> list[FrameworkVersionEntry]:
    """Return all known versions for a framework."""
    return PYTHON_MATRIX.get(framework, [])


def get_framework_entry(framework: str, version: str) -> FrameworkVersionEntry | None:
    """Return the matrix entry for a specific framework version."""
    for entry in PYTHON_MATRIX.get(framework, []):
        if entry.version == version:
            return entry
    return None


def get_latest_compatible_version(
    framework: str,
    python_version: str,
    cuda_version: str | None = None,
    rocm_version: str | None = None,
) -> str | None:
    """
    Return the latest framework version compatible with the given
    Python, CUDA, and ROCm versions. Returns None if no compatible version found.
    """
    candidates = []
    for entry in PYTHON_MATRIX.get(framework, []):
        if python_version not in entry.supported_python:
            continue
        if cuda_version is not None and cuda_version not in entry.supported_cuda:
            continue
        if rocm_version is not None and rocm_version not in entry.supported_rocm:
            continue
        candidates.append(entry.version)

    if not candidates:
        return None

    # Sort descending by version tuple and return the first (latest)
    candidates.sort(key=lambda v: tuple(int(x) for x in v.split(".")), reverse=True)
    return candidates[0]
