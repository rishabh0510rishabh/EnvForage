from __future__ import annotations
import shutil
import sys


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def check_python_version(
    minimum: tuple[int, int] = (3, 10),
) -> ValidationResult:
    result = ValidationResult()

    if sys.version_info < minimum:
        result.errors.append(
            f"Python {minimum[0]}.{minimum[1]}+ is required. "
            f"Found {sys.version_info.major}.{sys.version_info.minor}."
        )

    return result


def check_git_installed() -> ValidationResult:
    result = ValidationResult()

    if shutil.which("git") is None:
        result.errors.append(
            "Git is not installed or not available in PATH."
        )

    return result


def check_docker_installed() -> ValidationResult:
    result = ValidationResult()

    if shutil.which("docker") is None:
        result.errors.append(
            "Docker is not installed or not available in PATH."
        )

    return result


def validate_environment() -> ValidationResult:
    result = ValidationResult()

    checks = [
        check_python_version(),
        check_git_installed(),
        check_docker_installed(),
    ]

    for check in checks:
        result.errors.extend(check.errors)
        result.warnings.extend(check.warnings)

    return result