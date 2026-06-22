"""Tests for the --output flag of the envforage diagnose command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


from envforage.schemas import DiagnosticReport

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class TestDiagnoseOutputFlag:
    """Tests for the --output flag of the envforage diagnose command."""

    def test_output_flag_creates_json_file(self, tmp_path) -> None:
        """--output saves a valid JSON DiagnosticReport to the given file path."""
        from envforage.cli import cli
        from click.testing import CliRunner

        output_file = tmp_path / "report.json"

        with patch("envforage.cli.ReportBuilder") as mock_builder:
            mock_report = DiagnosticReport.model_validate(load_fixture("linux_gpu.json"))
            mock_builder.return_value.build.return_value = mock_report

            runner = CliRunner()
            result = runner.invoke(cli, ["diagnose", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists(), "Output file was not created"
        parsed = json.loads(output_file.read_text(encoding="utf-8"))
        assert "agent_version" in parsed
        assert "os" in parsed
        assert "gpus" in parsed

    def test_output_flag_quiet_still_writes_file(self, tmp_path) -> None:
        """--output with --quiet still writes the file even with no terminal output."""
        from envforage.cli import cli
        from click.testing import CliRunner

        output_file = tmp_path / "report.json"

        with patch("envforage.cli.ReportBuilder") as mock_builder:
            mock_report = DiagnosticReport.model_validate(load_fixture("linux_gpu.json"))
            mock_builder.return_value.build.return_value = mock_report

            runner = CliRunner()
            result = runner.invoke(cli, ["diagnose", "--output", str(output_file), "--quiet"])

        assert result.exit_code == 0
        assert output_file.exists(), "File must still be written in quiet mode"
        parsed = json.loads(output_file.read_text(encoding="utf-8"))
        assert "agent_version" in parsed

    def test_output_file_contains_all_report_fields(self, tmp_path) -> None:
        """The saved JSON contains all expected DiagnosticReport top-level fields."""
        from envforage.cli import cli
        from click.testing import CliRunner

        output_file = tmp_path / "report.json"

        with patch("envforage.cli.ReportBuilder") as mock_builder:
            mock_report = DiagnosticReport.model_validate(load_fixture("linux_gpu.json"))
            mock_builder.return_value.build.return_value = mock_report

            runner = CliRunner()
            result = runner.invoke(cli, ["diagnose", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists(), "Output file was not created"
        parsed = json.loads(output_file.read_text(encoding="utf-8"))
        for field in ["agent_version", "os", "cpu", "ram", "gpus", "cuda", "python_installations"]:
            assert field in parsed, f"Missing field: {field}"

    def test_without_output_flag_json_printed_to_stdout(self) -> None:
        """Without --output, the JSON report is echoed to stdout (pipe-friendly)."""
        from envforage.cli import cli
        from click.testing import CliRunner

        with patch("envforage.cli.ReportBuilder") as mock_builder:
            mock_report = DiagnosticReport.model_validate(load_fixture("linux_gpu.json"))
            mock_builder.return_value.build.return_value = mock_report

            runner = CliRunner()
            result = runner.invoke(cli, ["diagnose", "--quiet", "--format", "json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "agent_version" in parsed
        assert "os" in parsed

    def test_wsl_gpu_passthrough_warning_printed(self) -> None:
        from envforage.cli import cli
        from click.testing import CliRunner

        with patch("envforage.cli.ReportBuilder") as mock_builder:
            mock_report = DiagnosticReport.model_validate(load_fixture("wsl_cuda.json"))
            mock_builder.return_value.build.return_value = mock_report

            with patch(
                "envforage.cli.detect_wsl_gpu_passthrough",
                return_value=(False, ["Missing /dev/dxg"]),
            ):
                runner = CliRunner()
                result = runner.invoke(cli, ["--no-color", "diagnose"])

        assert result.exit_code == 0
        assert (
            "GPU passthrough unavailable in WSL2. Falling back to CPU environment recommendation."
            in result.output
        )
