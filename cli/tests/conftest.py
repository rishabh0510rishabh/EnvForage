"""
Shared pytest fixtures for envforage CLI tests.

Mocks check_macos_support() as a no-op so the CLI test suite
can run on macOS developer machines without sys.exit(1).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def bypass_macos_check():
    """Prevent check_macos_support() from calling sys.exit(1) on macOS."""
    with patch("envforage.cli.check_macos_support"):
        yield
