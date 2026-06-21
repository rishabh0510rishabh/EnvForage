"""Troubleshoot prompt builder — converts diagnostic context into LLM prompts.

The builder takes structured data (DiagnosticReport, profile info, user
description) and produces a safe, optimised user-message for the LLM.
All sensitive data is sanitised and token budgets are respected.
"""

import re
from typing import Any

from app.ai.models import TroubleshootRequest
from app.compatibility.matrix.cuda import (
    CUDA_MATRIX,
    FRAMEWORK_CUDA_SUPPORT,
    SUPPORTED_CUDA_VERSIONS,
)


class TroubleshootPromptBuilder:
    """
    Builds the user-message for the troubleshoot LLM call.

    Responsibilities:
        - Serialise diagnostic report into clean, structured context
        - Inject CUDA/Python compatibility matrix excerpts
        - Enforce token budget by truncating low-priority fields
        - Sanitise user input to prevent prompt injection
    """

    # Maximum characters for user description (prompt injection defence)
    MAX_USER_DESC_CHARS = 500

    def build(
        self, request: TroubleshootRequest, history: list[Any] | None = None
    ) -> str:
        """
        Build the user message from a TroubleshootRequest.

        Args:
            request: The structured troubleshoot request containing
                     diagnostic data, profile info, and user description.
            history: Optional list of previous AISuggestion objects.

        Returns:
            A formatted string to be passed as the ``user`` role message
            to the LLM provider.
        """
        sections: list[str] = []

        # ── Section 1: Diagnostic Report ──────────────────────────────────
        sections.append(self._build_diagnostic_section(request))

        # ── Section 2: Target Profile ─────────────────────────────────────
        if request.profile_slug:
            sections.append(self._build_profile_section(request))

        # ── Section 3: Compatibility Context ──────────────────────────────
        sections.append(self._build_compatibility_context(request))

        # ── Section 4: Session History ───────────────────────────────────
        if history:
            sections.append(self._build_history_section(history))

        # ── Section 5: User Description ───────────────────────────────────
        if request.user_description:
            sections.append(self._build_user_description(request.user_description))

        # ── Section 6: Instructions ───────────────────────────────────────
        sections.append(self._build_instructions())

        return "\n\n".join(sections)

    def _build_history_section(self, history: list[Any]) -> str:
        """Serialise previous AI suggestions for conversation context."""
        lines = ["## PREVIOUS SUGGESTIONS IN THIS SESSION"]
        for fix in history:
            # fix is an AISuggestion DB model
            lines.append(
                f"Step {getattr(fix, 'step_number', '?')}: {getattr(fix, 'title', 'Unknown')}"
            )
            lines.append(f"  {getattr(fix, 'description', '')}")
        return "\n".join(lines)

    # ── Private builders ──────────────────────────────────────────────────

    def _build_diagnostic_section(self, request: TroubleshootRequest) -> str:
        """Serialise the hardware/software diagnostic data."""
        diag = request.diagnostic
        lines = ["## DIAGNOSTIC REPORT"]

        # OS
        if diag.get("os"):
            os_info = diag["os"]
            lines.append(
                f"OS: {os_info.get('name', 'Unknown')} "
                f"({os_info.get('architecture', '?')})"
            )
            if os_info.get("wsl_version"):
                lines.append(f"WSL: {os_info['wsl_version']}")

        # CPU
        if diag.get("cpu"):
            cpu = diag["cpu"]
            lines.append(
                f"CPU: {cpu.get('brand', 'Unknown')} "
                f"({cpu.get('cores', '?')} cores, "
                f"{cpu.get('threads', '?')} threads)"
            )

        # RAM
        if diag.get("ram"):
            ram = diag["ram"]
            lines.append(
                f"RAM: {ram.get('total_gb', '?')} GB total, "
                f"{ram.get('available_gb', '?')} GB available"
            )

        # GPU(s)
        gpus = diag.get("gpus", [])
        if gpus:
            for i, gpu in enumerate(gpus):
                lines.append(
                    f"GPU[{i}]: {gpu.get('name', 'Unknown')} | "
                    f"VRAM: {gpu.get('vram_gb', '?')} GB | "
                    f"Driver: {gpu.get('driver_version', 'Unknown')}"
                )
        else:
            lines.append("GPU: None detected")

        # CUDA
        cuda = diag.get("cuda", {})
        cuda_ver = cuda.get("version")
        if cuda_ver:
            lines.append(f"CUDA: {cuda_ver}")
            if cuda.get("cudnn_version"):
                lines.append(f"cuDNN: {cuda['cudnn_version']}")
            if cuda.get("nccl_version"):
                lines.append(f"NCCL: {cuda['nccl_version']}")
        else:
            lines.append("CUDA: Not installed")

        # Python
        active_py = diag.get("active_python")
        if active_py:
            lines.append(
                f"Active Python: {active_py.get('version', '?')} "
                f"at {active_py.get('path', '?')}"
            )
            if active_py.get("is_venv"):
                lines.append(f"  (virtual env: {active_py.get('venv_path', '?')})")

        all_py = diag.get("python_installations", [])
        if all_py:
            versions = [p.get("version", "?") for p in all_py]
            lines.append(f"All Python versions: {', '.join(versions)}")

        return "\n".join(lines)

    def _build_profile_section(self, request: TroubleshootRequest) -> str:
        """Describe the target environment profile."""
        lines = [
            "## TARGET PROFILE",
            f"Profile: {request.profile_slug}",
        ]
        if request.profile_name:
            lines.append(f"Name: {request.profile_name}")
        if request.target_os:
            lines.append(f"Target OS: {request.target_os}")
        if request.python_version:
            lines.append(f"Requested Python: {request.python_version}")
        if request.cuda_version:
            lines.append(f"Requested CUDA: {request.cuda_version}")

        return "\n".join(lines)

    def _build_compatibility_context(self, request: TroubleshootRequest) -> str:
        """Inject relevant CUDA matrix data so the LLM has ground truth."""
        lines = ["## ENVFORAGE COMPATIBILITY CONTEXT"]
        lines.append(f"Supported CUDA versions: {', '.join(SUPPORTED_CUDA_VERSIONS)}")

        # If the user has CUDA, show the matrix entry
        cuda_ver = request.diagnostic.get("cuda", {}).get("version")
        if cuda_ver and cuda_ver in CUDA_MATRIX:
            entry = CUDA_MATRIX[cuda_ver]
            lines.append(
                f"CUDA {cuda_ver} requires driver >= {entry.min_driver_linux} (Linux) "
                f"/ {entry.min_driver_windows} (Windows)"
            )
            lines.append(f"Supported cuDNN: {', '.join(entry.cudnn_versions)}")

        # Show PyTorch CUDA support
        torch_support = FRAMEWORK_CUDA_SUPPORT.get("torch", {})
        if torch_support:
            recent = list(torch_support.items())[-3:]  # Last 3 versions
            for ver, cuda_list in recent:
                lines.append(f"PyTorch {ver} supports CUDA: {', '.join(cuda_list)}")

        return "\n".join(lines)

    def _sanitize_markdown(self, text: str) -> str:
        """
        Remove markdown structural characters to reduce prompt injection risk.
        """

        text = re.sub(r"^\s*(?:[#>*\-+]+|\d+\.)\s*", "", text, flags=re.MULTILINE)

        text = text.replace("`", "")
        text = text.replace("|", "")

        return text

    def _build_user_description(self, description: str) -> str:
        """Sanitise and include the user's free-text description."""
        # Truncate to prevent token overflow / injection
        sanitised = description[: self.MAX_USER_DESC_CHARS].strip()
        # Strip any attempt to override system instructions
        sanitised = sanitised.replace("RULES", "[REDACTED]")
        sanitised = sanitised.replace("IGNORE", "[REDACTED]")
        sanitised = sanitised.replace("system prompt", "[REDACTED]")
        sanitised = self._sanitize_markdown(sanitised)

        return f"## USER DESCRIPTION\n{sanitised}"

    def _build_instructions(self) -> str:
        """Final instruction block."""
        return (
            "## INSTRUCTIONS\n"
            "Analyse the diagnostic report above. Identify the root cause of any "
            "environment incompatibilities and provide ordered fix suggestions.\n"
            "Return ONLY valid JSON matching the TroubleshootResponse schema."
        )
