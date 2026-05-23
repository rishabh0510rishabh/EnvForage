"""Repair Script Service — renders repair templates from AI suggestions.

The AI suggests a ``repair_template_id``. This service looks up the
corresponding Jinja2 template, renders it with validated parameters,
and passes the output through the SafetyFilter before returning.

Flow:
    AI suggestion → template lookup → render → SafetyFilter → return script
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    select_autoescape,
)

from app.ai.prompts.system import AVAILABLE_REPAIR_TEMPLATES
from app.templates.safety import validate_rendered_output

logger = logging.getLogger(__name__)

# ── Template directory ────────────────────────────────────────────────────────
REPAIR_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "jinja" / "repair"

# ── Template ID → Jinja2 filename mapping ─────────────────────────────────────
REPAIR_TEMPLATE_MAP: dict[str, str] = {
    "repair_cuda_upgrade": "repair_cuda_upgrade.sh.j2",
    "repair_python_install": "repair_python_install.sh.j2",
    "repair_driver_update": "repair_driver_update.sh.j2",
    "repair_venv_recreate": "repair_venv_recreate.sh.j2",
    "repair_pip_reinstall": "repair_pip_reinstall.sh.j2",
}

# ── Default context values ────────────────────────────────────────────────────
_DEFAULT_CONTEXT: dict[str, Any] = {
    "envforge_version": "0.4.0",
    "generated_at": "",  # Filled at render time
}


def _build_repair_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(REPAIR_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


_REPAIR_ENV = _build_repair_env()


class RepairTemplateNotFoundError(Exception):
    """Raised when a repair_template_id is not in the registry."""
    def __init__(self, template_id: str) -> None:
        self.template_id = template_id
        valid = ", ".join(AVAILABLE_REPAIR_TEMPLATES)
        super().__init__(
            f"Unknown repair template: '{template_id}'. "
            f"Valid templates: {valid}"
        )


class RepairService:
    """
    Renders repair scripts from AI-suggested template IDs.

    Usage::

        service = RepairService()
        result = service.render_repair("repair_cuda_upgrade", {
            "target_cuda_version": "12.1",
        })
    """

    def render_repair(
        self,
        template_id: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Render a repair script from a template ID and parameters.

        Args:
            template_id: One of the AVAILABLE_REPAIR_TEMPLATES.
            params: Template parameters (merged with defaults).

        Returns:
            Dict with ``template_id``, ``filename``, ``content``, and ``size_bytes``.

        Raises:
            RepairTemplateNotFoundError: If template_id is unknown.
            SafetyViolationError: If rendered content fails safety check.
        """
        # Validate template ID
        if template_id not in REPAIR_TEMPLATE_MAP:
            raise RepairTemplateNotFoundError(template_id)

        template_filename = REPAIR_TEMPLATE_MAP[template_id]

        # Build context
        context = {**_DEFAULT_CONTEXT}
        context["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        if params:
            context.update(params)

        # Render
        template = _REPAIR_ENV.get_template(template_filename)
        rendered = template.render(**context)

        # Safety filter
        safe_content = validate_rendered_output(
            rendered, template_name=f"repair/{template_filename}"
        )

        # Build output filename (strip .j2)
        output_filename = template_filename.replace(".j2", "")

        logger.info(
            "Repair script rendered: %s (%d bytes)",
            template_id, len(safe_content.encode("utf-8")),
        )

        return {
            "template_id": template_id,
            "filename": output_filename,
            "content": safe_content,
            "size_bytes": len(safe_content.encode("utf-8")),
        }

    def list_templates(self) -> list[dict[str, str]]:
        """List all available repair templates with descriptions."""
        descriptions = {
            "repair_cuda_upgrade": "Upgrade CUDA toolkit to a supported version",
            "repair_python_install": "Install or switch Python version (pyenv/system)",
            "repair_driver_update": "Check and guide NVIDIA driver update",
            "repair_venv_recreate": "Back up and recreate Python virtual environment",
            "repair_pip_reinstall": "Force-reinstall pip packages with correct versions",
        }
        return [
            {"id": tid, "description": descriptions.get(tid, "")}
            for tid in AVAILABLE_REPAIR_TEMPLATES
        ]
