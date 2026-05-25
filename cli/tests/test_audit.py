"""Unit tests for envforge audit (#181 MVP)."""
from __future__ import annotations
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner

import subprocess
from unittest.mock import patch

from envforge_agent.audit import (
    audit_command,
    diff,
    LocalEnvironment,
    LockfileSource,
    Package,
)
from envforge_agent.audit.differ import _classify_version_change
from envforge_agent.audit.models import _normalize_name


class TestPackageNormalization:
    def test_lowercases_name(self):
        assert Package(name="Pillow", version="10.0.0").name == "pillow"

    def test_collapses_separators(self):
        assert Package(name="pytest_asyncio", version="0.21").name == "pytest-asyncio"
        assert Package(name="my.pkg", version="1.0").name == "my-pkg"

    def test_collapses_multiple_runs(self):
        assert _normalize_name("Foo___Bar...Baz") == "foo-bar-baz"


class TestVersionClassification:
    def test_major_change(self):
        assert _classify_version_change("1.0.0", "2.0.0") == "major"

    def test_minor_change(self):
        assert _classify_version_change("1.0.0", "1.1.0") == "minor"

    def test_patch_change(self):
        assert _classify_version_change("1.0.0", "1.0.1") == "patch"

    def test_non_numeric_falls_to_other(self):
        assert _classify_version_change("1.0.0", "1.0.0-rc1") == "other"

    def test_short_versions_handled(self):
        assert _classify_version_change("1", "1.0.1") == "patch"


class TestLockfileSource:
    def test_parses_pinned_packages(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        lockfile.write_text("django==4.2.0\nrequests==2.31.0\n")
        packages = list(LockfileSource(lockfile).packages())
        assert Package(name="django", version="4.2.0") in packages
        assert Package(name="requests", version="2.31.0") in packages
        assert len(packages) == 2

    def test_skips_comments_and_blank_lines(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        lockfile.write_text(
            "# This is a comment\n\ndjango==4.2.0  # inline comment\n\n"
        )
        packages = list(LockfileSource(lockfile).packages())
        assert packages == [Package(name="django", version="4.2.0")]

    def test_skips_flag_lines(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        lockfile.write_text(
            "-r requirements-dev.txt\n"
            "--index-url https://pypi.org/simple\n"
            "django==4.2.0\n"
        )
        packages = list(LockfileSource(lockfile).packages())
        assert packages == [Package(name="django", version="4.2.0")]

    def test_skips_unpinned_lines(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        lockfile.write_text("django>=4.0\nrequests==2.31.0\n")
        packages = list(LockfileSource(lockfile).packages())
        assert packages == [Package(name="requests", version="2.31.0")]

    def test_handles_extras(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        lockfile.write_text("django[bcrypt]==4.2.0\n")
        packages = list(LockfileSource(lockfile).packages())
        assert packages == [Package(name="django", version="4.2.0")]

    def test_handles_environment_markers(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        lockfile.write_text("django==4.2.0; python_version<'3.10'\n")
        packages = list(LockfileSource(lockfile).packages())
        assert packages == [Package(name="django", version="4.2.0")]

    def test_raises_on_missing_file(self):
        with pytest.raises(RuntimeError, match=r"not found"):
            list(LockfileSource("/does/not/exist.txt").packages())

    def test_raises_on_invalid_utf8(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        # Write bytes that are NOT valid UTF-8 (lone continuation bytes)
        lockfile.write_bytes(b"django==4.2.0\n\xff\xfe garbage\n")
        with pytest.raises(RuntimeError, match=r"not valid UTF-8"):
            list(LockfileSource(lockfile).packages())
    
    def test_handles_arbitrary_equality(self, tmp_path: Path):
        """PEP 440 === (arbitrary equality) should parse correctly,
        not as == with a leading '=' in the version."""
        lockfile = tmp_path / "req.txt"
        lockfile.write_text("mypackage===1.0.local+build\n")
        packages = list(LockfileSource(lockfile).packages())
        assert packages == [Package(name="mypackage", version="1.0.local+build")]


class _StubSource:
    """Test double — yields a fixed list of packages."""

    def __init__(self, name: str, packages: List[Package]) -> None:
        self.name = name
        self._packages = packages

    def packages(self):
        return iter(self._packages)


class TestDiff:
    def test_identical_environments_have_no_drift(self):
        a = _StubSource("a", [Package("django", "4.2.0"), Package("requests", "2.31.0")])
        b = _StubSource("b", [Package("django", "4.2.0"), Package("requests", "2.31.0")])
        result = diff(a, b)
        assert not result.has_drift()
        assert result.common_count == 2

    def test_detects_added_packages(self):
        a = _StubSource("a", [Package("django", "4.2.0")])
        b = _StubSource("b", [Package("django", "4.2.0"), Package("requests", "2.31.0")])
        result = diff(a, b)
        added = [d for d in result.differences if d.severity == "added"]
        assert len(added) == 1
        assert added[0].package == "requests"
        assert added[0].a_version is None
        assert added[0].b_version == "2.31.0"

    def test_detects_removed_packages(self):
        a = _StubSource("a", [Package("django", "4.2.0"), Package("legacy", "1.0.0")])
        b = _StubSource("b", [Package("django", "4.2.0")])
        result = diff(a, b)
        removed = [d for d in result.differences if d.severity == "removed"]
        assert len(removed) == 1
        assert removed[0].package == "legacy"

    def test_classifies_version_changes(self):
        a = _StubSource("a", [
            Package("django", "4.2.0"),
            Package("requests", "2.31.0"),
            Package("numpy", "1.24.0"),
        ])
        b = _StubSource("b", [
            Package("django", "5.0.0"),
            Package("requests", "2.32.0"),
            Package("numpy", "1.24.1"),
        ])
        result = diff(a, b)
        by_pkg = {d.package: d.severity for d in result.differences}
        assert by_pkg["django"] == "major"
        assert by_pkg["requests"] == "minor"
        assert by_pkg["numpy"] == "patch"


class TestAuditCommand:
    def test_audit_with_two_lockfiles(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b)])
        assert result.exit_code == 0
        normalized = result.output.lower()
        assert "django" in normalized
        assert "major" in normalized

    def test_audit_identical_lockfiles_reports_no_drift(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==4.2.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b)])
        assert result.exit_code == 0
        assert "no drift" in result.output.lower()

    def test_audit_invalid_source_errors(self):
        result = CliRunner().invoke(audit_command, ["/does/not/exist.txt", "local"])
        assert result.exit_code == 2
        assert "could not interpret source" in result.output.lower()
        
class TestLocalEnvironmentErrors:
    @patch("envforge_agent.audit.sources.subprocess.run")
    def test_timeout_raises_runtime_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pip", timeout=30)
        with pytest.raises(RuntimeError, match=r"did not complete"):
            list(LocalEnvironment().packages())

    @patch("envforge_agent.audit.sources.subprocess.run")
    def test_pip_failure_raises_runtime_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="pip", stderr="permission denied"
        )
        with pytest.raises(RuntimeError, match=r"failed with exit code 1"):
            list(LocalEnvironment().packages())

    @patch("envforge_agent.audit.sources.subprocess.run")
    def test_malformed_pip_output_raises_runtime_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not valid json", stderr=""
        )
        with pytest.raises(RuntimeError, match=r"malformed JSON"):
            list(LocalEnvironment().packages())
            
    @patch("envforge_agent.audit.sources.subprocess.run")
    def test_missing_interpreter_raises_runtime_error(self, mock_run):
        mock_run.side_effect = FileNotFoundError("python not found")
        with pytest.raises(RuntimeError, match=r"Could not execute Python interpreter"):
            list(LocalEnvironment(python_executable="/bad/python").packages())