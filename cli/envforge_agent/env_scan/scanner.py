import os
import re
from pathlib import Path

EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    "site-packages",
    ".git",
}

ENV_PATTERNS = [
    r'os\.getenv\(\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']',
    r'os\.environ\.get\(\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']',
    r'os\.environ\[\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']\s*\]',
]


def find_used_variables(project_path: str) -> set[str]:
    used = set()

    for root, dirs, files in os.walk(project_path, topdown=True):
        # Prune excluded directories before descending into them
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            if not file.endswith(".py"):
                continue

            py_file = Path(root) / file

            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue

            for pattern in ENV_PATTERNS:
                used.update(re.findall(pattern, content))

    return used


def read_env_file(path: str) -> set[str]:
    variables = set()

    env_file = Path(path)

    if not env_file.exists():
        return variables

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key = line.split("=", 1)[0].strip()
            variables.add(key)

    return variables