"""
Regression tests for the telemetry gate in `_send_report`.

`_send_report` must never POST a diagnostic report to the API when
ENVFORAGE_TELEMETRY=off, including case-insensitive and
whitespace-padded variants. It must POST when telemetry is unset
(default "on") or explicitly enabled.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from envforage.cli import _send_report
from envforage.schemas import DiagnosticReport

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def report() -> DiagnosticReport:
    raw = (FIXTURES_DIR / "linux_gpu.json").read_text(encoding="utf-8")
    return DiagnosticReport.model_validate_json(raw)


@pytest.fixture
def mock_httpx():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"report_id": "test-report-123"}

    mock_client = MagicMock()
    mock_post = AsyncMock(return_value=mock_resp)
    mock_client.post = mock_post

    mock_class = MagicMock()
    mock_class.return_value.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", mock_class):
        yield mock_post


class TestTelemetryDisabled:
    """ENVFORAGE_TELEMETRY=off (and case/whitespace variants) must never POST."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "value",
        ["off", "OFF", "Off", " off ", "\toff\n", "  OFF  "],
    )
    async def test_never_posts_when_disabled(self, value, report, mock_httpx, monkeypatch):
        monkeypatch.setenv("ENVFORAGE_TELEMETRY", value)

        await _send_report(report, "http://localhost:8000", quiet=True)

        mock_httpx.assert_not_called()

    @pytest.mark.asyncio
    async def test_never_posts_when_disabled_quiet_true(self, report, mock_httpx, monkeypatch):
        """quiet=True must not change the gating behaviour."""
        monkeypatch.setenv("ENVFORAGE_TELEMETRY", "off")

        await _send_report(report, "http://localhost:8000", quiet=True)

        mock_httpx.assert_not_called()

    @pytest.mark.asyncio
    async def test_never_posts_when_disabled_quiet_false(self, report, mock_httpx, monkeypatch, capsys):
        """quiet=False should print a notice but still not POST."""
        monkeypatch.setenv("ENVFORAGE_TELEMETRY", "off")

        await _send_report(report, "http://localhost:8000", quiet=False)

        mock_httpx.assert_not_called()


class TestTelemetryEnabled:
    """Telemetry unset (default) or explicitly enabled must POST."""

    @pytest.mark.asyncio
    async def test_posts_when_unset(self, report, mock_httpx, monkeypatch):
        monkeypatch.delenv("ENVFORAGE_TELEMETRY", raising=False)

        await _send_report(report, "http://localhost:8000", quiet=True)

        mock_httpx.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", ["on", "ON", " on ", "anything-else"])
    async def test_posts_when_enabled_variants(self, value, report, mock_httpx, monkeypatch):
        monkeypatch.setenv("ENVFORAGE_TELEMETRY", value)

        await _send_report(report, "http://localhost:8000", quiet=True)

        mock_httpx.assert_called_once()