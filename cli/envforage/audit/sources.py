"""
Source abstractions for envforage audit.

A Source represents one environment we can compare. The MVP supports two:
    LocalEnvironment: the active Python interpreter, enumerated via `pip list`
    LockfileSource:   a requirements.txt-style file on disk

Future sources (poetry.lock, uv.lock, remote envforage envs via #85's REST API)
slot in by subclassing Source and yielding Package instances.
"""

from __future__ import annotations

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        try:
            from pip._vendor import tomli as tomllib  # type: ignore[no-redef,no-name-in-module]
        except ImportError:
            tomllib = None
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Optional, Union

from .models import Package


class Source:
    """Base class for audit sources. Subclasses yield Package instances."""

    name: str = "source"

    def packages(self) -> Iterator[Package]:
        raise NotImplementedError


class LocalEnvironment(Source):
    """Active Python environment, enumerated via `pip list --format=json`.

    Wraps the subprocess call with a timeout and converts any failure mode
    (timeout, non-zero exit, missing interpreter, malformed output) into a
    RuntimeError with a clear message, so the command layer can surface a
    clean error instead of a raw traceback.
    """

    name = "local"
    PIP_LIST_TIMEOUT_SECONDS = 30

    def __init__(self, python_executable: Optional[str] = None) -> None:
        self.python = python_executable or sys.executable

    def packages(self) -> Iterator[Package]:
        try:
            result = subprocess.run(
                [self.python, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.PIP_LIST_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"`pip list` did not complete within {self.PIP_LIST_TIMEOUT_SECONDS}s. "
                f"The active Python environment may be unresponsive."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip() or "<no stderr>"
            raise RuntimeError(
                f"`pip list` failed with exit code {exc.returncode}: {stderr}"
            ) from exc
        except (FileNotFoundError, OSError) as exc:
            raise RuntimeError(
                f"Could not execute Python interpreter at '{self.python}': {exc}"
            ) from exc

        try:
            entries = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("`pip list` returned malformed JSON output.") from exc

        for entry in entries:
            yield Package(name=entry["name"], version=entry["version"])


class LockfileSource(Source):
    """Requirements-format lockfile (one `package==version` per line).

    Handles inline `#` comments, blank lines, flag lines (`-r`, `--index-url`),
    extras (`pkg[extra]==1.0`), and environment markers
    (`pkg==1.0; python_version<'3.10'`) by stripping them. Lines without `==`
    are skipped since they can't be meaningfully diffed.
    """

    def __init__(self, path: Union[Path, str]) -> None:
        self.path = Path(path)
        self.name = f"lockfile:{self.path.name}"

    def packages(self) -> Iterator[Package]:
        try:
            content = self.path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RuntimeError(f"Lockfile not found: {self.path}") from exc
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"Lockfile is not valid UTF-8: {self.path} ({exc.reason})") from exc
        except (PermissionError, IsADirectoryError, OSError) as exc:
            raise RuntimeError(f"Could not read lockfile {self.path}: {exc}") from exc

        for raw_line in content.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue

            if "===" in line:
                separator = "==="
            elif "==" in line:
                separator = "=="
            else:
                continue

            name_part, version_part = line.split(separator, 1)
            name = name_part.split("[", 1)[0].split(";", 1)[0].strip()
            version = version_part.split(";", 1)[0].strip()
            if name and version:
                yield Package(name=name, version=version)


class ConfigFileSource(Source):
    """Reads a pyproject.toml file (Poetry or PEP 621 format) and extracts dependencies.

    Supports both the `[tool.poetry.dependencies]` section and the standardized
    PEP 621 `[project.dependencies]` format. Version specifiers with leading
    operators (`^`, `~`, `>=`, etc.) have the operator stripped so they can be
    compared against other sources. The `python` requirement is excluded since
    it's the Python version, not a dependency. Git, path, and URL dependencies
    are skipped (no comparable version).
    """

    def __init__(self, path) -> None:
        self.path = Path(path)
        self.name = f"pyproject:{self.path.name}"

    def packages(self) -> Iterator[Package]:
        if tomllib is None:
            raise RuntimeError(
                "No TOML parsing library found. Please install 'tomli' or run with Python 3.11+."
            )
        try:
            with open(self.path, "rb") as f:
                data = tomllib.load(f)
        except FileNotFoundError as exc:
            raise RuntimeError(f"Config file not found: {self.path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise RuntimeError(f"Invalid TOML in {self.path}: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise RuntimeError(
                f"Config file is not valid UTF-8: {self.path} ({exc.reason})"
            ) from exc
        except (PermissionError, IsADirectoryError, OSError) as exc:
            raise RuntimeError(f"Could not read config file {self.path}: {exc}") from exc

        # Parse Poetry format dependencies
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        for name, spec in poetry_deps.items():
            if name == "python":
                continue
            version = self._extract_version(spec)
            if version:
                yield Package(name=name, version=version)

        # Parse PEP 621 standard dependencies
        project_deps = data.get("project", {}).get("dependencies", [])
        for dep_str in project_deps:
            # Parse PEP 508 string (e.g., "requests>=2.31.0; python_version<'3.10'")
            # Simple parser for MVP: split on operators
            match = re.match(
                r"^([a-zA-Z0-9_\-\.]+)\s*(>=|==|<=|>|<|~=|!=)\s*([^;,\s]+)",
                dep_str.strip(),
            )
            if match:
                name, op, version = match.groups()
                if name != "python":
                    yield Package(name=name, version=version)

    @staticmethod
    def _extract_version(spec) -> Optional[str]:
        """Extract a comparable version string from a Poetry dep spec.

        spec is either:
        - a string like "2.31.0", "^2.31", "==2.31", ">=2.31,<3"
        - a dict like {"version": "2.31.0", "extras": [...]}
        - a dict like {"git": "..."} or {"path": "..."} -> no comparable version

        Returns None if no usable version can be extracted.
        """
        if isinstance(spec, dict):
            spec = spec.get("version")
            if not spec:
                return None  # git, path, or url dep

        if not isinstance(spec, str):
            return None

        # Strip leading operators: ^, ~, ==, >=, <=, >, <, !=
        stripped = spec.lstrip("^~<>=!")
        # Take the first part of compound specifiers like ">=2.31,<3"
        stripped = stripped.split(",")[0].strip()

        # Must look like a version (starts with a digit)
        if stripped and stripped[0].isdigit():
            return stripped
        return None
