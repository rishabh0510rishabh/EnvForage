import pytest

from app.templates.safety import validate_rendered_output


@pytest.mark.asyncio
async def test_safety_filter_evasion_caught():
    """
    Test that the AST parser catches regex evasion attempts.
    """
    script = r"""#!/bin/bash
r"m" -rf /
"""
    # This shouldn't throw a SafetyViolationError (because regex doesn't match and AST just flags it as high risk, wait!)
    # Actually, `rm -rf /` might be caught by ShellCheck, but let's see.
    content, score = await validate_rendered_output(script, "setup.sh")
    assert score == "Medium" or score == "High"


@pytest.mark.asyncio
async def test_safety_score_eval():
    """
    Test that eval increases the risk score.
    """
    script = r"""#!/bin/bash
echo "test"
eval "ls -l"
"""
    # eval gives +2, unknown 'ls' gives +1 => 3 => Medium
    content, score = await validate_rendered_output(script, "setup.sh")
    assert score == "Medium"


@pytest.mark.asyncio
async def test_safety_score_base64_decode():
    """
    Test that base64 --decode increases the risk score.
    """
    script = r"""#!/bin/bash
base64 --decode
"""
    content, score = await validate_rendered_output(script, "setup.sh")
    assert score == "Medium" or score == "High"
