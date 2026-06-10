"""
Unit tests for envforge-agent.

Tests use JSON fixtures to avoid any live system detection calls.
All detector tests mock subprocess / platform — no nvidia-smi required.
"""

from __future__ import annotations

import sys
import json
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envforge_agent.schemas import DiagnosticReport

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


# ── Schema round-trip tests ───────────────────────────────────────────────────


class TestDiagnosticReportSchema:
    """Validate that fixture JSON round-trips through the Pydantic schema."""

    @pytest.mark.parametrize(
        "fixture_file",
        [
            "linux_gpu.json",
            "wsl_cuda.json",
            "linux_no_cuda.json",
            "windows_gpu.json",
        ],
    )
    def test_fixture_parses_cleanly(self, fixture_file: str) -> None:
        """Every fixture must deserialize into a valid DiagnosticReport."""
        raw = (FIXTURES_DIR / fixture_file).read_text(encoding="utf-8")
        report = DiagnosticReport.model_validate_json(raw)
        assert report.agent_version == "1.0.0"
        assert report.os.name
        assert report.cpu.cores >= 1
        assert report.cpu.threads >= report.cpu.cores
        assert report.ram.total_gb > 0

    def test_linux_gpu_fixture(self) -> None:
        data = load_fixture("linux_gpu.json")
        report = DiagnosticReport.model_validate(data)

        assert report.os.architecture == "x86_64"
        assert report.os.wsl_version is None
        assert len(report.gpus) == 1
        assert report.gpus[0].name == "NVIDIA GeForce RTX 4090"
        assert report.gpus[0].vram_gb == 24.0
        assert report.cuda.version == "12.1"
        assert report.cuda.cudnn_version == "8.9.0"
        assert report.active_python is not None
        assert report.active_python.version.startswith("3.11")

    def test_wsl_fixture_has_wsl_version(self) -> None:
        data = load_fixture("wsl_cuda.json")
        report = DiagnosticReport.model_validate(data)

        assert report.os.wsl_version == "WSL2"
        assert report.cuda.version == "11.8"
        assert report.gpus[0].driver_version == "527.86"

    def test_no_cuda_fixture(self) -> None:
        data = load_fixture("linux_no_cuda.json")
        report = DiagnosticReport.model_validate(data)

        assert report.gpus == []
        assert report.cuda.version is None
        assert report.cuda.toolkit_path is None

    def test_windows_fixture(self) -> None:
        data = load_fixture("windows_gpu.json")
        report = DiagnosticReport.model_validate(data)

        assert "Windows" in report.os.name
        assert report.os.wsl_version is None
        assert report.gpus[0].driver_version == "551.61"
        assert report.cuda.version is None  # toolkit not installed yet

    def test_to_json_produces_valid_json(self) -> None:
        data = load_fixture("linux_gpu.json")
        report = DiagnosticReport.model_validate(data)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["agent_version"] == "1.0.0"
        assert "os" in parsed
        assert "gpus" in parsed


# ── OS Detector tests ─────────────────────────────────────────────────────────


class TestOSDetector:
    def test_detect_os_returns_os_info(self) -> None:
        """detect_os() always returns an OSInfo — never raises."""
        from envforge_agent.detectors.os_detector import detect_os

        result = detect_os()
        assert result.name
        assert result.version
        assert result.architecture

    def test_wsl_detection_via_env(self) -> None:
        from envforge_agent.detectors.os_detector import _detect_wsl

        with patch.dict("os.environ", {"WSL_DISTRO_NAME": "Ubuntu"}):
            result = _detect_wsl()
        assert result == "WSL2"

    def test_no_wsl_returns_none(self) -> None:
        from envforge_agent.detectors.os_detector import _detect_wsl

        # Patch env to remove WSL vars and /proc files to not exist
        with patch.dict("os.environ", {}, clear=True):
            with patch("builtins.open", side_effect=FileNotFoundError):
                result = _detect_wsl()
        assert result is None

    @pytest.mark.skipif(sys.platform != "win32", reason="requires winreg/Windows")
    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    @patch("platform.release")
    def test_detect_windows_10(self, mock_release, mock_query, mock_openkey) -> None:
        from envforge_agent.detectors.os_detector import _detect_windows

        mock_release.return_value = "10"
        mock_query.side_effect = [
            ("Windows 10 Home", 1),
            ("19045", 1),
            ("22H2", 1),
        ]
        result = _detect_windows("AMD64")
        assert result.name == "Windows 10 Home"
        assert result.version == "22H2 (Build 19045)"
        assert result.architecture == "AMD64"

    @pytest.mark.skipif(sys.platform != "win32", reason="requires winreg/Windows")
    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    @patch("platform.release")
    def test_detect_windows_11_via_build(self, mock_release, mock_query, mock_openkey) -> None:
        from envforge_agent.detectors.os_detector import _detect_windows

        mock_release.return_value = "10"
        mock_query.side_effect = [
            ("Windows 10 Home Single Language", 1),
            ("22000", 1),
            ("21H2", 1),
        ]
        result = _detect_windows("AMD64")
        assert result.name == "Windows 11 Home Single Language"
        assert result.version == "21H2 (Build 22000)"

    @pytest.mark.skipif(sys.platform != "win32", reason="requires winreg/Windows")
    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    @patch("platform.release")
    def test_detect_windows_11_via_release(self, mock_release, mock_query, mock_openkey) -> None:
        from envforge_agent.detectors.os_detector import _detect_windows

        mock_release.return_value = "11"
        mock_query.side_effect = [
            ("Windows 10 Pro", 1),
            ("invalid_build", 1),
            ("23H2", 1),
        ]
        result = _detect_windows("AMD64")
        assert result.name == "Windows 11 Pro"
        assert result.version == "23H2 (Build invalid_build)"


# ── GPU Detector tests ────────────────────────────────────────────────────────


class TestGPUDetector:
    def test_no_nvidia_smi_returns_empty(self) -> None:
        from envforge_agent.detectors.gpu_detector import detect_gpus

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = detect_gpus()
        assert result == []

    def test_nvidia_smi_failure_returns_empty(self) -> None:
        from envforge_agent.detectors.gpu_detector import detect_gpus

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = detect_gpus()
        assert result == []

    def test_parses_single_gpu(self) -> None:
        from envforge_agent.detectors.gpu_detector import detect_gpus

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0, NVIDIA GeForce RTX 4090, 24576, 535.54.03\n"
        with patch("subprocess.run", return_value=mock_result):
            result = detect_gpus()
        assert len(result) == 1
        assert result[0].name == "NVIDIA GeForce RTX 4090"
        assert result[0].vram_gb == pytest.approx(24.0, abs=0.1)
        assert result[0].driver_version == "535.54.03"
        assert result[0].index == 0

    def test_parses_multi_gpu(self) -> None:
        from envforge_agent.detectors.gpu_detector import detect_gpus

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "0, NVIDIA GeForce RTX 4090, 24576, 535.54.03\n"
            "1, NVIDIA GeForce RTX 4090, 24576, 535.54.03\n"
        )
        with patch("subprocess.run", return_value=mock_result):
            result = detect_gpus()
        assert len(result) == 2
        assert result[1].index == 1

    def test_vram_converted_from_mib_to_gb(self) -> None:
        from envforge_agent.detectors.gpu_detector import detect_gpus

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0, Test GPU, 8192, 535.0\n"  # 8192 MiB = 8.0 GB
        with patch("subprocess.run", return_value=mock_result):
            result = detect_gpus()
        assert result[0].vram_gb == pytest.approx(8.0, abs=0.01)

    def test_wsl_gpu_passthrough_reports_issues_when_dxg_missing(self) -> None:
        from envforge_agent.detectors.gpu_detector import detect_wsl_gpu_passthrough

        with patch("envforge_agent.detectors.gpu_detector._detect_wsl", return_value="WSL2"):
            with patch("os.path.exists", return_value=False):
                with patch("subprocess.run", side_effect=FileNotFoundError):
                    ok, issues = detect_wsl_gpu_passthrough()

        assert ok is False
        assert any("/dev/dxg" in issue for issue in issues)
        assert any("nvidia-smi" in issue for issue in issues)

    def test_wsl_gpu_passthrough_ok_when_dxg_and_nvidia_available(self) -> None:
        from envforge_agent.detectors.gpu_detector import detect_wsl_gpu_passthrough

        mock_smi = MagicMock()
        mock_smi.returncode = 0
        mock_smi.stdout = "GPU 0: Test GPU"
        mock_nct = MagicMock()
        mock_nct.returncode = 0
        mock_nct.stdout = "nvidia-container-cli 1.0"

        with patch("envforge_agent.detectors.gpu_detector._detect_wsl", return_value="WSL2"):
            with patch("os.path.exists", return_value=True):
                with patch("os.stat", return_value=MagicMock(st_mode=stat.S_IFCHR)):
                    with patch("subprocess.run", side_effect=[mock_smi, mock_nct]):
                        ok, issues = detect_wsl_gpu_passthrough()

        assert ok is True
        assert issues == []


# ── CUDA Detector tests ───────────────────────────────────────────────────────


class TestCUDADetector:
    def test_no_cuda_returns_empty_info(self) -> None:
        from envforge_agent.detectors.cuda_detector import detect_cuda

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("builtins.open", side_effect=FileNotFoundError):
                with patch.dict("os.environ", {}, clear=True):
                    result = detect_cuda()
        assert result.version is None
        assert result.toolkit_path is None

    def test_nvcc_version_parsed(self) -> None:
        from envforge_agent.detectors.cuda_detector import _nvcc_version

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Cuda compilation tools, release 12.1, V12.1.105"
        with patch("subprocess.run", return_value=mock_result):
            result = _nvcc_version()
        assert result == "12.1"

    def test_nvcc_not_found_returns_none(self) -> None:
        from envforge_agent.detectors.cuda_detector import _nvcc_version

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _nvcc_version()
        assert result is None

    def test_cuda_path_env_version(self) -> None:
        from envforge_agent.detectors.cuda_detector import _cuda_path_env_version

        with patch.dict("os.environ", {"CUDA_PATH": r"C:\CUDA\v12.1"}):
            result = _cuda_path_env_version()
        assert result == "12.1"

    @patch("subprocess.run")
    def test_nvidia_smi_cuda_version_query_success(self, mock_run: MagicMock) -> None:
        from envforge_agent.detectors.cuda_detector import _nvidia_smi_cuda_version

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "12.3\n"
        mock_run.return_value = mock_proc

        result = _nvidia_smi_cuda_version()
        assert result == "12.3"

    @patch("subprocess.run")
    def test_nvidia_smi_cuda_version_fallback_success(self, mock_run: MagicMock) -> None:
        from envforge_agent.detectors.cuda_detector import _nvidia_smi_cuda_version

        # First call (query-gpu) fails
        mock_query_fail = MagicMock()
        mock_query_fail.returncode = 1

        # Second call (standard nvidia-smi) succeeds
        mock_fallback_ok = MagicMock()
        mock_fallback_ok.returncode = 0
        mock_fallback_ok.stdout = (
            "Fri May 22 15:53:56 2026       \n"
            "+-----------------------------------------------------------------------------------------+\n"
            "| NVIDIA-SMI 595.79                 Driver Version: 595.79         CUDA Version: 13.2     |\n"
            "+-----------------------------------------+------------------------+----------------------+\n"
        )

        mock_run.side_effect = [mock_query_fail, mock_fallback_ok]

        result = _nvidia_smi_cuda_version()
        assert result == "13.2"

    @patch("subprocess.run")
    def test_nvidia_smi_cuda_version_not_found(self, mock_run: MagicMock) -> None:
        from envforge_agent.detectors.cuda_detector import _nvidia_smi_cuda_version

        mock_run.side_effect = FileNotFoundError()

        result = _nvidia_smi_cuda_version()
        assert result is None


# ── Python Detector tests ─────────────────────────────────────────────────────


class TestPythonDetector:
    def test_active_python_detected(self) -> None:
        """The current interpreter should always be detectable."""
        from envforge_agent.detectors.python_detector import detect_python

        installations, active = detect_python()
        assert active is not None
        assert active.version  # e.g. "3.11.9"
        assert active.path
        assert len(active.version.split(".")) >= 2

    def test_installations_not_empty(self) -> None:
        """At minimum, the current interpreter is in installations."""
        from envforge_agent.detectors.python_detector import detect_python

        installations, _ = detect_python()
        assert len(installations) >= 1

    def test_inspector_parses_version(self) -> None:
        from envforge_agent.detectors.python_detector import _inspect_python
        import sys

        result = _inspect_python(sys.executable)
        assert result is not None
        assert result.version
        path_str = result.path
        if path_str.startswith("<USER_HOME>"):
            path_str = path_str.replace("<USER_HOME>", str(Path.home()), 1)
        assert (
            path_str == sys.executable or Path(path_str).resolve() == Path(sys.executable).resolve()
        )

    @patch("subprocess.Popen")
    @patch("psutil.Process")
    def test_inspect_python_timeout(
        self, mock_psutil_process: MagicMock, mock_popen: MagicMock
    ) -> None:
        import subprocess
        from envforge_agent.detectors.python_detector import _inspect_python

        # Mock Popen instance
        mock_proc = MagicMock()
        # Mock communicate to raise TimeoutExpired on the first call, and succeed on the second
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd="mock_python", timeout=10),
            ("", ""),
        ]
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        # Mock psutil Process instance
        mock_psutil_proc_inst = MagicMock()
        mock_child = MagicMock()
        mock_psutil_proc_inst.children.return_value = [mock_child]
        mock_psutil_process.return_value = mock_psutil_proc_inst

        # Run inspect
        result = _inspect_python("mock_python")

        # Verify result is None
        assert result is None

        # Verify child and parent were killed
        mock_child.kill.assert_called_once()
        mock_proc.kill.assert_called_once()
        # Verify communicate was called again to reap the process
        assert mock_proc.communicate.call_count == 2


# ── System Detector tests ─────────────────────────────────────────────────────


class TestSystemDetector:
    def test_cpu_detected(self) -> None:
        from envforge_agent.detectors.system_detector import detect_cpu

        result = detect_cpu()
        assert result.brand
        assert result.cores >= 1
        assert result.threads >= result.cores

    def test_ram_detected(self) -> None:
        from envforge_agent.detectors.system_detector import detect_ram

        result = detect_ram()
        assert result.total_gb > 0
        assert result.available_gb >= 0
        assert result.available_gb <= result.total_gb


# ── ReportBuilder integration test ───────────────────────────────────────────


class TestReportBuilder:
    def test_build_returns_valid_report(self) -> None:
        """build() must always return a valid DiagnosticReport without raising."""
        from envforge_agent.report import ReportBuilder

        report = ReportBuilder().build()
        assert isinstance(report, DiagnosticReport)
        assert report.agent_version == "1.0.2"
        assert report.os.name
        assert report.cpu.cores >= 1

    def test_build_serializes_to_json(self) -> None:
        from envforge_agent.report import ReportBuilder

        report = ReportBuilder().build()
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert "agent_version" in parsed
        assert "os" in parsed
        assert "gpus" in parsed


def test_sarif_output_structure():
    """Test that to_sarif() returns valid SARIF 2.1.0 structure."""
    from envforge_agent.schemas import DiagnosticReport, OSInfo, CPUInfo, RAMInfo, CUDAInfo

    report = DiagnosticReport(
        os=OSInfo(name="Ubuntu", version="22.04", architecture="x86_64"),
        cpu=CPUInfo(brand="Intel i9", cores=8, threads=16),
        ram=RAMInfo(total_gb=32.0, available_gb=16.0),
        gpus=[],
        cuda=CUDAInfo(version=None),
        python_installations=[],
        active_python=None,
    )
    sarif = report.to_sarif()

    assert sarif["version"] == "2.1.0"
    assert "$schema" in sarif
    assert "runs" in sarif
    assert len(sarif["runs"]) == 1

    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "envforge-agent"
    assert "results" in run

    rule_ids = [r["ruleId"] for r in run["results"]]
    assert "ENV001" in rule_ids
    assert "ENV002" in rule_ids
    assert "ENV003" in rule_ids


def test_sarif_no_issues_when_healthy():
    """Test that a healthy environment produces no SARIF results."""
    from envforge_agent.schemas import (
        DiagnosticReport,
        OSInfo,
        CPUInfo,
        RAMInfo,
        CUDAInfo,
        GPUInfo,
        PythonInfo,
    )

    report = DiagnosticReport(
        os=OSInfo(name="Ubuntu", version="22.04", architecture="x86_64"),
        cpu=CPUInfo(brand="Intel i9", cores=8, threads=16),
        ram=RAMInfo(total_gb=32.0, available_gb=16.0),
        gpus=[GPUInfo(name="NVIDIA RTX 4090", vram_gb=24.0)],
        cuda=CUDAInfo(version="12.1"),
        python_installations=[],
        active_python=PythonInfo(version="3.11.9", path="/usr/bin/python3"),
    )
    sarif = report.to_sarif()
    assert sarif["runs"][0]["results"] == []


class TestVerifyCommand:
    """Tests for the envforge verify CLI command."""

    @patch("subprocess.run")
    def test_verify_pass_no_profile(self, mock_run: MagicMock) -> None:
        from envforge_agent.cli import cli
        from click.testing import CliRunner

        # Mock the subprocess execution
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"import_ok": true, "cuda_ok": false, "error": null}'
        mock_run.return_value = mock_proc

        runner = CliRunner()
        result = runner.invoke(cli, ["verify", "-q"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "PASS"
        assert "imported successfully" in data["message"]
        assert "CPU only" in data["message"]

    @patch("subprocess.run")
    def test_verify_pass_cuda_profile(self, mock_run: MagicMock) -> None:
        from envforge_agent.cli import cli
        from click.testing import CliRunner

        # Mock the subprocess execution
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"import_ok": true, "cuda_ok": true, "error": null}'
        mock_run.return_value = mock_proc

        runner = CliRunner()
        result = runner.invoke(cli, ["verify", "--profile", "pytorch-cuda", "-q"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "PASS"
        assert "with CUDA support" in data["message"]

    @patch("subprocess.run")
    def test_verify_fail_import(self, mock_run: MagicMock) -> None:
        from envforge_agent.cli import cli
        from click.testing import CliRunner

        # Mock the subprocess execution
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"import_ok": false, "cuda_ok": false, "error": "ModuleNotFoundError: No module named \'torch\'"}'
        mock_run.return_value = mock_proc

        runner = CliRunner()
        result = runner.invoke(cli, ["verify", "-q"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["status"] == "FAIL"
        assert "PyTorch import failed" in data["message"]
        assert "ModuleNotFoundError" in data["error"]

    @patch("subprocess.run")
    def test_verify_fail_cuda_on_gpu_profile(self, mock_run: MagicMock) -> None:
        from envforge_agent.cli import cli
        from click.testing import CliRunner

        # Mock the subprocess execution
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"import_ok": true, "cuda_ok": false, "error": null}'
        mock_run.return_value = mock_proc

        runner = CliRunner()
        result = runner.invoke(cli, ["verify", "--profile", "pytorch-cuda", "-q"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["status"] == "FAIL"
        assert "CUDA not available" in data["message"]
