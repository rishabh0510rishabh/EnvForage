"""
Source abstractions for envforge audit.

A Source represents one environment we can compare. The MVP supports two:
    LocalEnvironment: the active Python interpreter, enumerated via `pip list`
    LockfileSource:   a requirements.txt-style file on disk

Future sources (poetry.lock, uv.lock, remote envforge envs via #85's REST API)
slot in by subclassing Source and yielding Package instances.
"""
from __future__ import annotations
import json
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
            raise RuntimeError(
                f"`pip list` returned malformed JSON output."
            ) from exc

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
            raise RuntimeError(
                f"Lockfile is not valid UTF-8: {self.path} ({exc.reason})"
            ) from exc
        except (PermissionError, IsADirectoryError, OSError) as exc:
            raise RuntimeError(
                f"Could not read lockfile {self.path}: {exc}"
            ) from exc

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