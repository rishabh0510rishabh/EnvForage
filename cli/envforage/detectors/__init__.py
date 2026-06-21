"""Detectors package."""

from envforage.detectors.cuda_detector import detect_cuda
from envforage.detectors.gpu_detector import detect_gpus, detect_wsl_gpu_passthrough
from envforage.detectors.os_detector import detect_os
from envforage.detectors.python_detector import detect_python
from envforage.detectors.rocm_detector import detect_rocm
from envforage.detectors.system_detector import detect_cpu, detect_ram, detect_disk

__all__ = [
    "detect_os",
    "detect_cpu",
    "detect_ram",
    "detect_gpus",
    "detect_wsl_gpu_passthrough",
    "detect_cuda",
    "detect_rocm",
    "detect_disk",
    "detect_python",
]
