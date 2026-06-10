"""
Unit tests for cli/envforge_agent/detectors/python_detector.py

Tests error handling for invalid Python executables,
broken symlinks, and missing binaries.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from envforge_agent.detectors.python_detector import _inspect_python


class TestInspectPython(unittest.TestCase):
    """Tests for _inspect_python()."""

    def test_handles_oserror(self):
        """Broken symlinks or invalid executables should be skipped."""
        with patch(
            "subprocess.Popen",
            side_effect=OSError("Broken symlink"),
        ):
            result = _inspect_python("python3.12")

        self.assertIsNone(result)

    def test_handles_filenotfounderror(self):
        """Missing Python binaries should be skipped."""
        with patch(
            "subprocess.Popen",
            side_effect=FileNotFoundError("No such file"),
        ):
            result = _inspect_python("python3.12")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
