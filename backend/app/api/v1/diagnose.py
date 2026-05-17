"""Diagnose endpoint — POST /api/v1/diagnose."""
import uuid
from datetime import datetime

from fastapi import APIRouter

from app.api.deps import DB
from app.compatibility.errors import IncompatibilityError, UnsupportedOSError, UnknownVersionError
from app.compatibility.models import PackageConstraint
from app.compatibility.resolver import CompatibilityResolver
from app.models.diagnostic import DiagnosticReport
from app.schemas.diagnostic import CompatibilityIssue, DiagnoseResponse, DiagnosticReportSchema
from app.services import profile_service

router = APIRouter()

_resolver = CompatibilityResolver()

# ── OS name → target_os mapping ──────────────────────────────────────────────

_OS_KEYWORDS: list[tuple[str, str]] = [
    ("wsl", "WSL"),
    ("windows", "WIN"),
    ("macos", "MACOS"),
    ("darwin", "MACOS"),
    ("linux", "LINUX"),
    ("ubuntu", "LINUX"),
    ("debian", "LINUX"),
    ("centos", "LINUX"),
    ("fedora", "LINUX"),
    ("rhel", "LINUX"),
]


def _derive_target_os(os_name: str | None) -> str:
    """Map a human-readable OS name to the resolver's target_os string."""
    if not os_name:
        return "LINUX"
    lower = os_name.lower()
    for keyword, target in _OS_KEYWORDS:
        if keyword in lower:
            return target
    return "LINUX"


def _error_to_issue(profile_slug: str, error: IncompatibilityError) -> CompatibilityIssue:
    """Convert an IncompatibilityError into a CompatibilityIssue schema object."""
    component = getattr(error, "component", "compatibility")
    message = str(error)

    if isinstance(error, UnsupportedOSError):
        suggested_fix = (
            f"Profile '{profile_slug}' does not support the detected OS "
            f"({getattr(error, 'requested_os', 'unknown')}). "
            f"Choose a profile whose os_support includes your operating system."
        )
    elif isinstance(error, UnknownVersionError):
        suggested_fix = (
            f"Version '{getattr(error, 'version', 'unknown')}' is not in the "
            f"validated matrix for profile '{profile_slug}'. "
            f"Upgrade or switch to a supported version."
        )
    else:
        suggested_fix = (
            f"Resolve the {component} incompatibility for profile '{profile_slug}'."
        )

    return CompatibilityIssue(
        severity="ERROR",
        component=component,
        message=message,
        suggested_fix=suggested_fix,
    )


@router.post("/diagnose", response_model=DiagnoseResponse, status_code=201)
async def diagnose(
    report: DiagnosticReportSchema,
    db: DB,
) -> DiagnoseResponse:
    """
    Accept a DiagnosticReport from the CLI agent and return
    a compatibility analysis: which profiles are compatible,
    and what issues were found.
    """
    # Persist the raw report
    db_report = DiagnosticReport(
        id=uuid.uuid4(),
        report_data=report.model_dump(),
        os_type=report.os.name.split()[0].upper()[:5] if report.os else None,
        gpu_name=report.gpus[0].name if report.gpus else None,
        cuda_version=report.cuda.version if report.cuda else None,
        rocm_version=report.rocm.version if report.rocm else None,
        python_version=report.active_python.version[:4] if report.active_python else None,
        driver_version=report.gpus[0].driver_version if report.gpus else None,
        created_at=datetime.utcnow(),
    )
    db.add(db_report)
    await db.flush()

    # ── Full compatibility analysis against all active profiles ───────────
    issues: list[CompatibilityIssue] = []
    compatible_profiles: list[str] = []
    recommendations: list[str] = []

    # Derive machine-level inputs from the report
    target_os = _derive_target_os(report.os.name if report.os else None)
    python_version = (
        ".".join(report.active_python.version.split(".")[:2])
        if report.active_python
        else None
    )
    cuda_version = report.cuda.version if report.cuda else None

    # Fetch all active profiles
    profiles = await profile_service.list_all_active_profiles(db)

    for profile in profiles:
        # Build PackageConstraints from the profile's packages
        constraints = [
            PackageConstraint(
                name=pkg.package_name,
                version_spec=pkg.version_spec,
                cuda_variant=pkg.cuda_variant,
            )
            for pkg in sorted(profile.packages, key=lambda p: p.install_order)
        ]

        try:
            _resolver.resolve(
                packages=constraints,
                python_version=python_version or "3.11",
                cuda_version=cuda_version,
                target_os=target_os,
                profile_slug=profile.slug,
                os_support=list(profile.os_support),
                cuda_required=profile.cuda_required,
            )
            compatible_profiles.append(profile.slug)
            recommendations.append(
                f"{profile.name} is compatible with your environment."
            )
        except IncompatibilityError as exc:
            issues.append(_error_to_issue(profile.slug, exc))

    return DiagnoseResponse(
        report_id=str(db_report.id),
        compatible_profiles=compatible_profiles,
        issues=issues,
        recommendations=recommendations,
    )
