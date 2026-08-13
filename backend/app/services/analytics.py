from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic import DiagnosticReport, VerificationCheck


class AnalyticsEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self) -> dict[str, Any]:
        vendor_case = case(
            (DiagnosticReport.gpu_name.is_(None), "No GPU"),
            (DiagnosticReport.gpu_name.ilike("%nvidia%"), "NVIDIA"),
            (DiagnosticReport.gpu_name.ilike("%amd%"), "AMD"),
            (DiagnosticReport.gpu_name.ilike("%intel%"), "Intel"),
            else_="Other",
        )
        gpu_counts = await self.db.execute(
            select(vendor_case, func.count()).group_by(vendor_case)
        )
        gpu_distribution: dict[str, int] = dict(gpu_counts.all())  # type: ignore[arg-type]

        python_counts = await self.db.execute(
            select(DiagnosticReport.python_version, func.count())
            .group_by(DiagnosticReport.python_version)
        )
        python_version_histogram = {
            (v or "unknown"): c for v, c in python_counts.all()
        }

        cuda_gpu_counts = await self.db.execute(
            select(
                DiagnosticReport.cuda_version,
                DiagnosticReport.gpu_name,
                func.count(),
            )
            .where(DiagnosticReport.cuda_version.is_not(None))
            .group_by(DiagnosticReport.cuda_version, DiagnosticReport.gpu_name)
        )
        cuda_version_heatmap = [
            {"cuda_version": cv, "gpu_name": gn or "unknown", "count": c}
            for cv, gn, c in cuda_gpu_counts.all()
        ]

        os_counts = await self.db.execute(
            select(DiagnosticReport.os_type, func.count())
            .group_by(DiagnosticReport.os_type)
        )
        os_distribution = {(o or "unknown"): c for o, c in os_counts.all()}

        failure_counts = await self.db.execute(
            select(VerificationCheck.check_name, func.count())
            .where(VerificationCheck.passed.is_(False))
            .group_by(VerificationCheck.check_name)
            .order_by(func.count().desc())
            .limit(10)
        )
        common_failures: dict[str, int] = dict(failure_counts.all())  # type: ignore[arg-type]

        return {
            "gpu_distribution": gpu_distribution,
            "python_version_histogram": python_version_histogram,
            "cuda_version_heatmap": cuda_version_heatmap,
            "os_distribution": os_distribution,
            "common_failures": common_failures,
        }
