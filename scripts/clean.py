#!/usr/bin/env python3
"""Remove locally generated build/test/cache artifacts.

Mirrors the generated paths in .gitignore so a developer can clean a working
tree without deleting environment or state. Virtualenvs, .env files, databases,
and Docker volumes are intentionally left alone, since those are environment or
state rather than build artifacts.

Usage:
    python scripts/clean.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directory names removed wherever they occur in the tree.
DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    ".eggs",
}

# Directory-name glob patterns removed wherever they occur (e.g. foo.egg-info).
DIR_PATTERNS = ("*.egg-info",)

# File glob patterns removed wherever they occur.
FILE_PATTERNS = ("*.pyc", "*.pyo", "*.pyd", "*.egg", "*.log")

# Specific paths (relative to repo root) removed if present.
EXACT_PATHS = (
    "build",
    "dist",
    "generated",
    "logs",
    ".coverage",
    "coverage.xml",
    "backend/.coverage",
    "backend/coverage.xml",
    "frontend/.next",
    "frontend/out",
)


def _rm(path: Path) -> None:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists() or path.is_symlink():
            path.unlink(missing_ok=True)
        else:
            return
        print(f"removed {path.relative_to(ROOT)}")
    except Exception as exc:  # best-effort cleanup
        print(f"skip {path}: {exc}")


def main() -> None:
    for name in DIR_NAMES:
        for path in ROOT.rglob(name):
            if path.is_dir():
                _rm(path)

    for pattern in DIR_PATTERNS:
        for path in ROOT.rglob(pattern):
            if path.is_dir():
                _rm(path)

    for pattern in FILE_PATTERNS:
        for path in ROOT.rglob(pattern):
            if path.is_file():
                _rm(path)

    for rel in EXACT_PATHS:
        _rm(ROOT / rel)


if __name__ == "__main__":
    main()