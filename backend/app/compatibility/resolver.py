"""
Compatibility Resolver — the core decision-making engine.

This module resolves package and environment constraints. It queries database-backed
matrices when an async database session is provided, using a cached intermediate layer
to keep execution performance extremely high and prevent DetachedInstanceErrors.
If the database session is absent or a database error occurs, it falls back to local
static matrix definitions.
"""

import logging

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compatibility.errors import (
    IncompatibilityError,
    UnknownVersionError,
    UnsupportedOSError,
)
from app.compatibility.matrix.cuda import (
    get_cuda_entry,
)
from app.compatibility.matrix.os_rules import get_os_notes
from app.compatibility.matrix.python import (
    get_framework_versions,
)
from app.compatibility.matrix.rocm import (
    get_rocm_entry,
)
from app.compatibility.models import (
    CUDAMatrixEntry,
    FrameworkVersionEntry,
    OSTarget,
    PackageConstraint,
    ResolvedEnvironment,
    ResolvedPackage,
    ROCMMatrixEntry,
)
from app.models.matrix import (
    CUDAMatrixEntry as CUDAMatrixDBModel,
)
from app.models.matrix import (
    PythonMatrixEntry as PythonMatrixDBModel,
)
from app.models.matrix import (
    RocmMatrixEntry as RocmMatrixDBModel,
)

logger = logging.getLogger(__name__)


async def clear_compatibility_cache() -> None:
    """Clear all Redis compatibility matrix caches."""

    try:
        from app.cache import get_redis_client

        redis = await get_redis_client()
        if redis is not None:
            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor, match="compatibility_resolver:v1:*", count=100
                )
                if keys:
                    await redis.delete(*keys)
                if cursor == 0:
                    break
    except Exception as exc:
        logger.warning("Failed to clear Redis compatibility resolver cache: %s", exc)


class CompatibilityResolver:
    """
    Resolves a set of package constraints + environment constraints into a
    fully validated, pinned ResolvedEnvironment.

    All incompatibilities raise structured IncompatibilityError exceptions
    with actionable messages — never bare strings.
    """

    async def _get_cuda_entry(
        self, db: AsyncSession | None, version: str
    ) -> CUDAMatrixEntry | None:
        if db is not None:
            try:
                stmt = select(CUDAMatrixDBModel).where(
                    CUDAMatrixDBModel.cuda_version == version
                )
                result = await db.execute(stmt)
                db_entry = result.scalars().first()
                if db_entry:
                    entry = CUDAMatrixEntry(
                        cuda_version=db_entry.cuda_version,
                        min_driver_linux=db_entry.min_driver_linux,
                        min_driver_windows=db_entry.min_driver_windows,
                        cudnn_versions=db_entry.cudnn_versions,
                        supported_archs=db_entry.supported_archs,
                        notes=db_entry.notes or "",
                        source_url=db_entry.source_url or "",
                    )
                else:
                    entry = None
                return entry
            except Exception as exc:
                logger.warning(
                    "DB query for CUDA version %s failed, falling back to static: %s",
                    version,
                    exc,
                )
        return get_cuda_entry(version)

    async def _get_rocm_entry(
        self, db: AsyncSession | None, version: str
    ) -> ROCMMatrixEntry | None:
        if db is not None:
            try:
                stmt = select(RocmMatrixDBModel).where(
                    RocmMatrixDBModel.rocm_version == version
                )
                result = await db.execute(stmt)
                db_entry = result.scalars().first()
                if db_entry:
                    entry = ROCMMatrixEntry(
                        rocm_version=db_entry.rocm_version,
                        min_driver_linux=db_entry.min_driver_linux,
                        supported_gpus=db_entry.supported_gpus,
                        notes=db_entry.notes or "",
                        source_url=db_entry.source_url or "",
                    )
                else:
                    entry = None
                return entry
            except Exception as exc:
                logger.warning(
                    "DB query for ROCm version %s failed, falling back to static: %s",
                    version,
                    exc,
                )
        return get_rocm_entry(version)

    async def _get_framework_versions(
        self, db: AsyncSession | None, framework: str
    ) -> list[FrameworkVersionEntry]:
        if db is not None:
            try:
                stmt = select(PythonMatrixDBModel).where(
                    PythonMatrixDBModel.framework == framework
                )
                result = await db.execute(stmt)
                db_entries = result.scalars().all()
                entries = [
                    FrameworkVersionEntry(
                        framework=db_entry.framework,
                        version=db_entry.version,
                        min_python=db_entry.min_python,
                        max_python=db_entry.max_python,
                        supported_cuda=db_entry.supported_cuda,
                        supported_rocm=db_entry.supported_rocm,
                        supported_python=db_entry.supported_python,
                    )
                    for db_entry in db_entries
                ]
                return entries
            except Exception as exc:
                logger.warning(
                    "DB query for framework %s failed, falling back to static: %s",
                    framework,
                    exc,
                )
        return get_framework_versions(framework)

    async def _get_framework_entry(
        self, db: AsyncSession | None, framework: str, version: str
    ) -> FrameworkVersionEntry | None:
        versions = await self._get_framework_versions(db, framework)
        for entry in versions:
            if entry.version == version:
                return entry
        return None

    async def _get_supported_cuda_versions(self, db: AsyncSession | None) -> list[str]:
        if db is not None:
            try:
                stmt = select(CUDAMatrixDBModel.cuda_version)
                result = await db.execute(stmt)
                versions = sorted(result.scalars().all())
                if versions:
                    return versions
            except Exception:
                pass
        from app.compatibility.matrix.cuda import SUPPORTED_CUDA_VERSIONS

        return SUPPORTED_CUDA_VERSIONS

    async def _get_supported_rocm_versions(self, db: AsyncSession | None) -> list[str]:
        if db is not None:
            try:
                stmt = select(RocmMatrixDBModel.rocm_version)
                result = await db.execute(stmt)
                versions = sorted(result.scalars().all())
                if versions:
                    return versions
            except Exception:
                pass
        from app.compatibility.matrix.rocm import SUPPORTED_ROCM_VERSIONS

        return SUPPORTED_ROCM_VERSIONS

    async def resolve(
        self,
        packages: list[PackageConstraint],
        python_version: str,
        cuda_version: str | None,
        target_os: OSTarget,
        profile_slug: str,
        os_support: list[str],
        rocm_version: str | None = None,
        cuda_required: bool = False,
        rocm_required: bool = False,
        overrides: dict[str, str] | None = None,
        db: AsyncSession | None = None,
    ) -> ResolvedEnvironment:
        """
        Resolves a set of package constraints + environment constraints into a
        fully validated, pinned ResolvedEnvironment.

        Args:
            packages: List of package constraints from the profile
            python_version: Requested Python version, e.g. "3.11"
            cuda_version: Requested CUDA version, e.g. "12.1", or None for CPU
            target_os: Target OS: "LINUX" | "WSL" | "WIN"
            profile_slug: Profile identifier for error messages
            os_support: OS targets this profile supports
            cuda_required: Whether CUDA is mandatory for this profile
            overrides: User-specified version overrides {package_name: version}
            db: Optional async database session. If provided, matrix will be queried from the database.

        Returns:
            ResolvedEnvironment with all packages pinned and validated

        Raises:
            UnsupportedOSError: If target_os is not in os_support
            IncompatibilityError: If any version constraint cannot be satisfied
            UnknownVersionError: If a requested version is not in the matrix
        """
        overrides = overrides or {}

        # Step 1: Validate OS support
        self._validate_os(target_os, profile_slug, os_support)

        # Step 2: Validate CUDA constraint
        warnings: list[str] = []
        if cuda_required and cuda_version is None:
            supported_cuda = await self._get_supported_cuda_versions(db)
            raise IncompatibilityError(
                component="cuda",
                constraint=f"Profile '{profile_slug}' requires CUDA",
                detected="No CUDA version specified",
                suggestion=(
                    "Provide a cuda_version in your request. "
                    f"Supported: {', '.join(supported_cuda)}"
                ),
            )

        if cuda_version is not None:
            await self._validate_cuda_version(db, cuda_version)

        if rocm_required and rocm_version is None:
            supported_rocm = await self._get_supported_rocm_versions(db)
            raise IncompatibilityError(
                component="rocm",
                constraint=f"Profile '{profile_slug}' requires ROCm",
                detected="No ROCm version specified",
                suggestion=(
                    "Provide a rocm_version in your request. "
                    f"Supported: {', '.join(supported_rocm)}"
                ),
            )

        if rocm_version is not None:
            await self._validate_rocm_version(db, rocm_version)

        # Step 3: Resolve each package
        resolved_packages: list[ResolvedPackage] = []
        for constraint in packages:
            resolved = await self._resolve_package(
                db=db,
                constraint=constraint,
                python_version=python_version,
                cuda_version=cuda_version,
                rocm_version=rocm_version,
                override_version=overrides.get(constraint.name),
            )
            resolved_packages.append(resolved)

        # Step 4: Collect compatibility warnings
        framework_names = [p.name for p in packages]
        gpu_required = cuda_required or rocm_required
        os_notes = get_os_notes(target_os, gpu_required, framework_names)
        warnings.extend(os_notes)
        warnings.extend(
            self._warn_on_abi_sensitive_hybrid_environment(resolved_packages)
        )

        return ResolvedEnvironment(
            python_version=python_version,
            cuda_version=cuda_version,
            rocm_version=rocm_version,
            target_os=target_os,
            packages=resolved_packages,
            warnings=warnings,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _validate_os(
        self,
        target_os: OSTarget,
        profile_slug: str,
        os_support: list[str],
    ) -> None:
        if target_os not in os_support:
            raise UnsupportedOSError(
                profile_slug=profile_slug,
                requested_os=target_os,
                supported_os=os_support,
            )

    async def _validate_cuda_version(
        self, db: AsyncSession | None, cuda_version: str
    ) -> None:
        entry = await self._get_cuda_entry(db, cuda_version)
        if entry is None:
            supported_cuda = await self._get_supported_cuda_versions(db)
            raise UnknownVersionError(
                component="cuda",
                version=cuda_version,
                known_versions=supported_cuda,
            )

    async def _validate_rocm_version(
        self, db: AsyncSession | None, rocm_version: str
    ) -> None:
        entry = await self._get_rocm_entry(db, rocm_version)
        if entry is None:
            supported_rocm = await self._get_supported_rocm_versions(db)
            raise UnknownVersionError(
                component="rocm",
                version=rocm_version,
                known_versions=supported_rocm,
            )

    async def _resolve_package(
        self,
        db: AsyncSession | None,
        constraint: PackageConstraint,
        python_version: str,
        cuda_version: str | None,
        rocm_version: str | None,
        override_version: str | None,
    ) -> ResolvedPackage:
        """
        Resolve a single package to a pinned version.

        If override_version is provided, validate it is compatible.
        Otherwise, select the latest compatible version.
        """
        package_name = constraint.name

        if override_version is not None:
            # Validate user override
            return await self._resolve_with_override(
                db=db,
                package_name=package_name,
                override_version=override_version,
                python_version=python_version,
                cuda_version=cuda_version,
                rocm_version=rocm_version,
            )

        # Use version from profile spec (treat as exact version if no range)
        spec_version = constraint.version_spec

        # Check if the version spec is an exact version (no operators)
        if not any(
            op in spec_version for op in [">=", "<=", "!=", ">", "<", "~=", "=="]
        ):
            # Exact version — validate it and use it directly
            return await self._resolve_exact_version(
                db=db,
                package_name=package_name,
                version=spec_version,
                python_version=python_version,
                cuda_version=cuda_version,
                rocm_version=rocm_version,
            )

        return await self._resolve_version_range(
            db=db,
            package_name=package_name,
            version_spec=spec_version,
            python_version=python_version,
            cuda_version=cuda_version,
            rocm_version=rocm_version,
            cuda_variant=constraint.cuda_variant,
        )

    async def _resolve_version_range(
        self,
        db: AsyncSession | None,
        package_name: str,
        version_spec: str,
        python_version: str,
        cuda_version: str | None,
        rocm_version: str | None,
        cuda_variant: str | None,
    ) -> ResolvedPackage:
        """
        Resolve a semantic version range and select the highest
        compatible version from the compatibility matrix.
        """
        entries = await self._get_framework_versions(db, package_name)

        # Package not in matrix — preserve existing behavior
        if not entries:
            return ResolvedPackage(
                name=package_name,
                version=version_spec,
                cuda_variant=cuda_variant,
            )

        try:
            spec = SpecifierSet(version_spec)
        except InvalidSpecifier as exc:
            raise IncompatibilityError(
                component=package_name,
                constraint=version_spec,
                detected="Invalid version specifier",
                suggestion="Provide a valid semantic version constraint.",
            ) from exc

        matching_entries = []

        for entry in entries:
            if python_version not in entry.supported_python:
                continue

            if cuda_version is not None and entry.supported_cuda:
                if cuda_version not in entry.supported_cuda:
                    continue

            if rocm_version is not None and entry.supported_rocm:
                if rocm_version not in entry.supported_rocm:
                    continue

            if Version(entry.version) in spec:
                matching_entries.append(entry)

        if not matching_entries:
            raise IncompatibilityError(
                component=package_name,
                constraint=version_spec,
                detected="No compatible versions found",
                suggestion=(
                    "No versions in the compatibility matrix satisfy "
                    "the requested constraint and environment."
                ),
            )

        matching_entries.sort(
            key=lambda entry: Version(entry.version),
            reverse=True,
        )

        selected = matching_entries[0]

        return await self._resolve_exact_version(
            db=db,
            package_name=package_name,
            version=selected.version,
            python_version=python_version,
            cuda_version=cuda_version,
            rocm_version=rocm_version,
        )

    async def _resolve_exact_version(
        self,
        db: AsyncSession | None,
        package_name: str,
        version: str,
        python_version: str,
        cuda_version: str | None,
        rocm_version: str | None,
    ) -> ResolvedPackage:
        """Validate an exact version against the matrix and return a ResolvedPackage."""
        entry = await self._get_framework_entry(db, package_name, version)
        if entry is None:
            # Not in matrix — use as-is (could be a helper package)
            return ResolvedPackage(name=package_name, version=version)

        # Validate Python compatibility
        if python_version not in entry.supported_python:
            raise IncompatibilityError(
                component="python",
                constraint=(
                    f"{package_name} {version} requires Python "
                    f"{entry.min_python}-{entry.max_python}"
                ),
                detected=f"Python {python_version}",
                suggestion=(
                    f"Use Python {entry.min_python}-{entry.max_python}, "
                    f"or select a different {package_name} version."
                ),
                docs_url="https://pytorch.org/get-started/locally/",
            )

        # Validate CUDA compatibility
        if cuda_version is not None and entry.supported_cuda:
            if cuda_version not in entry.supported_cuda:
                raise IncompatibilityError(
                    component="cuda",
                    constraint=(
                        f"{package_name} {version} supports CUDA: "
                        f"{', '.join(entry.supported_cuda)}"
                    ),
                    detected=f"CUDA {cuda_version}",
                    suggestion=(
                        f"Use CUDA {entry.supported_cuda[-1]} or select a "
                        f"different {package_name} version."
                    ),
                    docs_url="https://pytorch.org/get-started/locally/",
                )

        # Validate ROCm compatibility
        if rocm_version is not None and entry.supported_rocm:
            if rocm_version not in entry.supported_rocm:
                raise IncompatibilityError(
                    component="rocm",
                    constraint=(
                        f"{package_name} {version} supports ROCm: "
                        f"{', '.join(entry.supported_rocm)}"
                    ),
                    detected=f"ROCm {rocm_version}",
                    suggestion=(
                        f"Use ROCm {entry.supported_rocm[-1]} or select a "
                        f"different {package_name} version."
                    ),
                    docs_url="https://pytorch.org/get-started/locally/",
                )

        gpu_variant = self._resolve_gpu_variant(
            package_name, version, cuda_version, rocm_version
        )
        return ResolvedPackage(
            name=package_name,
            version=version,
            cuda_variant=gpu_variant,
        )

    async def _resolve_with_override(
        self,
        db: AsyncSession | None,
        package_name: str,
        override_version: str,
        python_version: str,
        cuda_version: str | None,
        rocm_version: str | None = None,
    ) -> ResolvedPackage:
        """Validate and apply a user-specified version override."""
        return await self._resolve_exact_version(
            db=db,
            package_name=package_name,
            version=override_version,
            python_version=python_version,
            cuda_version=cuda_version,
            rocm_version=rocm_version,
        )

    def _warn_on_abi_sensitive_hybrid_environment(
        self,
        resolved_packages: list[ResolvedPackage],
    ) -> list[str]:
        """Detect ABI-sensitive conda + pip hybrid package mixes."""
        has_gpu_wheel = any(pkg.cuda_variant for pkg in resolved_packages)
        has_non_gpu_package = any(not pkg.cuda_variant for pkg in resolved_packages)

        if has_gpu_wheel and has_non_gpu_package:
            return [
                (
                    "This profile mixes conda-managed packages with pip-installed "
                    "GPU wheel packages. Hybrid conda/pip environments are ABI-sensitive; "
                    "pip may resolve secondary dependencies and override Conda-managed binaries. "
                    "Review pins or use a conda-first profile."
                )
            ]
        return []

    @staticmethod
    def _resolve_gpu_variant(
        package_name: str,
        version: str,
        cuda_version: str | None,
        rocm_version: str | None,
    ) -> str | None:
        """Resolves specific GPU-accelerated variants (CUDA/ROCm) for targeted packages.

        e.g., torch 2.1.0 with CUDA 11.8 → variant = "cu118"
              torch 2.1.0 with ROCm 5.6 → variant = "rocm5.6"
        """
        gpu_packages = {"torch", "torchvision", "torchaudio", "onnxruntime-gpu", "cupy"}

        if package_name not in gpu_packages:
            return None

        if cuda_version is not None:
            return "cu" + cuda_version.replace(".", "")

        if rocm_version is not None:
            return "rocm" + rocm_version

        return None
