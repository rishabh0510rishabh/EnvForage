"""
Integration tests for the `envforge rollback` CLI command.
"""
from __future__ import annotations

import os
from unittest.mock import patch
from click.testing import CliRunner

from envforge_agent.cli import cli


class TestRollbackNoBackups:
    def test_exits_when_no_backups_found(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["rollback"])
        assert result.exit_code == 1

    def test_shows_helpful_hint_when_no_backups(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["rollback"])
        assert "backup" in result.output.lower()


class TestRollbackSingleBackup:
    def test_restores_single_backup_on_confirm(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("venv_backup_20260524")
            with open("venv_backup_20260524/pyvenv.cfg", "w") as f:
                f.write("version = 3.11")

            with patch("rich.prompt.Confirm.ask", return_value=True):
                result = runner.invoke(cli, ["rollback"])

        assert result.exit_code == 0
        assert "complete" in result.output.lower()

    def test_cancels_on_deny(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("venv_backup_20260524")
            with open("venv_backup_20260524/pyvenv.cfg", "w") as f:
                f.write("version = 3.11")

            with patch("rich.prompt.Confirm.ask", return_value=False):
                result = runner.invoke(cli, ["rollback"])

        assert result.exit_code == 0
        assert "cancel" in result.output.lower()


class TestRollbackMultipleBackups:
    def test_prompts_selection_for_multiple_backups(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("venv_backup_20260524")
            with open("venv_backup_20260524/pyvenv.cfg", "w") as f:
                f.write("")
            os.makedirs("venv_backup_20260523")
            with open("venv_backup_20260523/pyvenv.cfg", "w") as f:
                f.write("")

            with patch("rich.prompt.IntPrompt.ask", return_value=1):
                with patch("rich.prompt.Confirm.ask", return_value=False):
                    result = runner.invoke(cli, ["rollback"])

        assert result.exit_code == 0

    def test_backups_are_alphabetically_sorted(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("venv_backup_z")
            with open("venv_backup_z/pyvenv.cfg", "w") as f:
                f.write("")
            os.makedirs("venv_backup_a")
            with open("venv_backup_a/pyvenv.cfg", "w") as f:
                f.write("")

            with patch("rich.prompt.IntPrompt.ask", return_value=1):
                with patch("rich.prompt.Confirm.ask", return_value=False):
                    result = runner.invoke(cli, ["rollback"])

        assert result.exit_code == 0
        assert "venv_backup_a" in result.output
        assert "venv_backup_z" in result.output
        # Since choices are sorted, 'venv_backup_a' should appear before 'venv_backup_z'
        assert result.output.index("venv_backup_a") < result.output.index("venv_backup_z")


class TestRollbackFiltering:
    def test_ignores_non_directory_files(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("venv_backup_directory")
            with open("venv_backup_directory/pyvenv.cfg", "w") as f:
                f.write("")
            with open("venv_backup_file", "w") as f:
                f.write("not a directory")

            with patch("rich.prompt.Confirm.ask", return_value=False):
                result = runner.invoke(cli, ["rollback"])

        assert result.exit_code == 0
        assert "selecting: venv_backup_directory" in result.output
        assert "venv_backup_file" not in result.output


class TestRollbackRobustness:
    def test_rollback_failure_restores_original(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("venv")
            with open("venv/pyvenv.cfg", "w") as f:
                f.write("version = 3.11")

            os.makedirs("venv_backup_2026")
            with open("venv_backup_2026/pyvenv.cfg", "w") as f:
                f.write("version = 3.12")

            with patch("shutil.copytree", side_effect=Exception("Failed to copy")):
                with patch("rich.prompt.Confirm.ask", return_value=True):
                    result = runner.invoke(cli, ["rollback"])

            assert result.exit_code == 1
            assert "rollback failed" in result.output.lower()
            assert os.path.exists("venv")
            with open("venv/pyvenv.cfg", "r") as f:
                content = f.read()
            assert "version = 3.11" in content

    def test_invalid_name_parsing_fails(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("_backup_2026")
            with open("_backup_2026/pyvenv.cfg", "w") as f:
                f.write("")

            result = runner.invoke(cli, ["rollback"])

        assert result.exit_code == 1
        assert "could not determine original" in result.output.lower()

    def test_rollback_failure_when_no_original_exists_cleans_up(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.makedirs("venv_backup_2026")
            with open("venv_backup_2026/pyvenv.cfg", "w") as f:
                f.write("version = 3.12")

            def fake_copytree(src, dst):
                os.makedirs(dst)
                with open(os.path.join(dst, "partial.cfg"), "w") as f:
                    f.write("partial")
                raise Exception("Failed mid-copy")

            with patch("shutil.copytree", side_effect=fake_copytree):
                with patch("rich.prompt.Confirm.ask", return_value=True):
                    result = runner.invoke(cli, ["rollback"])

            assert result.exit_code == 1
            assert not os.path.exists("venv")