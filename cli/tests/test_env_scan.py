from click.testing import CliRunner

from envforge_agent.env_scan.command import env_scan_command


def test_scan_env_command_runs():
    result = CliRunner().invoke(env_scan_command, ["."])

    assert result.exit_code == 0


def test_detects_used_unused_and_missing(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    (project / "app.py").write_text(
        """
import os

os.getenv("DATABASE_URL")
os.getenv("JWT_SECRET")
""",
        encoding="utf-8",
    )

    (project / ".env").write_text(
        """
DATABASE_URL=test
JWT_SECRET=secret
OLD_API_KEY=123
""",
        encoding="utf-8",
    )

    (project / ".env.example").write_text(
        """
DATABASE_URL=
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        env_scan_command,
        [
            str(project),
            "--env-file",
            str(project / ".env"),
            "--example-file",
            str(project / ".env.example"),
        ],
    )

    assert result.exit_code == 0

    assert "DATABASE_URL" in result.output
    assert "JWT_SECRET" in result.output
    assert "OLD_API_KEY appears unused" in result.output
    assert "JWT_SECRET used in code but missing" in result.output


def test_missing_env_files(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    (project / "app.py").write_text(
        """
import os

os.getenv("DATABASE_URL")
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        env_scan_command,
        [str(project)],
    )

    assert result.exit_code == 0