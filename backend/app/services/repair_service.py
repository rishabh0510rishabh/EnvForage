"""Repair Script Service — renders repair templates from AI suggestions.

The AI suggests a ``repair_template_id``. This service looks up the
corresponding Jinja2 template, renders it with validated parameters,
and passes the output through the SafetyFilter before returning.

Flow:
    AI suggestion -> template lookup -> param validation -> render -> SafetyFilter -> return script
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import (
    StrictUndefined,
    select_autoescape,
)
from jinja2.sandbox import SandboxedEnvironment

from app.ai.prompts.system import AVAILABLE_REPAIR_TEMPLATES
from app.templates.safety import validate_rendered_output

logger = logging.getLogger(__name__)

# ── Template directory ────────────────────────────────────────────────────────
REPAIR_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "jinja" / "repair"

# ── Template ID -> Jinja2 filename mapping ─────────────────────────────────────
REPAIR_TEMPLATE_MAP: dict[str, str] = {
    "repair_cuda_upgrade": "repair_cuda_upgrade.sh.j2",
    "repair_python_install": "repair_python_install.sh.j2",
    "repair_driver_update": "repair_driver_update.sh.j2",
    "repair_venv_recreate": "repair_venv_recreate.sh.j2",
    "repair_pip_reinstall": "repair_pip_reinstall.sh.j2",
}

# ── Default context values ────────────────────────────────────────────────────
_DEFAULT_CONTEXT: dict[str, Any] = {
    "envforage_version": "0.4.0",
    "generated_at": "",  # Filled at render time
}

# ── Per-template allowed param keys with value validation regexes ─────────────
# None as a regex means the param is validated separately (e.g. structured types).
_ALLOWED_PARAMS: dict[str, dict[str, str | None]] = {
    "repair_cuda_upgrade": {
        "target_cuda_version": r"^\d+\.\d+(\.\d+)?$",
    },
    "repair_python_install": {
        "target_python_version": r"^\d+\.\d+$",
    },
    "repair_driver_update": {
        "min_driver_version": r"^\d+(\.\d+)*$",
    },
    "repair_venv_recreate": {
        "python_bin": r"^[a-zA-Z0-9/_.-]+$",
        "venv_dir": r"^[a-zA-Z0-9/_.-]+$",
    },
    "repair_pip_reinstall": {
        "packages": None,  # list of dicts validated field-by-field below
    },
}

_SAFE_PKG_NAME = re.compile(r"^[a-zA-Z0-9_.-]+$")
_SAFE_PKG_VERSION = re.compile(r"^[\d.a-zA-Z_+!=-]*$")
_SAFE_PIP_SPEC = re.compile(r"^[a-zA-Z0-9_.\[\]~!=<>,; +@-]+$")
_SAFE_INDEX_URL = re.compile(r"^https?://[^\s]+$")


def _validate_package_entry(entry: Any, index: int) -> None:
    if not isinstance(entry, dict):
        raise ValueError(
            f"packages[{index}] must be a mapping, got {type(entry).__name__}"
        )
    name = entry.get("name", "")
    if not isinstance(name, str) or not _SAFE_PKG_NAME.match(name):
        raise ValueError(f"packages[{index}].name contains unsafe characters: {name!r}")
    version = entry.get("version")
    if version is not None:
        if not isinstance(version, str) or not _SAFE_PKG_VERSION.match(version):
            raise ValueError(
                f"packages[{index}].version contains unsafe characters: {version!r}"
            )
    pip_spec = entry.get("pip_spec", "")
    if not isinstance(pip_spec, str) or not _SAFE_PIP_SPEC.match(pip_spec):
        raise ValueError(
            f"packages[{index}].pip_spec contains unsafe characters: {pip_spec!r}"
        )
    index_url = entry.get("index_url")
    if index_url is not None:
        if not isinstance(index_url, str) or not _SAFE_INDEX_URL.match(index_url):
            raise ValueError(
                f"packages[{index}].index_url is not a valid URL: {index_url!r}"
            )


def _validate_params(template_id: str, params: dict[str, Any]) -> None:
    allowed = _ALLOWED_PARAMS.get(template_id, {})
    for key in params:
        if key not in allowed:
            raise ValueError(
                f"Unknown param '{key}' for template '{template_id}'. "
                f"Allowed: {sorted(allowed)}"
            )
    for key, pattern in allowed.items():
        if key not in params:
            continue
        value = params[key]
        if pattern is None:
            if key == "packages":
                if not isinstance(value, list):
                    raise ValueError("'packages' must be a list")
                for i, entry in enumerate(value):
                    _validate_package_entry(entry, i)
        else:
            if not isinstance(value, str):
                raise ValueError(
                    f"Param '{key}' must be a string, got {type(value).__name__}"
                )
            if not re.fullmatch(pattern, value):
                raise ValueError(
                    f"Param '{key}' value {value!r} does not match allowed pattern {pattern!r}"
                )
            # Reject absolute paths and traversal sequences for
            # filesystem-sensitive parameters (prevents venv_dir=/etc,
            # python_bin=../../bin/sh, etc.)
            if key in ("venv_dir", "python_bin"):
                if value.startswith("/") or value.startswith("~") or ".." in value:
                    raise ValueError(
                        f"Param '{key}' must be a relative path without "
                        f"'..' or leading '/' or '~': {value!r}"
                    )


def _build_repair_env() -> SandboxedEnvironment:
    from jinja2 import FileSystemLoader

    return SandboxedEnvironment(
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
            f"Unknown repair template: '{template_id}'. Valid templates: {valid}"
        )


class RepairParamError(ValueError):
    """Raised when repair template params fail validation."""


class RepairService:
    """
    Renders repair scripts from AI-suggested template IDs.

    Usage::

        service = RepairService()
        result = service.render_repair("repair_cuda_upgrade", {
            "target_cuda_version": "12.1",
        })
    """

    async def render_repair(
        self,
        template_id: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Render a repair script from a template ID and parameters.

        Args:
            template_id: One of the AVAILABLE_REPAIR_TEMPLATES.
            params: Template parameters (validated against per-template allowlist).

        Returns:
            Dict with ``template_id``, ``filename``, ``content``, and ``size_bytes``.

        Raises:
            RepairTemplateNotFoundError: If template_id is unknown.
            RepairParamError: If params contain unknown keys or unsafe values.
            SafetyViolationError: If rendered content fails safety check.
        """
        # Validate template ID
        if template_id not in REPAIR_TEMPLATE_MAP:
            raise RepairTemplateNotFoundError(template_id)

        template_filename = REPAIR_TEMPLATE_MAP[template_id]

        # Validate params against per-template allowlist
        if params:
            try:
                _validate_params(template_id, params)
            except ValueError as exc:
                raise RepairParamError(str(exc)) from exc

        # Build context
        context = {**_DEFAULT_CONTEXT}
        context["generated_at"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        if params:
            context.update(params)

        # Render via sandboxed environment
        template = _REPAIR_ENV.get_template(template_filename)
        rendered = template.render(**context)

        # Safety filter
        safe_content = await validate_rendered_output(
            rendered, template_name=f"repair/{template_filename}"
        )

        # Build output filename (strip .j2)
        output_filename = template_filename.replace(".j2", "")

        logger.info(
            "Repair script rendered: %s (%d bytes)",
            template_id,
            len(safe_content.encode("utf-8")),
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
