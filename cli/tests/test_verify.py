"""
Unit tests for `envforge verify` CLI command.

Tests mock subprocess.run to simulate PyTorch/CUDA inspection script
output, covering all key code paths in the verify command.
"""
from __future__ import annotations

import json
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envforage.cli import cli


def _make_proc(stdout: dict, returncode: int = 0, stderr: str = "") -> MagicMock:
    """Build a mock subprocess.CompletedProcess result."""
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = json.dumps(stdout)
    mock.stderr = stderr
    return mock


def _make_report():
    """Stub ReportBuilder so no real hardware detection runs."""
    mock_report = MagicMock()
    mock_report.active_python = MagicMock()
    mock_report.active_python.path = "python"
    mock_report.gpus = []
    mock_builder = MagicMock()
    mock_builder.return_value.build.return_value = mock_report
    return mock_builder


# ── Successful scenarios ──────────────────────────────────────────────────────


def test_verify_pytorch_cpu_success():
    """PyTorch import OK, no CUDA — should PASS with CPU only message."""
    proc = _make_proc({
        "framework": "PyTorch",
        "import_ok": True,
        "version": "2.3.0",
        "cuda_ok": False,
        "cuda_version": None,
        "error": None,
    })
    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", return_value=proc):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", "--quiet"])

    output = json.loads(result.output)
    assert output["status"] == "PASS"
    assert "CPU only" in output["message"]
    assert result.exit_code == 0


def test_verify_pytorch_cuda_success():
    """PyTorch + CUDA both available — should PASS with CUDA message."""
    proc = _make_proc({
        "framework": "PyTorch",
        "import_ok": True,
        "version": "2.3.0",
        "cuda_ok": True,
        "cuda_version": "12.1",
        "error": None,
    })
    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", return_value=proc):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["verify", "--profile", "pytorch-cuda", "--quiet"]
            )

    output = json.loads(result.output)
    assert output["status"] == "PASS"
    assert "CUDA" in output["message"]
    assert result.exit_code == 0


# ── Import failure ────────────────────────────────────────────────────────────


def test_verify_import_failure_exits_nonzero():
    """PyTorch import failed — should FAIL with friendly error message."""
    proc = _make_proc({
        "framework": "PyTorch",
        "import_ok": False,
        "version": None,
        "cuda_ok": False,
        "cuda_version": None,
        "error": "ModuleNotFoundError: No module named 'torch'",
    })
    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", return_value=proc):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", "--quiet"])

    output = json.loads(result.output)
    assert output["status"] == "FAIL"
    assert "import failed" in output["message"]
    assert result.exit_code != 0
    assert "Traceback" not in result.output


# ── CUDA unavailable on GPU profile ──────────────────────────────────────────


def test_verify_cuda_unavailable_on_gpu_profile():
    """Import OK but CUDA not available on a CUDA profile — should FAIL."""
    proc = _make_proc({
        "framework": "PyTorch",
        "import_ok": True,
        "version": "2.3.0",
        "cuda_ok": False,
        "cuda_version": None,
        "error": None,
    })
    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", return_value=proc):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["verify", "--profile", "pytorch-cuda", "--quiet"]
            )

    output = json.loads(result.output)
    assert output["status"] == "FAIL"
    assert "CUDA" in output["message"] or "GPU" in output["message"]
    assert result.exit_code != 0


# ── Subprocess error cases ────────────────────────────────────────────────────


def test_verify_subprocess_nonzero_returncode():
    """Non-zero returncode from subprocess — should FAIL gracefully."""
    proc = MagicMock()
    proc.returncode = 1
    proc.stdout = ""
    proc.stderr = "Segmentation fault"

    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", return_value=proc):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", "--quiet"])

    output = json.loads(result.output)
    assert output["status"] == "FAIL"
    assert result.exit_code != 0
    assert "Traceback" not in result.output


def test_verify_timeout_shows_friendly_message():
    """Subprocess timeout — should show 'timed out' message, no raw exception."""
    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", side_effect=TimeoutExpired(cmd="python", timeout=15)):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", "--quiet"])

    output = json.loads(result.output)
    assert output["status"] == "FAIL"
    assert "timed out" in output["message"].lower()
    assert result.exit_code != 0
    assert "Traceback" not in result.output


def test_verify_malformed_output_no_traceback():
    """Malformed subprocess JSON output — should fail gracefully, no traceback."""
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "NOT_VALID_JSON!!!"
    proc.stderr = ""

    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", return_value=proc):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", "--quiet"])

    assert result.exit_code != 0
    assert "Traceback" not in result.output


def test_verify_unexpected_exception_no_traceback():
    """Unexpected exception in subprocess — should fail gracefully, no traceback."""
    with patch("envforage.cli.ReportBuilder", _make_report()):
        with patch("subprocess.run", side_effect=OSError("Unexpected OS error")):
            runner = CliRunner()
            result = runner.invoke(cli, ["verify", "--quiet"])

    assert result.exit_code != 0
    assert "Traceback" not in result.output
