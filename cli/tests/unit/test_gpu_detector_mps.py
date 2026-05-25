"""
Unit tests for GPU detection with Apple Silicon/MPS support.
Tests for: cli/envforge_agent/detectors/gpu_detector.py
"""
from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch, MagicMock

from envforge_agent.detectors.gpu_detector import (
    detect_gpus,
    _detect_via_nvidia_smi,
    _detect_via_rocm_smi,
    _detect_mps,
    _get_macos_version,
    _parse_macos_version,
    _check_pytorch_mps_available,
)


class TestDetectGpus(unittest.TestCase):
    """Integration tests for detect_gpus()."""

    def test_detect_gpus_macos_arm64_with_mps(self):
        """On macOS arm64, should detect MPS before trying nvidia-smi."""
        mock_gpu = MagicMock()
        mock_gpu.name = "MPS GPU"
        with patch("platform.system", return_value="Darwin"):
            with patch("platform.machine", return_value="arm64"):
                with patch(
                    "envforge_agent.detectors.gpu_detector._detect_mps",
                    return_value=[mock_gpu],
                ):
                    gpus = detect_gpus()
                    self.assertEqual(len(gpus), 1)
                    self.assertEqual(gpus[0].name, "MPS GPU")

    def test_detect_gpus_linux_nvidia(self):
        """On Linux with NVIDIA, should detect via nvidia-smi."""
        with patch("platform.system", return_value="Linux"):
            with patch("platform.machine", return_value="x86_64"):
                with patch(
                    "envforge_agent.detectors.gpu_detector._detect_via_rocm_smi",
                    return_value=[],
                ):
                    nvidia_output = "0, NVIDIA A100, 40960, 525.105.17"
                    with patch(
                        "subprocess.run",
                        return_value=MagicMock(returncode=0, stdout=nvidia_output),
                    ):
                        gpus = detect_gpus()
                        self.assertEqual(len(gpus), 1)
                        self.assertIn("A100", gpus[0].name)

    def test_detect_gpus_no_gpu(self):
        """When no GPU detected, should return empty list."""
        with patch("platform.system", return_value="Darwin"):
            with patch("platform.machine", return_value="x86_64"):
                with patch(
                    "envforge_agent.detectors.gpu_detector._detect_via_nvidia_smi",
                    return_value=[],
                ):
                    with patch(
                        "envforge_agent.detectors.gpu_detector._detect_via_rocm_smi",
                        return_value=[],
                    ):
                        gpus = detect_gpus()
                        self.assertEqual(len(gpus), 0)


class TestDetectNvidiaSmi(unittest.TestCase):
    """Tests for _detect_via_nvidia_smi()."""

    def test_nvidia_smi_success(self):
        """Parse nvidia-smi output correctly."""
        output = "0, NVIDIA GeForce RTX 4090, 24576, 531.18"
        result = MagicMock(returncode=0, stdout=output)
        
        with patch("subprocess.run", return_value=result):
            gpus = _detect_via_nvidia_smi(timeout=30)
        
        self.assertEqual(len(gpus), 1)
        self.assertEqual(gpus[0].name, "NVIDIA GeForce RTX 4090")
        self.assertAlmostEqual(gpus[0].vram_gb, 24.0, delta=0.1)
        self.assertEqual(gpus[0].driver_version, "531.18")

    def test_nvidia_smi_multiple_gpus(self):
        """Parse multiple GPUs from nvidia-smi."""
        output = "0, NVIDIA A100, 40960, 525.105.17\n1, NVIDIA A100, 40960, 525.105.17"
        result = MagicMock(returncode=0, stdout=output)
        
        with patch("subprocess.run", return_value=result):
            gpus = _detect_via_nvidia_smi()
        
        self.assertEqual(len(gpus), 2)

    def test_nvidia_smi_not_found(self):
        """When nvidia-smi not in PATH, return empty list."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            gpus = _detect_via_nvidia_smi()
        
        self.assertEqual(len(gpus), 0)

    def test_nvidia_smi_timeout(self):
        """When nvidia-smi times out, return empty list."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 15)):
            gpus = _detect_via_nvidia_smi(timeout=15)
        
        self.assertEqual(len(gpus), 0)

    def test_nvidia_smi_respects_timeout_parameter(self):
        """Verify timeout parameter is passed to subprocess."""
        custom_timeout = 45
        result = MagicMock(returncode=0, stdout="")
        
        with patch("subprocess.run", return_value=result) as mock_run:
            _detect_via_nvidia_smi(timeout=custom_timeout)
            
            # Check that the timeout argument was passed
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            self.assertEqual(call_kwargs["timeout"], custom_timeout)


class TestDetectMps(unittest.TestCase):
    """Tests for _detect_mps() — Apple Silicon Metal Performance Shaders."""

    def test_mps_macos_13_available(self):
        """macOS 13.5.1 with PyTorch should report MPS available."""
        with patch(
            "envforge_agent.detectors.gpu_detector._get_macos_version",
            return_value="13.5.1",
        ):
            with patch(
                "envforge_agent.detectors.gpu_detector._check_pytorch_mps_available",
                return_value=True,
            ):
                gpus = _detect_mps()
        
        self.assertEqual(len(gpus), 1)
        self.assertEqual(gpus[0].name, "Apple Metal Performance Shaders (MPS)")
        self.assertIsNone(gpus[0].vram_gb)

    def test_mps_macos_old_version_unsupported(self):
        """macOS 12.2 (older than 12.3) should return no MPS."""
        with patch(
            "envforge_agent.detectors.gpu_detector._get_macos_version",
            return_value="12.2",
        ):
            gpus = _detect_mps()
        
        self.assertEqual(len(gpus), 0)

    def test_mps_pytorch_not_installed(self):
        """When PyTorch not installed but macOS 12.3+, infer MPS available."""
        with patch(
            "envforge_agent.detectors.gpu_detector._get_macos_version",
            return_value="12.3",
        ):
            with patch(
                "envforge_agent.detectors.gpu_detector._check_pytorch_mps_available",
                return_value=None,
            ):
                gpus = _detect_mps()
        
        # Should still return MPS (version check passed, PyTorch not available yet)
        self.assertEqual(len(gpus), 1)

    def test_mps_pytorch_not_available(self):
        """When PyTorch installed but MPS.is_available()=False, return no MPS."""
        with patch(
            "envforge_agent.detectors.gpu_detector._get_macos_version",
            return_value="13.0",
        ):
            with patch(
                "envforge_agent.detectors.gpu_detector._check_pytorch_mps_available",
                return_value=False,
            ):
                gpus = _detect_mps()
        
        self.assertEqual(len(gpus), 0)


class TestGetMacosVersion(unittest.TestCase):
    """Tests for _get_macos_version()."""

    def test_get_macos_version_via_sw_vers(self):
        """Should use sw_vers command first."""
        result = MagicMock(returncode=0, stdout="13.5.1\n")
        
        with patch("subprocess.run", return_value=result):
            version = _get_macos_version()
        
        self.assertEqual(version, "13.5.1")

    def test_get_macos_version_sw_vers_fails_fallback_to_platform(self):
        """When sw_vers fails, fallback to platform.mac_ver() product version."""
        with patch("subprocess.run", side_effect=Exception("sw_vers failed")):
            with patch("platform.mac_ver", return_value=("13.5.1", ("", "", ""), "")):
                version = _get_macos_version()

        self.assertEqual(version, "13.5.1")

    def test_get_macos_version_all_fail_returns_none(self):
        """When all methods fail, return None."""
        with patch("subprocess.run", side_effect=Exception):
            with patch("platform.release", side_effect=Exception):
                version = _get_macos_version()
        
        self.assertIsNone(version)


class TestParseMacosVersion(unittest.TestCase):
    """Tests for _parse_macos_version()."""

    def test_parse_version_release_format(self):
        """Parse standard macOS version (e.g., 13.5.1)."""
        major, minor = _parse_macos_version("13.5.1")
        self.assertEqual((major, minor), (13, 5))

    def test_parse_version_darwin_kernel_format(self):
        """Parse Darwin kernel version (e.g., 22.6.0)."""
        major, minor = _parse_macos_version("22.6.0")
        self.assertEqual((major, minor), (22, 6))

    def test_parse_version_major_only(self):
        """Parse version with only major number."""
        major, minor = _parse_macos_version("12")
        self.assertEqual((major, minor), (12, 0))

    def test_parse_version_invalid(self):
        """Invalid version string returns (0, 0)."""
        major, minor = _parse_macos_version("invalid")
        self.assertEqual((major, minor), (0, 0))


class TestCheckPytorchMpsAvailable(unittest.TestCase):
    """Tests for _check_pytorch_mps_available()."""

    def test_pytorch_installed_mps_available(self):
        """When PyTorch installed and MPS available."""
        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True
        
        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = _check_pytorch_mps_available()
        
        self.assertTrue(result)

    def test_pytorch_installed_mps_not_available(self):
        """When PyTorch installed but MPS not available."""
        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False
        
        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = _check_pytorch_mps_available()
        
        self.assertFalse(result)

    def test_pytorch_not_installed(self):
        """When PyTorch not installed, return None."""
        # This is tricky to test with mocking — in real scenario:
        # result should be None when import fails
        import sys
        if "torch" in sys.modules:
            del sys.modules["torch"]
        
        # Mock the import error
        with patch("builtins.__import__", side_effect=ImportError):
            result = _check_pytorch_mps_available()
        
        self.assertIsNone(result)


class TestIntegrationMpsDetection(unittest.TestCase):
    """Integration tests for complete MPS detection workflow."""

    def test_full_mps_detection_macos_m1_pytorch_installed(self):
        """Full detection: macOS 13.5, ARM64, PyTorch with MPS."""
        with patch("platform.system", return_value="Darwin"):
            with patch("platform.machine", return_value="arm64"):
                with patch(
                    "envforge_agent.detectors.gpu_detector._get_macos_version",
                    return_value="13.5.1",
                ):
                    with patch(
                        "envforge_agent.detectors.gpu_detector._check_pytorch_mps_available",
                        return_value=True,
                    ):
                        gpus = detect_gpus(timeout=30)
        
        self.assertEqual(len(gpus), 1)
        self.assertEqual(gpus[0].name, "Apple Metal Performance Shaders (MPS)")

    def test_full_detection_intel_mac_no_gpu(self):
        """Full detection: Intel Mac (x86_64) should return no GPU."""
        with patch("platform.system", return_value="Darwin"):
            with patch("platform.machine", return_value="x86_64"):
                with patch(
                    "envforge_agent.detectors.gpu_detector._detect_via_nvidia_smi",
                    return_value=[],
                ):
                    with patch(
                        "envforge_agent.detectors.gpu_detector._detect_via_rocm_smi",
                        return_value=[],
                    ):
                        gpus = detect_gpus()
        
        self.assertEqual(len(gpus), 0)


if __name__ == "__main__":
    unittest.main()
