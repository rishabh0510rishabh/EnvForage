"""
ReportBuilder — orchestrates all detectors and assembles a DiagnosticReport.

Usage:
    from envforage.report import ReportBuilder
    report = ReportBuilder().build()
    print(report.to_json())
"""

from __future__ import annotations

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

    def build(self) -> DiagnosticReport:
        """
        Run all detectors and return a validated DiagnosticReport.

        Always succeeds — worst case returns a report with empty/None fields.
        """
        os_info = detect_os()
        cpu_info = detect_cpu()
        ram_info = detect_ram()
        gpus = detect_gpus(timeout=self._timeout)
        cuda_info = detect_cuda(timeout=self._timeout)
        rocm_info = detect_rocm()
        disk_info = detect_disk()
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
