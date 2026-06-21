"""Fuzz tests for the template safety filter.

Uses Hypothesis to generate obfuscated variants of dangerous shell
commands and verify they are rejected, while also ensuring that
legitimate package management commands pass through cleanly.
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.templates.safety import SafetyViolationError, validate_rendered_output

# ── Strategies ──────────────────────────────────────────────────────────

# Whitespace + quoting obfuscation
_ws = st.sampled_from([" ", "\t", "  ", " \t "])
_quote = st.sampled_from(["", "'", '"'])


def _obfuscated_rm_rf():
    """Generate obfuscated `rm -rf /` variants."""
    return st.tuples(_ws, _ws, _ws, _quote).map(
        lambda t: f"rm{t[0]}-rf{t[1]}/{t[2]}"
    )


def _obfuscated_fork_bomb():
    """Generate fork bomb variants."""
    return st.just(":(){ :|:& };:")


def _curl_pipe_shell():
    """Generate curl-pipe-to-shell variants."""
    return st.tuples(
        st.sampled_from(["curl", "wget"]),
        st.sampled_from(["http://", "https://"]),
        st.from_regex(r"[a-z0-9]{3,12}\.[a-z]{2,4}", fullmatch=True),
        st.sampled_from(["bash", "sh"]),
    ).map(lambda t: f"{t[0]} {t[1]}{t[2]}/install.sh | {t[3]}")


def _destructive_sql():
    """Generate destructive SQL variants."""
    return st.tuples(
        st.sampled_from(["DROP DATABASE", "DROP TABLE", "TRUNCATE TABLE"]),
        st.from_regex(r"[a-z_]{3,12}", fullmatch=True),
    ).map(lambda t: f"{t[0]} {t[1]};")


# ── Tests — Dangerous commands MUST be caught ───────────────────────────


@given(cmd=_obfuscated_rm_rf())
@settings(max_examples=50)
async def test_rm_rf_always_caught(cmd: str):
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(cmd, "fuzz_rm_rf")


@given(cmd=_obfuscated_fork_bomb())
@settings(max_examples=5)
async def test_fork_bomb_always_caught(cmd: str):
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(cmd, "fuzz_fork_bomb")


@given(cmd=_curl_pipe_shell())
@settings(max_examples=30)
async def test_curl_pipe_shell_always_caught(cmd: str):
    # Exclude allowlisted domains
    assume("micro.mamba.pm" not in cmd and "astral.sh" not in cmd)
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(cmd, "fuzz_curl_pipe")


@given(cmd=_destructive_sql())
@settings(max_examples=30)
async def test_destructive_sql_always_caught(cmd: str):
    with pytest.raises(SafetyViolationError):
        await validate_rendered_output(cmd, "fuzz_sql")


# ── Tests — Safe commands MUST pass ─────────────────────────────────────


@pytest.mark.parametrize(
    "script",
    [
        "pip install numpy==1.26.4",
        "conda install -c conda-forge pytorch",
        "python -m venv .venv && source .venv/bin/activate",
        "pip install --upgrade pip setuptools wheel",
        "conda create -n myenv python=3.11 -y",
        "pip install -e '.[dev]'",
        "micromamba install -c conda-forge cuda-toolkit=12.1",
        'echo "Installation complete"',
        "export CUDA_HOME=/usr/local/cuda-12.1",
        "curl https://micro.mamba.pm/install.sh | bash",  # Allowlisted
    ],
)
async def test_safe_commands_pass(script: str):
    # Should NOT raise
    await validate_rendered_output(script, "fuzz_safe")


@given(pkg=st.from_regex(r"[a-z][a-z0-9_-]{1,20}", fullmatch=True))
@settings(max_examples=50)
async def test_pip_install_always_passes(pkg: str):
    script = f"pip install {pkg}"
    # Should NOT raise (no dangerous patterns)
    await validate_rendered_output(script, "fuzz_pip_install")
