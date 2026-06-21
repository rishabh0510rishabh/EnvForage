"""Unit tests for envforage audit (#181 MVP)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner

import subprocess
from unittest.mock import patch

from envforage.audit import (
    audit_command,
    diff,
    ConfigFileSource,
    LocalEnvironment,
    LockfileSource,
    Package,
)
from envforage.audit.formatters import format_json, format_sarif
from envforage.audit.differ import _classify_version_change
from envforage.audit.models import AuditResult, _normalize_name


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
        assert _classify_version_change("1.0.0", "abc") == "other"

    def test_short_versions_handled(self):
        assert _classify_version_change("1", "1.0.1") == "patch"

    def test_pre_release_handled_accurately(self):
        assert _classify_version_change("2.1.0-rc1", "2.1.0") == "patch"
        assert _classify_version_change("2.1.0-rc1", "2.1.0-rc2") == "patch"
        assert _classify_version_change("2.0.0", "2.1.0-rc1") == "minor"
        assert _classify_version_change("1.0.0", "2.0.0-rc1") == "major"
        assert _classify_version_change("1.0.0", "1.0.0") == "other"
        assert _classify_version_change(None, "1.0.0") == "other"
        assert _classify_version_change("1.0.0", None) == "other"


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
        lockfile.write_text("# This is a comment\n\ndjango==4.2.0  # inline comment\n\n")
        packages = list(LockfileSource(lockfile).packages())
        assert packages == [Package(name="django", version="4.2.0")]

    def test_skips_flag_lines(self, tmp_path: Path):
        lockfile = tmp_path / "req.txt"
        lockfile.write_text(
            "-r requirements-dev.txt\n--index-url https://pypi.org/simple\ndjango==4.2.0\n"
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
        a = _StubSource(
            "a",
            [
                Package("django", "4.2.0"),
                Package("requests", "2.31.0"),
                Package("numpy", "1.24.0"),
            ],
        )
        b = _StubSource(
            "b",
            [
                Package("django", "5.0.0"),
                Package("requests", "2.32.0"),
                Package("numpy", "1.24.1"),
            ],
        )
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
    @patch("envforage.audit.sources.subprocess.run")
    def test_timeout_raises_runtime_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pip", timeout=30)
        with pytest.raises(RuntimeError, match=r"did not complete"):
            list(LocalEnvironment().packages())

    @patch("envforage.audit.sources.subprocess.run")
    def test_pip_failure_raises_runtime_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="pip", stderr="permission denied"
        )
        with pytest.raises(RuntimeError, match=r"failed with exit code 1"):
            list(LocalEnvironment().packages())

    @patch("envforage.audit.sources.subprocess.run")
    def test_malformed_pip_output_raises_runtime_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not valid json", stderr=""
        )
        with pytest.raises(RuntimeError, match=r"malformed JSON"):
            list(LocalEnvironment().packages())

    @patch("envforage.audit.sources.subprocess.run")
    def test_missing_interpreter_raises_runtime_error(self, mock_run):
        mock_run.side_effect = FileNotFoundError("python not found")
        with pytest.raises(RuntimeError, match=r"Could not execute Python interpreter"):
            list(LocalEnvironment(python_executable="/bad/python").packages())


class TestJsonFormatter:
    def test_format_json_no_drift(self):
        # Use a synthetic empty result via direct construction
        from envforage.audit.models import AuditResult

        result = AuditResult(
            source_a="lockfile:a.txt",
            source_b="lockfile:b.txt",
            differences=[],
            common_count=5,
        )
        payload = json.loads(format_json(result))
        assert payload["source_a"] == "lockfile:a.txt"
        assert payload["source_b"] == "lockfile:b.txt"
        assert payload["differences"] == []
        assert payload["summary"]["total"] == 0
        assert payload["summary"]["common_count"] == 5

    def test_format_json_with_drift(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\nrequests==2.31.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\nrequests==2.32.0\n")

        result = diff(LockfileSource(a), LockfileSource(b))
        payload = json.loads(format_json(result))

        assert payload["summary"]["total"] == 2
        assert payload["summary"]["by_severity"]["major"] == 1
        assert payload["summary"]["by_severity"]["minor"] == 1

        packages = {entry["package"] for entry in payload["differences"]}
        assert packages == {"django", "requests"}


class TestSarifFormatter:
    def test_format_sarif_structure(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = diff(LockfileSource(a), LockfileSource(b))
        sarif = json.loads(format_sarif(result))

        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        assert len(sarif["runs"]) == 1
        run = sarif["runs"][0]
        assert run["tool"]["driver"]["name"] == "envforage-audit"
        assert len(run["results"]) == 1
        assert run["results"][0]["ruleId"] == "drift-major"
        assert run["results"][0]["level"] == "error"

    def test_format_sarif_severity_mapping(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("a==1.0.0\nb==1.0.0\nc==1.0.0\n")
        b = tmp_path / "b.txt"
        b.write_text("a==2.0.0\nb==1.1.0\nc==1.0.1\n")

        result = diff(LockfileSource(a), LockfileSource(b))
        sarif = json.loads(format_sarif(result))
        results = sarif["runs"][0]["results"]

        levels_by_severity = {r["ruleId"].replace("drift-", ""): r["level"] for r in results}
        assert levels_by_severity["major"] == "error"
        assert levels_by_severity["minor"] == "warning"
        assert levels_by_severity["patch"] == "note"


class TestAuditCommandOutputFormats:
    def test_json_flag_outputs_valid_json(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b), "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["summary"]["total"] == 1

    def test_sarif_flag_outputs_valid_sarif(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b), "--sarif"])
        assert result.exit_code == 0
        sarif = json.loads(result.output)
        assert sarif["version"] == "2.1.0"

    def test_json_and_sarif_mutually_exclusive(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b), "--json", "--sarif"])
        assert result.exit_code == 2
        assert "mutually exclusive" in result.output.lower()


class TestDriftScore:
    def test_no_drift_score_is_zero(self):
        result = AuditResult(source_a="a", source_b="b", differences=[], common_count=5)
        assert result.drift_score == 0

    def test_drift_score_weighted_by_severity(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\nrequests==2.31.0\nnumpy==1.24.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\nrequests==2.32.0\nnumpy==1.24.1\n")

        result = diff(LockfileSource(a), LockfileSource(b))
        # Expected: major=10 + minor=3 + patch=1 = 14
        assert result.drift_score == 14

    def test_drift_score_includes_added_and_removed(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("only_in_a==1.0.0\n")
        b = tmp_path / "b.txt"
        b.write_text("only_in_b==1.0.0\n")

        result = diff(LockfileSource(a), LockfileSource(b))
        # Expected: added=2 + removed=2 = 4
        assert result.drift_score == 4

    def test_drift_score_in_json_output(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = diff(LockfileSource(a), LockfileSource(b))
        payload = json.loads(format_json(result))
        assert payload["summary"]["drift_score"] == 10  # major drift


class TestStrictFlag:
    def test_strict_with_drift_exits_one(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b), "--strict"])
        assert result.exit_code == 1

    def test_strict_with_no_drift_exits_zero(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==4.2.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b), "--strict"])
        assert result.exit_code == 0

    def test_no_strict_with_drift_exits_zero(self, tmp_path: Path):
        a = tmp_path / "a.txt"
        a.write_text("django==4.2.0\n")
        b = tmp_path / "b.txt"
        b.write_text("django==5.0.0\n")

        result = CliRunner().invoke(audit_command, [str(a), str(b)])
        assert result.exit_code == 0


class TestConfigFileSource:
    def test_parses_direct_version_strings(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.poetry.dependencies]\npython = "^3.11"\nrequests = "2.31.0"\ndjango = "4.2.0"\n'
        )
        packages = sorted(ConfigFileSource(pyproject).packages(), key=lambda p: p.name)
        assert packages == [
            Package(name="django", version="4.2.0"),
            Package(name="requests", version="2.31.0"),
        ]

    def test_strips_caret_and_tilde_operators(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry.dependencies]\nrequests = "^2.31"\ndjango = "~4.2"\n')
        packages = sorted(ConfigFileSource(pyproject).packages(), key=lambda p: p.name)
        assert packages == [
            Package(name="django", version="4.2"),
            Package(name="requests", version="2.31"),
        ]

    def test_strips_equality_and_comparison_operators(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.poetry.dependencies]\npkg-a = "==1.0.0"\npkg-b = ">=2.0,<3.0"\n'
        )
        packages = sorted(ConfigFileSource(pyproject).packages(), key=lambda p: p.name)
        assert packages == [
            Package(name="pkg-a", version="1.0.0"),
            Package(name="pkg-b", version="2.0"),  # first part of compound
        ]

    def test_parses_table_format_with_version(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.poetry.dependencies]\nrequests = { version = "2.31.0", extras = ["security"] }\n'
        )
        packages = list(ConfigFileSource(pyproject).packages())
        assert packages == [Package(name="requests", version="2.31.0")]

    def test_skips_git_and_path_dependencies(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[tool.poetry.dependencies]\n"
            'mylib = { git = "https://github.com/example/mylib.git" }\n'
            'localpkg = { path = "../localpkg" }\n'
            'requests = "2.31.0"\n'
        )
        packages = list(ConfigFileSource(pyproject).packages())
        assert packages == [Package(name="requests", version="2.31.0")]

    def test_skips_python_key(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry.dependencies]\npython = "^3.11"\nrequests = "2.31.0"\n')
        names = [p.name for p in ConfigFileSource(pyproject).packages()]
        assert "python" not in names

    def test_empty_pyproject_yields_no_packages(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\nrequires = []\n")
        assert list(ConfigFileSource(pyproject).packages()) == []

    def test_raises_on_invalid_toml(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is { not valid toml")
        with pytest.raises(RuntimeError, match=r"Invalid TOML"):
            list(ConfigFileSource(pyproject).packages())

    def test_raises_on_missing_file(self):
        with pytest.raises(RuntimeError, match=r"not found"):
            list(ConfigFileSource("/does/not/exist.toml").packages())

    def test_parses_pep_621_dependencies(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            "dependencies = [\n"
            '    "requests>=2.31.0",\n'
            "    \"django==4.2rc1; python_version < '3.10'\",\n"
            '    "numpy~=1.24.0rc3",\n'
            '    "pandas<=2.0.0",\n'
            '    "pkg!=1.2.0"\n'
            "]\n"
        )
        packages = sorted(ConfigFileSource(pyproject).packages(), key=lambda p: p.name)
        assert packages == [
            Package(name="django", version="4.2rc1"),
            Package(name="numpy", version="1.24.0rc3"),
            Package(name="pandas", version="2.0.0"),
            Package(name="pkg", version="1.2.0"),
            Package(name="requests", version="2.31.0"),
        ]

    def test_pep_621_skips_python_key(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "python>=3.11",\n    "requests>=2.31.0"\n]\n'
        )
        names = [p.name for p in ConfigFileSource(pyproject).packages()]
        assert "python" not in names
        assert names == ["requests"]

    def test_pep_621_skips_no_version_specifier(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "requests",\n    "django>=4.2.0"\n]\n'
        )
        packages = list(ConfigFileSource(pyproject).packages())
        assert packages == [Package(name="django", version="4.2.0")]


class TestAuditCommandWithConfigFile:
    def test_audit_pyproject_vs_lockfile(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry.dependencies]\nrequests = "2.31.0"\n')
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.32.0\n")

        result = CliRunner().invoke(audit_command, [str(pyproject), str(lockfile)])
        assert result.exit_code == 0
        normalized = result.output.lower()
        assert "requests" in normalized
        assert "minor" in normalized

    def test_audit_two_pyproject_files(self, tmp_path: Path):
        a = tmp_path / "a.toml"
        a.write_text('[tool.poetry.dependencies]\nrequests = "2.31.0"\n')
        b = tmp_path / "b.toml"
        b.write_text('[tool.poetry.dependencies]\nrequests = "2.32.0"\n')

        result = CliRunner().invoke(audit_command, [str(a), str(b)])
        assert result.exit_code == 0
        assert "requests" in result.output.lower()

    def test_uppercase_toml_extension_routes_to_config_source(self, tmp_path: Path):
        """Path suffix matching is case-insensitive — a .TOML file should
        be parsed as pyproject, not misrouted to LockfileSource."""
        a = tmp_path / "a.TOML"
        a.write_text('[tool.poetry.dependencies]\nrequests = "2.31.0"\n')
        b = tmp_path / "b.toml"
        b.write_text('[tool.poetry.dependencies]\nrequests = "2.32.0"\n')

        result = CliRunner().invoke(audit_command, [str(a), str(b)])
        assert result.exit_code == 0
        assert "requests" in result.output.lower()
        assert "minor" in result.output.lower()
