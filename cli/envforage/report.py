"""
ReportBuilder — orchestrates all detectors and assembles a DiagnosticReport.

Usage:
    from envforage.report import ReportBuilder
    report = ReportBuilder().build()
    print(report.to_json())
"""

from __future__ import annotations

from typing import Callable

from envforage.detectors import (
    detect_cpu,
    detect_cuda,
    detect_gpus,
    detect_os,
    detect_python,
    detect_ram,
    detect_rocm,
    detect_disk,
)
from envforage.schemas import DiagnosticReport


class ReportBuilder:
    """
    Orchestrates all detectors and assembles a complete DiagnosticReport.

    Each detector is called independently — a failure in one never prevents
    the others from running. Failures are silently absorbed and produce
    zero/None values in the report.
    """

    def __init__(self, timeout: int = 30) -> None:
        """
        Args:
            timeout: Seconds before each detector subprocess call is aborted.
                     Timed-out detectors return safe defaults (None / empty).
        """
        self._timeout = timeout

    def build(self, progress_callback: Callable[[str], None] | None = None) -> DiagnosticReport:
        """
        Run all detectors and return a validated DiagnosticReport.

        Always succeeds — worst case returns a report with empty/None fields.

        Args:
            progress_callback: Optional function called with a status message
                               before each detector runs.
        """
        def _step(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        _step("Detecting OS")
        os_info = detect_os()

        _step("Detecting CPU")
        cpu_info = detect_cpu()

        _step("Detecting RAM")
        ram_info = detect_ram()

        _step("Detecting GPUs")
        gpus = detect_gpus(timeout=self._timeout)

        _step("Detecting CUDA")
        cuda_info = detect_cuda(timeout=self._timeout)

        _step("Detecting ROCm")
        rocm_info = detect_rocm()

        _step("Detecting disk")
        disk_info = detect_disk()

        _step("Detecting Python installations")
        installations, active_python = detect_python()

        return DiagnosticReport(
            os=os_info,
            cpu=cpu_info,
            ram=ram_info,
            gpus=gpus,
            cuda=cuda_info,
            rocm=rocm_info,
            disk=disk_info,
            python_installations=installations,
            active_python=active_python,
        )
