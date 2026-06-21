from pathlib import Path
import re


ENV_PATTERNS = [
    r'os\.getenv\(["\']([A-Z0-9_]+)["\']',
    r'os\.environ\.get\(["\']([A-Z0-9_]+)["\']',
    r'os\.environ\[\s*["\']([A-Z0-9_]+)["\']\s*\]',
]


def find_used_variables(project_path: str) -> set[str]:
    used = set()

    for py_file in Path(project_path).rglob("*.py"):
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