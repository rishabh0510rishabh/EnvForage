import json
import sys
import logging
logging.basicConfig(level=logging.INFO)
import urllib.error
import urllib.request


def fetch_pypi_python_requires(package: str, version: str | None = None) -> None:
    """
    Fetches the Requires-Python metadata from PyPI for a given package and version.
    This script is used to automate the verification of Python compatibility matrices.
    Uses local JSON file-based caching inside `~/.envforge/cache` to optimize performance with a 12-hour TTL.
    """
    import os
    import time

    # Store cache under ~/.envforge/cache per issue #386 spec
    cache_dir = os.path.expanduser("~/.envforge/cache")
    os.makedirs(cache_dir, exist_ok=True)

    safe_pkg = "".join(c for c in package if c.isalnum() or c in ".-_")
    safe_ver = (
        "".join(c for c in version if c.isalnum() or c in ".-_")
        if version
        else "latest"
    )
    cache_file = os.path.join(cache_dir, f"{safe_pkg}_{safe_ver}.json")

    data = None
    cache_valid = False

    # Check if cache file exists and is less than 12 hours (43200 seconds) old
    if os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 43200:
                cache_valid = True
        except Exception as e:
            logging.warning(f"Failed to read cache file metadata: {e}")

    if cache_valid:
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
            print(
                f"[Cache Hit] Loaded metadata for {package} {version or 'latest'} from local cache."
            )
        except Exception as e:
            print(f"[WARN] Failed to read cache: {e}")

    if not data:
        url = f"https://pypi.org/pypi/{package}/json"
        if version:
            url = f"https://pypi.org/pypi/{package}/{version}/json"

        try:
            print(
                f"[Cache Miss] Fetching metadata for {package} {version or 'latest'} from PyPI..."
            )
            req = urllib.request.Request(url, headers={"User-Agent": "EnvForage/1.0"})
            # Added 10s timeout to prevent hanging connections
            with urllib.request.urlopen(req, timeout=10) as response:
                raw_response = response.read().decode("utf-8")
                data = json.loads(raw_response)

            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(raw_response)
            except Exception as e:
                print(f"[WARN] Failed to write cache: {e}")

        except urllib.error.HTTPError as e:
            print(
                f"Failed to fetch metadata for {package} {version or ''}: HTTP {e.code}"
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error fetching metadata: {e}")
            sys.exit(1)

    info = data.get("info", {})
    pkg_version = info.get("version", "unknown")
    requires_python = info.get("requires_python", "Not specified")

    print(f"Package: {package}")
    print(f"Version: {pkg_version}")
    print(f"Requires-Python: {requires_python}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_pypi_metadata.py <package_name> [version]")
        sys.exit(1)

    pkg = sys.argv[1]
    ver = sys.argv[2] if len(sys.argv) > 2 else None
    fetch_pypi_python_requires(pkg, ver)
