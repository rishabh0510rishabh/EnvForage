"""Detectors package."""

from envforge_agent.detectors.cuda_detector import detect_cuda
from envforge_agent.detectors.gpu_detector import detect_gpus, detect_wsl_gpu_passthrough
from envforge_agent.detectors.os_detector import detect_os
from envforge_agent.detectors.python_detector import detect_python
from envforge_agent.detectors.rocm_detector import detect_rocm
from envforge_agent.detectors.system_detector import detect_cpu, detect_ram, detect_disk

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
