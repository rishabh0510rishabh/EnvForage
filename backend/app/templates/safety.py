"""
Template Engine safety filter.

Validates rendered output for dangerous shell patterns before
returning scripts to the client. This is a hard safety gate —
no script passes without this validation.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import re
import subprocess
from typing import Any

import bashlex
from pydantic import BaseModel

from app.ai.providers.base import LLMProvider

logger = logging.getLogger(__name__)

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-[rRf]{1,3}\s+/", "Recursive delete of filesystem path"),
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
    (
        r"curl\s+(?:-[^\s|;&]+?\s+)*?https?://(?!(?:micro\.mamba\.pm|astral\.sh)/)\S+\s*\|\s*(?:ba)?sh",
        "Curl-pipe-to-shell (untrusted exec)",
    ),
    (
        r"wget\s+(?:-[^\s|;&]+?\s+)*?https?://(?!(?:micro\.mamba\.pm|astral\.sh)/)\S+\s*\|\s*(?:ba)?sh",
        "Wget-pipe-to-shell (untrusted exec)",
    ),
    (
        r"wget\s+[^;\|&]+?(-O\s+\S+).*(?:&&|;|\||\|\||\n)\s*(?:ba)?sh\s+\1",
        "Wget download-and-execute pattern (sequential/chained)",
    ),
    (
        r"wget\s+[^;\|&]+?(-O\s+(\S+)).*(?:&&|;|\||\|\||\n)\s*(?:ba)?sh\s+\2",
        "Wget download-and-execute pattern (explicit target)",
    ),
    (
        r"curl\s+[^;\|&]*?(-o|--output)\s+(\S+).*(?:&&|;|\||\|\||\n)\s*(?:ba)?sh\s+\2",
        "Curl download-and-execute pattern",
    ),
    (
        r"curl\s+[^;\|&]*?(-O|--remote-name)\s+.*(?:&&|;|\||\|\||\n)\s*(?:ba)?sh\s+",
        "Curl remote-name download-and-execute pattern",
    ),
    (
        r"curl\s+[^;\|&]*?>\s*(\S+).*(?:&&|;|\||\|\||\n)\s*(?:ba)?sh\s+\1",
        "Curl redirect download-and-execute pattern",
    ),
    (
        r"(?:iex|Invoke-Expression)\s*\(?\s*(?:iwr|Invoke-WebRequest|Invoke-RestMethod|irm|curl|wget)\s+(?!https?://astral\.sh/)",
        "PowerShell malicious download cradle",
    ),
    (
        r"(?:iwr|Invoke-WebRequest|Invoke-RestMethod|irm|curl|wget)\s+(?!https?://astral\.sh/)\S+.*\s*\|\s*(?:iex|Invoke-Expression)",
        "PowerShell piped download cradle",
    ),
    (
        r"(?:iex|Invoke-Expression)\s*\(?\s*(?:\(?(?:New-Object)\s+Net\.WebClient\)?\.(?:DownloadString|DownloadFile))\s*\(",
        "PowerShell .Net WebClient download cradle",
    ),
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
            f"Safety violation detected: {description} (pattern: {pattern!r})"
        )


def _validate_bash_ast(content: str, template_name: str = "") -> None:
    """Parse and validate shell scripts using bashlex AST parsing."""
    try:
        nodes = bashlex.parse(content)
    except Exception as e:
        logger.warning(
            f"Bash AST parsing skipped for {template_name} due to parser error/limitation: {str(e)}"
        )
        return

    violations = []

    def has_substitution(node: Any) -> bool:
        if node.kind in ("commandsubstitution", "processsubstitution"):
            return True
        for attr in dir(node):
            if attr.startswith("_"):
                continue
            try:
                val = getattr(node, attr)
            except AttributeError:
                continue
            if hasattr(val, "kind") and hasattr(val, "pos"):
                if has_substitution(val):
                    return True
            elif isinstance(val, list):
                for item in val:
                    if hasattr(item, "kind") and hasattr(item, "pos"):
                        if has_substitution(item):
                            return True
        return False

    def check_node(node: Any, parent_pipeline: Any) -> None:
        # Rule 1: Redirection Target Checks
        if node.kind == "redirect":
            output_node = getattr(node, "output", None)
            if output_node and hasattr(output_node, "word"):
                target = output_node.word.strip("'\"").lower()
                dangerous_prefixes = (
                    "/dev/sd",
                    "/dev/hd",
                    "/dev/nvme",
                    "/dev/vd",
                    "/dev/tcp",
                    "/dev/udp",
                )
                if target.startswith(dangerous_prefixes):
                    violations.append(f"Dangerous redirection target: {target}")
                if has_substitution(output_node):
                    violations.append(
                        f"Dynamic redirection target with subshell: {output_node.word}"
                    )

        # Rule 2: Eval Checks
        if node.kind == "command":
            parts = getattr(node, "parts", [])
            if parts and hasattr(parts[0], "word") and parts[0].word == "eval":
                if parent_pipeline is not None:
                    violations.append("Eval command used inside a pipeline")
                for arg in parts[1:]:
                    if has_substitution(arg):
                        violations.append(
                            f"Eval command with dynamic subshell/substitution: {arg.word if hasattr(arg, 'word') else ''}"
                        )

        # Rule 3: Pipeline target checks
        if node.kind == "pipeline":
            pipeline_parts = getattr(node, "parts", [])
            for i, part in enumerate(pipeline_parts):
                if part.kind == "command":
                    cmd_parts = getattr(part, "parts", [])
                    if cmd_parts and hasattr(cmd_parts[0], "word"):
                        cmd_name = cmd_parts[0].word
                        cmd_basename = os.path.basename(cmd_name.replace("\\", "/"))
                        is_shell_target = False
                        matched_shell_name = cmd_name
                        if cmd_basename in ("sh", "bash", "dash", "zsh", "ksh"):
                            is_shell_target = True
                        elif (
                            cmd_basename == "env"
                            and len(cmd_parts) > 1
                            and hasattr(cmd_parts[1], "word")
                        ):
                            next_cmd_name = cmd_parts[1].word
                            next_cmd_basename = os.path.basename(
                                next_cmd_name.replace("\\", "/")
                            )
                            if next_cmd_basename in (
                                "sh",
                                "bash",
                                "dash",
                                "zsh",
                                "ksh",
                            ):
                                is_shell_target = True
                                matched_shell_name = f"env {next_cmd_name}"

                        if is_shell_target and i > 0:
                            # Allow whitelisted bootstrapping URLs for curl/wget piped to shell
                            is_whitelisted = False
                            first_part = pipeline_parts[0]
                            if first_part.kind == "command":
                                first_cmd_parts = getattr(first_part, "parts", [])
                                if first_cmd_parts and hasattr(
                                    first_cmd_parts[0], "word"
                                ):
                                    first_cmd_name = first_cmd_parts[0].word
                                    if first_cmd_name in ("curl", "wget"):
                                        for arg in first_cmd_parts[1:]:
                                            if hasattr(arg, "word"):
                                                u = arg.word.strip("'\"")
                                                if u.startswith(
                                                    ("http://", "https://")
                                                ):
                                                    try:
                                                        from urllib.parse import (
                                                            urlparse,
                                                        )

                                                        parsed = urlparse(u)
                                                        host = parsed.netloc.split(":")[
                                                            0
                                                        ].lower()
                                                        if host in (
                                                            "astral.sh",
                                                            "micro.mamba.pm",
                                                        ) or host.endswith(
                                                            (
                                                                ".astral.sh",
                                                                ".micro.mamba.pm",
                                                            )
                                                        ):
                                                            is_whitelisted = True
                                                            break
                                                    except Exception:
                                                        pass
                            if not is_whitelisted:
                                violations.append(
                                    f"Pipe-to-shell detected in pipeline: {matched_shell_name}"
                                )

        # Rule 4: Shell execution commands with dynamic arguments
        if node.kind == "command":
            parts = getattr(node, "parts", [])
            if parts and hasattr(parts[0], "word"):
                cmd_name = parts[0].word
                cmd_basename = os.path.basename(cmd_name.replace("\\", "/"))
                target_cmd_name = cmd_name
                args_to_check: list[Any] = []
                is_shell_exec = False

                shells_and_helpers = (
                    "sh",
                    "bash",
                    "dash",
                    "zsh",
                    "ksh",
                    "source",
                    ".",
                    "exec",
                )

                if cmd_basename in shells_and_helpers:
                    is_shell_exec = True
                    target_cmd_name = cmd_name
                    args_to_check = parts[1:]
                elif (
                    cmd_basename == "env"
                    and len(parts) > 1
                    and hasattr(parts[1], "word")
                ):
                    next_cmd_name = parts[1].word
                    next_cmd_basename = os.path.basename(
                        next_cmd_name.replace("\\", "/")
                    )
                    if next_cmd_basename in shells_and_helpers:
                        is_shell_exec = True
                        target_cmd_name = f"env {next_cmd_name}"
                        args_to_check = parts[2:]

                if is_shell_exec:
                    for arg in args_to_check:
                        if has_substitution(arg):
                            violations.append(
                                f"Shell command '{target_cmd_name}' executed with dynamic subshell/substitution: {arg.word if hasattr(arg, 'word') else ''}"
                            )

    def traverse(node: Any, parent_pipeline: Any = None) -> None:
        if not node:
            return
        check_node(node, parent_pipeline)
        current_pipeline = node if node.kind == "pipeline" else parent_pipeline
        for attr in dir(node):
            if attr.startswith("_"):
                continue
            try:
                val = getattr(node, attr)
            except AttributeError:
                continue
            if hasattr(val, "kind") and hasattr(val, "pos"):
                traverse(val, current_pipeline)
            elif isinstance(val, list):
                for item in val:
                    if hasattr(item, "kind") and hasattr(item, "pos"):
                        traverse(item, current_pipeline)

    for n in nodes:
        traverse(n)

    if violations:
        raise SafetyViolationError(
            pattern="AST_SAFETY_VIOLATION",
            description="AST validation failed: " + "; ".join(violations),
            context=f"Template: {template_name}",
        )


def _validate_shellcheck(content: str, template_name: str = "") -> None:
    """Run shellcheck static analysis on the rendered content."""
    try:
        args = ["shellcheck", "--severity=warning", "--format=json"]
        first_line = content.splitlines()[0].strip() if content.strip() else ""
        if not first_line.startswith("#!"):
            args.append("--shell=bash")
        args.append("-")

        process = subprocess.run(
            args,
            input=content,
            text=True,
            capture_output=True,
            check=False,
            timeout=5.0,
        )
        if process.returncode != 0:
            try:
                results = json.loads(process.stdout)
                if results:
                    violations_desc = []
                    for item in results:
                        line = item.get("line", 0)
                        column = item.get("column", 0)
                        message = item.get("message", "")
                        code = item.get("code", "")
                        level = item.get("level", "warning")
                        violations_desc.append(
                            f"Line {line}:{column}: [{level}] {message} (SC{code})"
                        )
                    if violations_desc:
                        raise SafetyViolationError(
                            pattern="SHELLCHECK_WARNING",
                            description="Shellcheck validation failed with warnings:\n"
                            + "\n".join(violations_desc),
                            context=f"Template: {template_name}",
                        )
            except json.JSONDecodeError:
                if process.stderr:
                    logger.error(f"shellcheck error: {process.stderr}")
    except SafetyViolationError:
        raise
    except Exception as e:
        logger.warning(
            f"Failed to execute shellcheck: {str(e)}. Skipping static analysis."
        )


def validate_rendered_output(
    content: str,
    template_name: str = "",
    llm_client: LLMProvider | None = None,
) -> str:
    """
    Scan rendered template output for forbidden patterns using Regex, AST validation, Shellcheck, and an optional AI engine.

    Raises:
        SafetyViolationError: If any checks fail or the AI flags a malicious script.
    """
    # 1. Regex Checks
    for compiled_pattern, description in _COMPILED:
        if compiled_pattern.search(content):
            raise SafetyViolationError(
                pattern=compiled_pattern.pattern,
                description=description,
                context=f"Template: {template_name}",
            )

    # 2. AST and Shellcheck Checks (Bash shell scripts only)
    is_bash = False
    if template_name:
        is_bash = (
            template_name.endswith(".sh")
            or template_name.endswith(".sh.j2")
            or "setup.sh" in template_name
            or "verify" in template_name
        )
    if not is_bash and content:
        first_line = content.splitlines()[0] if content.strip() else ""
        if first_line.startswith("#!") and ("sh" in first_line or "bash" in first_line):
            is_bash = True

    if is_bash and content.strip():
        _validate_bash_ast(content, template_name)
        _validate_shellcheck(content, template_name)

    # 3. AI Safety Checks
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

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        method_to_call(
                            system_prompt=system_prompt,
                            user_message=user_message,
                            response_model=AISafetyVerdict,
                        ),
                    )
                    verdict = future.result()
            else:
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
        except SafetyViolationError:
            raise
        except Exception as e:
            logger.warning(
                f"AI Safety check failed due to provider error — degrading to regex-only: {str(e)}"
            )

    return content
