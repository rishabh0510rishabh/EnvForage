"""
Tests for `envforage troubleshoot` and `envforage list` CLI commands.

Both commands make live HTTP requests to the backend API. These tests
mock the relevant httpx functions to intercept network calls:
- troubleshoot: uses httpx.AsyncClient + client.stream() (async)
- list: uses synchronous httpx.get() directly
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from envforage.cli import cli


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_report_builder():
    """Stub out ReportBuilder so no real hardware detection runs."""
    mock_report = MagicMock()
    mock_report.to_json.return_value = '{"agent_version": "1.0.0"}'
    mock_report.model_dump.return_value = {"agent_version": "1.0.0"}
    mock_builder = MagicMock()
    mock_builder.return_value.build.return_value = mock_report
    return mock_builder, mock_report


def _make_sync_response(status_code=200, json_data=None, connect_error=False):
    """Build a mock synchronous httpx response."""
    if connect_error:
        return None  # signal to raise ConnectError
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = json_data or {}
    return mock_resp


# ── envforage troubleshoot ────────────────────────────────────────────────────


class TestTroubleshootCommand:
    """Tests for `envforage troubleshoot`."""

    def _make_stream_client(self, stream_lines=None, connect_error=False):
        """Build a mock httpx.AsyncClient for streaming."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        if stream_lines is not None:
            async def _aiter_lines():
                for line in (stream_lines or []):
                    yield line
            mock_response.aiter_lines = _aiter_lines

        mock_stream_ctx = MagicMock()
        if connect_error:
            mock_stream_ctx.__aenter__ = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
        else:
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)

        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_class = MagicMock(return_value=mock_client_ctx)
        return mock_class

    def test_connect_error_shows_friendly_message(self):
        """A ConnectError should print a friendly error, not a traceback."""
        mock_builder, _ = _make_report_builder()
        mock_class = self._make_stream_client(connect_error=True)

        with patch("envforage.cli.ReportBuilder", mock_builder):
            with patch("httpx.AsyncClient", mock_class):
                runner = CliRunner()
                result = runner.invoke(
                    cli, ["troubleshoot", "--quiet",
                          "--api-url", "http://localhost:9999"]
                )

        assert "Traceback" not in result.output
        assert "Cannot connect" in result.output or result.exit_code != 0

    def test_successful_stream_prints_no_traceback(self):
        """A successful stream should exit cleanly."""
        stream_lines = [
            'data: {"chunk": "Checking CUDA..."}',
            "data: [DONE]",
        ]
        mock_builder, _ = _make_report_builder()
        mock_class = self._make_stream_client(stream_lines=stream_lines)

        with patch("envforage.cli.ReportBuilder", mock_builder):
            with patch("httpx.AsyncClient", mock_class):
                runner = CliRunner()
                result = runner.invoke(
                    cli, ["troubleshoot", "--quiet",
                          "--api-url", "http://localhost:8000"]
                )

        assert "Traceback" not in result.output

    def test_quiet_suppresses_panel_output(self):
        """--quiet should suppress the EnvForge AI Troubleshooter panel."""
        stream_lines = ["data: [DONE]"]
        mock_builder, _ = _make_report_builder()
        mock_class = self._make_stream_client(stream_lines=stream_lines)

        with patch("envforage.cli.ReportBuilder", mock_builder):
            with patch("httpx.AsyncClient", mock_class):
                runner = CliRunner()
                result = runner.invoke(
                    cli, ["troubleshoot", "--quiet",
                          "--api-url", "http://localhost:8000"]
                )

        assert "EnvForge AI Troubleshooter" not in result.output
        assert "Traceback" not in result.output


# ── envforage list ────────────────────────────────────────────────────────────


class TestListCommand:
    """Tests for `envforage list`."""

    def _profiles_data(self, profiles=None):
        return {
            "profiles": profiles or [
                {"slug": "pytorch-cuda", "name": "PyTorch + CUDA",
                 "description": "GPU-accelerated PyTorch", "tags": ["gpu", "cuda"]},
                {"slug": "cpu-only", "name": "CPU Only",
                 "description": "CPU-only PyTorch", "tags": ["cpu"]},
            ],
            "total": 2,
            "page": 1,
            "page_size": 100,
        }

    def test_list_quiet_outputs_json(self):
        """--quiet should print a JSON list to stdout and exit 0."""
        mock_resp = _make_sync_response(json_data=self._profiles_data())

        with patch("httpx.get", return_value=mock_resp):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["list", "--quiet", "--api-url", "http://localhost:8000"]
            )

        assert result.exit_code == 0
        assert "pytorch-cuda" in result.output

    def test_list_connect_error_shows_friendly_message(self):
        """A ConnectError should print a friendly error, not a traceback."""
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["list", "--api-url", "http://localhost:9999"]
            )

        assert "Traceback" not in result.output
        assert "Cannot connect" in result.output

    def test_list_empty_profiles(self):
        """Empty profile list should exit 0 without crashing."""
        mock_resp = _make_sync_response(
            json_data={"profiles": [], "total": 0, "page": 1, "page_size": 100}
        )

        with patch("httpx.get", return_value=mock_resp):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["list", "--quiet", "--api-url", "http://localhost:8000"]
            )

        assert result.exit_code == 0
        assert "[]" in result.output

    def test_list_filter_by_tag(self):
        """--filter should restrict output to matching profiles."""
        mock_resp = _make_sync_response(json_data=self._profiles_data())

        with patch("httpx.get", return_value=mock_resp):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["list", "--filter", "cpu",
                      "--quiet", "--api-url", "http://localhost:8000"]
            )

        assert result.exit_code == 0
        assert "cpu-only" in result.output

    def test_list_http_error_shows_status_code(self):
        """Non-2xx response should show the status code in output."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=mock_resp
        )

        with patch("httpx.get", return_value=mock_resp):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["list", "--api-url", "http://localhost:8000"]
            )

        assert "503" in result.output