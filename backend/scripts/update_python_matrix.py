import json
import sys
from pathlib import Path

# Add backend to path so we can import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from packaging.specifiers import SpecifierSet

from app.compatibility.matrix.python import PYTHON_MATRIX

MATRIX_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "compatibility"
    / "matrix"
    / "python_matrix_data.json"
)
SUPPORTED_PYTHONS = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]


def fetch_pypi_python_bounds(package: str, version: str):
    """Fetch required python bounds from PyPI, using a local file cache with a 12-hour TTL."""
    import os
    import time

    # Store cache under ~/.envforge/cache per issue #386 spec
    cache_dir = Path(os.path.expanduser("~/.envforge/cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    safe_pkg = "".join(c for c in package if c.isalnum() or c in ".-_")
    safe_ver = "".join(c for c in version if c.isalnum() or c in ".-_")
    cache_file = cache_dir / f"{safe_pkg}_{safe_ver}.json"

    data = None
    cache_valid = False

    # Check if cache file exists and is less than 12 hours (43200 seconds) old
    if cache_file.exists():
        try:
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < 43200:
                cache_valid = True
        except Exception as e:
            print(f"  [WARN] Failed to read cache file metadata: {e}")

    if cache_valid:
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
            print(f"  [Cache Hit] Loaded {package} {version} from local cache.")
        except Exception as e:
            print(f"  [WARN] Failed to read cache: {e}")

    if not data:
        url = f"https://pypi.org/pypi/{package}/{version}/json"
        print(f"  [Cache Miss] Fetching {url} from PyPI...")
        # Added 10s timeout to prevent hanging connections
        r = httpx.get(url, timeout=10)

        if r.status_code != 200:
            print(
                f"  [WARN] Failed to fetch {package} {version} (Status {r.status_code})"
            )
            return None

        data = r.json()

        # Save JSON to cache file
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"  [WARN] Failed to write cache: {e}")

    requires_python = data.get("info", {}).get("requires_python")

    if not requires_python:
        print(f"  [WARN] No requires_python found for {package} {version}")
        return None

    try:
        spec = SpecifierSet(requires_python)
    except Exception as e:
        print(f"  [WARN] Failed to parse specifier '{requires_python}': {e}")
        return None

    supported = []
    for py_ver in SUPPORTED_PYTHONS:
        # Check against x.y.0
        if spec.contains(f"{py_ver}.0"):
            supported.append(py_ver)

    if not supported:
        return None

    return {
        "min_python": supported[0],
        "max_python": supported[-1],
        "supported_python": supported,
    }


def main():
    print("Automating PyPI metadata retrieval for PYTHON_MATRIX...")

    # Check if JSON already exists; if so, load from it to allow continuous updates.
    # Otherwise, bootstrap from the currently imported PYTHON_MATRIX.
    if MATRIX_JSON_PATH.exists():
        print(f"Loading existing data from {MATRIX_JSON_PATH.name}")
        with open(MATRIX_JSON_PATH) as f:
            raw_data = json.load(f)
    else:
        print("Bootstrapping from hardcoded python.py...")
        from dataclasses import asdict

        raw_data = {
            fw: [asdict(entry) for entry in entries]
            for fw, entries in PYTHON_MATRIX.items()
        }

    updated_data = {}

    for framework, entries in raw_data.items():
        updated_data[framework] = []
        for entry in entries:
            version = entry["version"]
            bounds = fetch_pypi_python_bounds(framework, version)

            if bounds:
                entry["min_python"] = bounds["min_python"]
                entry["max_python"] = bounds["max_python"]
                entry["supported_python"] = bounds["supported_python"]
                print(f"  Updated {framework} {version}: {bounds['supported_python']}")
            else:
                print(f"  Kept original bounds for {framework} {version}")

            updated_data[framework].append(entry)

    print(f"\nWriting updated matrix to {MATRIX_JSON_PATH.name}...")
    with open(MATRIX_JSON_PATH, "w") as f:
        json.dump(updated_data, f, indent=4)

    print("Done! You can now configure python.py to load from this JSON file.")


if __name__ == "__main__":
    main()
