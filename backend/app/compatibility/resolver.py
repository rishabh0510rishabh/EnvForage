"""
Compatibility Resolver — the core decision-making engine.

This module is PURE: no I/O, no database calls, no network, no side effects.
Every function is deterministic: same inputs → same outputs.

Usage:
    from app.compatibility.resolver import CompatibilityResolver
    from app.compatibility.models import PackageConstraint

    resolver = CompatibilityResolver()
    resolved = resolver.resolve(
        packages=[PackageConstraint("torch", "2.1.0", "cu118")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        cuda_required=True,
    )
"""
from app.compatibility.errors import (
    IncompatibilityError,
    UnknownVersionError,
    UnsupportedOSError,
)
from app.compatibility.matrix.cuda import (
    CUDA_MATRIX,
    get_cuda_entry,
)
from app.compatibility.matrix.os_rules import get_os_notes
from app.compatibility.matrix.python import (
    get_framework_entry,
    get_latest_compatible_version,
)
from app.compatibility.matrix.rocm import (
    ROCM_MATRIX,
    get_rocm_entry,
)
from app.compatibility.models import (
    OSTarget,
    PackageConstraint,
    ResolvedEnvironment,
    ResolvedPackage,
)


class CompatibilityResolver:
    """
    Resolves a set of package constraints + environment constraints into a
    fully validated, pinned ResolvedEnvironment.

    All incompatibilities raise structured IncompatibilityError exceptions
    with actionable messages — never bare strings.
    """

    def resolve(
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
    ) -> ResolvedEnvironment:
        """
        Main resolution entry point.

        Args:
            packages: List of package constraints from the profile
            python_version: Requested Python version, e.g. "3.11"
            cuda_version: Requested CUDA version, e.g. "12.1", or None for CPU
            target_os: Target OS: "LINUX" | "WSL" | "WIN"
            profile_slug: Profile identifier for error messages
            os_support: OS targets this profile supports
            cuda_required: Whether CUDA is mandatory for this profile
            overrides: User-specified version overrides {package_name: version}

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
            raise IncompatibilityError(
                component="cuda",
                constraint=f"Profile '{profile_slug}' requires CUDA",
                detected="No CUDA version specified",
                suggestion=(
                    "Provide a cuda_version in your request. "
                    f"Supported: {', '.join(CUDA_MATRIX.keys())}"
                ),
            )

        if cuda_version is not None:
            self._validate_cuda_version(cuda_version)

        if rocm_required and rocm_version is None:
            raise IncompatibilityError(
                component="rocm",
                constraint=f"Profile '{profile_slug}' requires ROCm",
                detected="No ROCm version specified",
                suggestion=(
                    "Provide a rocm_version in your request. "
                    f"Supported: {', '.join(ROCM_MATRIX.keys())}"
                ),
            )

        if rocm_version is not None:
            self._validate_rocm_version(rocm_version)

        # Step 3: Resolve each package
        resolved_packages: list[ResolvedPackage] = []
        for constraint in packages:
            resolved = self._resolve_package(
                constraint=constraint,
                python_version=python_version,
                cuda_version=cuda_version,
                rocm_version=rocm_version,
                override_version=overrides.get(constraint.name),
            )
            resolved_packages.append(resolved)

        # Step 4: Collect OS-specific notes
        framework_names = [p.name for p in packages]
        gpu_required = cuda_required or rocm_required
        os_notes = get_os_notes(target_os, gpu_required, framework_names)
        warnings.extend(os_notes)

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

    def _validate_cuda_version(self, cuda_version: str) -> None:
        entry = get_cuda_entry(cuda_version)
        if entry is None:
            raise UnknownVersionError(
                component="cuda",
                version=cuda_version,
                known_versions=list(CUDA_MATRIX.keys()),
            )

    def _validate_rocm_version(self, rocm_version: str) -> None:
        entry = get_rocm_entry(rocm_version)
        if entry is None:
            raise UnknownVersionError(
                component="rocm",
                version=rocm_version,
                known_versions=list(ROCM_MATRIX.keys()),
            )

    def _resolve_package(
        self,
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
            return self._resolve_with_override(
                package_name=package_name,
                override_version=override_version,
                python_version=python_version,
                cuda_version=cuda_version,
            )

        # Use version from profile spec (treat as exact version if no range)
        spec_version = constraint.version_spec

        # Check if the version spec is an exact version (no operators)
        if not any(op in spec_version for op in [">=", "<=", "!=", ">", "<", "~="]):
            # Exact version — validate it and use it directly
            return self._resolve_exact_version(
                package_name=package_name,
                version=spec_version,
                python_version=python_version,
                cuda_version=cuda_version,
                rocm_version=rocm_version,
            )

        # Range spec — find the latest compatible version within range
        # For now, defer to the matrix for well-known packages
        latest = get_latest_compatible_version(
            framework=package_name,
            python_version=python_version,
            cuda_version=cuda_version,
            rocm_version=rocm_version,
        )
        if latest is not None:
            gpu_variant = self._resolve_gpu_variant(
                package_name, latest, cuda_version, rocm_version
            )
            return ResolvedPackage(
                name=package_name,
                version=latest,
                cuda_variant=gpu_variant,
            )

        # Package not in matrix — use spec as-is with a warning
        # (e.g., pip, setuptools, or other non-framework packages)
        return ResolvedPackage(
            name=package_name,
            version=spec_version.lstrip(">=<!=~"),
            cuda_variant=constraint.cuda_variant,
        )

    def _resolve_exact_version(
        self,
        package_name: str,
        version: str,
        python_version: str,
        cuda_version: str | None,
        rocm_version: str | None,
    ) -> ResolvedPackage:
        """Validate an exact version against the matrix and return a ResolvedPackage."""
        entry = get_framework_entry(package_name, version)
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

    def _resolve_with_override(
        self,
        package_name: str,
        override_version: str,
        python_version: str,
        cuda_version: str | None,
        rocm_version: str | None = None,
    ) -> ResolvedPackage:
        """Validate and apply a user-specified version override."""
        return self._resolve_exact_version(
            package_name=package_name,
            version=override_version,
            python_version=python_version,
            cuda_version=cuda_version,
            rocm_version=rocm_version,
        )

    @staticmethod
    def _resolve_gpu_variant(
        package_name: str,
        version: str,
        cuda_version: str | None,
        rocm_version: str | None,
    ) -> str | None:
        """
        Determine the pip install variant suffix for a package.
        e.g., torch 2.1.0 with CUDA 11.8 → variant = "cu118"
              torch 2.1.0 with ROCm 5.6 → variant = "rocm5.6"
        """
        if cuda_version is not None:
            if package_name not in ("torch", "torchvision", "torchaudio"):
                return None
            return "cu" + cuda_version.replace(".", "")

        if rocm_version is not None:
            if package_name not in ("torch", "torchvision", "torchaudio"):
                return None
            return "rocm" + rocm_version

        return None
