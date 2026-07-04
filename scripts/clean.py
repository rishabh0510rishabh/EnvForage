#!/usr/bin/env python3
"""Remove locally generated build/test/cache artifacts.

Mirrors the generated paths in .gitignore so a developer can clean a working
tree without deleting environment or state. Virtualenvs, node_modules, .env
files, databases, and Docker volumes are intentionally left alone, since those
are environment or state rather than build artifacts.

Usage:
    python scripts/clean.py
"""

from __future__ import annotations

import fnmatch
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories we never descend into: virtualenvs, dependencies, VCS, and state.
# Pruned in-place during the walk so installed packages (e.g. compiled .pyd
# files inside a venv) are never touched and the tree is traversed only once.
PRUNE_DIRS = {
    ".venv",
    "venv",
    "env",
    "ENV",
    "node_modules",
    ".git",
    "postgres_data",
}

# Directory names removed wherever they occur (outside pruned dirs).
DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    ".eggs",
}

# Directory-name glob patterns removed wherever they occur.
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
    # Single top-down walk: prune ignored directories in place so we never
    # descend into them, and remove matching artifact dirs/files as we go.
    for dirpath, dirnames, filenames in os.walk(ROOT, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]

        for d in list(dirnames):
            if d in DIR_NAMES or any(fnmatch.fnmatch(d, p) for p in DIR_PATTERNS):
                _rm(Path(dirpath) / d)
                dirnames.remove(d)  # don't descend into a dir we just removed

        for f in filenames:
            if any(fnmatch.fnmatch(f, p) for p in FILE_PATTERNS):
                _rm(Path(dirpath) / f)

    for rel in EXACT_PATHS:
        _rm(ROOT / rel)


if __name__ == "__main__":
    main()