"""
Template Engine safety filter.

Validates rendered output for dangerous shell patterns before
returning scripts to the client. This is a hard safety gate —
no script passes without this validation.
"""
import asyncio
import logging
import re

from pydantic import BaseModel

from app.ai.providers.base import LLMProvider

logger = logging.getLogger(__name__)

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    # Pattern, Description
    (r"rm\s+-[rRf]{1,3}\s+/(?!\w)", "Recursive delete of root filesystem"),
    (r"rm\s+-[rRf]{1,3}\s+\$HOME", "Recursive delete of home directory"),
    (r"rm\s+-[rRf]{1,3}\s+~", "Recursive delete of home directory (tilde)"),
    (r"mkfs\.", "Filesystem format command"),
    (r"format\s+[A-Za-z]:", "Windows drive format command"),
    (r":(\s*)\(\s*\)\s*\{.*\|.*&", "Fork bomb pattern"),
    (r"dd\s+if=", "Raw disk write command"),
    (r">\s*/dev/sd[a-z]", "Direct disk write"),
    (r"shutdown\s+(/s|/r|-h|-r)", "System shutdown/reboot"),
    (r"DROP\s+DATABASE", "SQL database destruction"),
    (r"DROP\s+TABLE", "SQL table destruction"),
    (r"TRUNCATE\s+TABLE", "SQL table truncation"),
    (r"curl\s+.*\|\s*(ba)?sh", "Curl-pipe-to-shell (untrusted exec)"),
    (r"wget\s+.*-O-\s*\|\s*(ba)?sh", "Wget-pipe-to-shell (untrusted exec)"),
    (r"eval\s+\$\(", "Eval of subshell output"),
    (r"base64\s+--decode\s*\|.*sh", "Base64 decode pipe to shell"),
]

_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE | re.DOTALL), desc)
    for pattern, desc in FORBIDDEN_PATTERNS
]


class AISafetyVerdict(BaseModel):
    is_safe: bool
    reason: str


class SafetyViolationError(Exception):
    """Raised when rendered template output contains a forbidden pattern."""

    def __init__(self, pattern: str, description: str, context: str = "") -> None:
        self.pattern = pattern
        self.description = description
        self.context = context
        super().__init__(
            f"Safety violation detected: {description} "
            f"(pattern: {pattern!r})"
        )


def validate_rendered_output(
    content: str,
    template_name: str = "",
    llm_client: LLMProvider | None = None,
) -> str:
    """
    Scan rendered template output for forbidden patterns using Regex and an optional AI engine.

    Raises:
        SafetyViolationError: If a pattern is matched or the AI flags a malicious script.
    """
    for compiled_pattern, description in _COMPILED:
        if compiled_pattern.search(content):
            raise SafetyViolationError(
                pattern=compiled_pattern.pattern,
                description=description,
                context=f"Template: {template_name}",
            )

    if llm_client:
        system_prompt = (
            "You are a strict Linux security auditor. Review the user's generated bash script. "
            "Ensure it does not contain malicious code, hidden payloads, or destructive behavior."
        )
        user_message = f"Verify this script:\n\n{content}"

        try:
            method_to_call = getattr(
                llm_client,
                "generate_response",
                getattr(llm_client, "complete", None),
            )

            if method_to_call is None:
                raise AttributeError(
                    "LLM client does not implement a recognized completion method."
                )

            verdict = asyncio.run(
                method_to_call(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    response_model=AISafetyVerdict,
                )
            )

            if not verdict.is_safe:
                raise SafetyViolationError(
                    pattern="AI_SAFETY_FILTER_FLAG",
                    description=f"AI Auditor flagged this script: {verdict.reason}",
                    context=f"Template: {template_name}",
                )
        except Exception as e:
            logger.error(f"AI Safety check skipped due to provider error: {str(e)}")

    return content
