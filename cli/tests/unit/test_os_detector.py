"""
Unit tests for cli/envforge_agent/detectors/os_detector.py
Issue #152: Add unit tests for CLI OS Detector
"""

from __future__ import annotations

import unittest
from unittest.mock import mock_open, patch, MagicMock


from envforge_agent.detectors.os_detector import (
    detect_os,
    _detect_linux,
    _detect_windows,
    _read_os_release,
    _detect_wsl,
)


class TestReadOsRelease(unittest.TestCase):
    """Tests for _read_os_release() — simulates /etc/os-release."""

    def test_ubuntu_os_release(self):
        content = 'PRETTY_NAME="Ubuntu 22.04.3 LTS"\nVERSION_ID="22.04"\n'
        with patch("builtins.open", mock_open(read_data=content)):
            name, version = _read_os_release()
        self.assertEqual(name, "Ubuntu 22.04.3 LTS")
        self.assertEqual(version, "22.04")

    def test_fallback_when_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("platform.release", return_value="5.15.0"):
                name, version = _read_os_release()
        self.assertIn("Linux", name)
        self.assertEqual(version, "5.15.0")

    def test_fallback_on_generic_exception(self):
        with patch("builtins.open", side_effect=Exception("fail")):
            with patch("platform.release", return_value="5.15.0"):
                name, version = _read_os_release()
        self.assertEqual(name, "Linux")
        self.assertEqual(version, "5.15.0")


class TestDetectWsl(unittest.TestCase):
    """Tests for _detect_wsl() — simulates WSL2, WSL1, and native Linux."""

    def test_wsl2_via_env_variable(self):
        with patch.dict("os.environ", {"WSL_DISTRO_NAME": "Ubuntu"}):
            result = _detect_wsl()
        self.assertEqual(result, "WSL2")

    def test_wsl2_via_proc_version(self):
        with patch.dict("os.environ", {}, clear=True):
            proc_version = "Linux version 5.15.90.1-microsoft-standard-WSL2"
            osrelease = "5.15.90.1-microsoft-standard-WSL2"

            def fake_open(path, *args, **kwargs):
                if "osrelease" in path:
                    return mock_open(read_data=osrelease)()
                return mock_open(read_data=proc_version)()

            with patch("builtins.open", side_effect=fake_open):
                result = _detect_wsl()
        self.assertEqual(result, "WSL2")

    def test_wsl1_via_proc_version(self):
        with patch.dict("os.environ", {}, clear=True):
            proc_version = "Linux version 4.4.0-microsoft-standard"
            osrelease = "4.4.0-microsoft"

            def fake_open(path, *args, **kwargs):
                if "osrelease" in path:
                    return mock_open(read_data=osrelease)()
                return mock_open(read_data=proc_version)()

            with patch("builtins.open", side_effect=fake_open):
                result = _detect_wsl()
        self.assertEqual(result, "WSL1")

    def test_native_linux_returns_none(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("builtins.open", side_effect=Exception("no file")):
                result = _detect_wsl()
        self.assertIsNone(result)


class TestDetectLinux(unittest.TestCase):
    """Tests for _detect_linux() — simulates Ubuntu and WSL2."""

    def test_ubuntu_native(self):
        with patch(
            "envforge_agent.detectors.os_detector._read_os_release",
            return_value=("Ubuntu 22.04.3 LTS", "22.04"),
        ):
            with patch(
                "envforge_agent.detectors.os_detector._detect_wsl",
                return_value=None,
            ):
                with patch("platform.machine", return_value="x86_64"):
                    result = _detect_linux("x86_64")
        self.assertEqual(result.name, "Ubuntu 22.04.3 LTS")
        self.assertEqual(result.version, "22.04")
        self.assertIsNone(result.wsl_version)

    def test_ubuntu_wsl2(self):
        with patch(
            "envforge_agent.detectors.os_detector._read_os_release",
            return_value=("Ubuntu 22.04.3 LTS", "22.04"),
        ):
            with patch(
                "envforge_agent.detectors.os_detector._detect_wsl",
                return_value="WSL2",
            ):
                result = _detect_linux("x86_64")
        self.assertEqual(result.wsl_version, "WSL2")


class TestDetectWindows(unittest.TestCase):
    """Tests for _detect_windows() — simulates Windows registry."""

    def test_windows_10_from_registry(self):
        mock_key = MagicMock()

        def query_value(key, name):
            values = {
                "ProductName": "Windows 10 Pro",
                "CurrentBuildNumber": "19045",
                "DisplayVersion": "22H2",
            }
            return (values[name], 1)

        with patch(
            "envforge_agent.detectors.os_detector.platform.system",
            return_value="Windows",
        ):
            with patch.dict(
                "sys.modules",
                {
                    "winreg": MagicMock(
                        OpenKey=MagicMock(return_value=mock_key),
                        QueryValueEx=MagicMock(side_effect=query_value),
                        HKEY_LOCAL_MACHINE=MagicMock(),
                    )
                },
            ):
                import importlib
                import envforge_agent.detectors.os_detector as mod

                importlib.reload(mod)
                result = mod._detect_windows("AMD64")

        self.assertIn("Windows", result.name)
        self.assertEqual(result.architecture, "AMD64")

    def test_windows_fallback_on_exception(self):
        with patch.dict("sys.modules", {"winreg": None}):
            with patch("platform.release", return_value="10"):
                with patch("platform.version", return_value="10.0.19041"):
                    result = _detect_windows("AMD64")
        self.assertIn("Windows", result.name)
        self.assertEqual(result.architecture, "AMD64")


class TestDetectOs(unittest.TestCase):
    """Integration-level tests for detect_os()."""

    def test_detects_linux(self):
        with patch("platform.system", return_value="Linux"):
            with patch("platform.machine", return_value="x86_64"):
                with patch(
                    "envforge_agent.detectors.os_detector._detect_linux",
                    return_value=MagicMock(
                        name="Ubuntu 22.04",
                        version="22.04",
                        architecture="x86_64",
                        wsl_version=None,
                    ),
                ):
                    result = detect_os()
        self.assertIsNotNone(result)

    def test_detects_windows(self):
        with patch("platform.system", return_value="Windows"):
            with patch("platform.machine", return_value="AMD64"):
                with patch(
                    "envforge_agent.detectors.os_detector._detect_windows",
                    return_value=MagicMock(
                        name="Windows 10 Pro",
                        version="22H2",
                        architecture="AMD64",
                        wsl_version=None,
                    ),
                ):
                    result = detect_os()
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
