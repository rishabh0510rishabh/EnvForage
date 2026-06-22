"""
Template Engine — renders Jinja2 templates into setup scripts.

All rendered output passes through SafetyFilter before being returned.
This module never executes generated code; it only renders text.
"""

import logging
import sys
import tempfile
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from jinja2 import ChoiceLoader, FileSystemLoader, StrictUndefined, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

from app.config import get_settings
from app.templates.models import RenderResult, TemplateContext
from app.templates.safety import validate_rendered_output

# ── Template directory ─────────────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent / "jinja"

# ── Template name → output filename mapping ────────────────────────────────────
TEMPLATE_MAP: dict[str, str] = {
    "setup.sh": "setup/setup_linux.sh.j2",
    "setup.ps1": "setup/setup_windows.ps1.j2",
    "requirements.txt": "config/requirements.j2",
    "Dockerfile": "config/dockerfile.j2",
    "docker-compose.yml": "config/docker-compose.yml.j2",
    "Makefile": "config/makefile.j2",
    "devcontainer.json": "config/devcontainer.j2",
    "verify.sh": "verify/verify_generic.sh.j2",
    "verify_torch.sh": "verify/verify_torch.sh.j2",
    "verify_tf.sh": "verify/verify_tf.sh.j2",
    "verify_opencv.sh": "verify/verify_opencv.sh.j2",
    "verify_diffusers.sh": "verify/verify_diffusers.sh.j2",
    "environment.yml": "config/environment.yml.j2",
    "pyproject.toml": "config/pyproject.toml.j2",
    "pyproject.poetry.toml": "config/poetry.toml.j2",
    ".gitignore": "config/gitignore.j2",
}

# ── Profile-specific verify template mapping ───────────────────────────────────
PROFILE_VERIFY_TEMPLATES: dict[str, str] = {
    "pytorch-cuda": "verify_torch.sh",
    "tf-gpu": "verify_tf.sh",
    "yolov8": "verify_torch.sh",
    "stable-diffusion": "verify_diffusers.sh",
    "opencv-beginner": "verify_opencv.sh",
}


def _build_jinja_env() -> SandboxedEnvironment:
    return SandboxedEnvironment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
    )


@lru_cache(maxsize=16)
def _get_jinja_env(custom_template_dir: Path | None) -> SandboxedEnvironment:
    loaders = []
    if custom_template_dir:
        resolved_path = Path(custom_template_dir).resolve()
        project_root = Path(__file__).resolve().parent.parent.parent.parent

        is_valid = False
        try:
            resolved_path.relative_to(project_root)
            is_valid = True
        except ValueError:
            pass

        if not is_valid and "pytest" in sys.modules:
            temp_dir = Path(tempfile.gettempdir()).resolve()
            try:
                resolved_path.relative_to(temp_dir)
                is_valid = True
            except ValueError:
                pass

        if not is_valid:
            raise ValueError(
                f"custom_template_dir '{custom_template_dir}' resolved to '{resolved_path}' "
                f"which is outside the safe boundary (project root: '{project_root}')."
            )

        if resolved_path.exists() and resolved_path.is_dir():
            loaders.append(FileSystemLoader(str(resolved_path)))
        else:
            logging.getLogger(__name__).warning(
                "Configured custom_template_dir '%s' does not exist or is not a directory. "
                "Falling back to defaults.",
                custom_template_dir,
            )
    loaders.append(FileSystemLoader(str(TEMPLATES_DIR)))

    return SandboxedEnvironment(
        loader=ChoiceLoader(loaders),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


_JINJA_ENV = _get_jinja_env(None)


class TemplateRenderer:
    """
    Renders setup scripts from a TemplateContext.
    All output is safety-validated before returning.
    """

    async def render(
        self,
        output_filename: str,
        context: TemplateContext,
    ) -> RenderResult:
        """
        Render a single template to its output file content.

        Args:
            output_filename: Target filename, e.g. "setup.sh"
            context: Validated TemplateContext

        Returns:
            RenderResult with filename and rendered content

        Raises:
            KeyError: If output_filename is not in TEMPLATE_MAP
            SafetyViolationError: If rendered content contains forbidden patterns
            jinja2.UndefinedError: If template references undefined variable
        """
        template_path = TEMPLATE_MAP.get(output_filename)
        if template_path is None:
            raise KeyError(
                f"Unknown output format: '{output_filename}'. "
                f"Known: {list(TEMPLATE_MAP.keys())}"
            )

        settings = get_settings()
        env = _get_jinja_env(settings.custom_template_dir)
        template = env.get_template(template_path)
        rendered = template.render(**context.to_dict())
        safe_content = await validate_rendered_output(
            rendered, template_name=template_path
        )

        return RenderResult(filename=output_filename, content=safe_content)

    async def render_all(
        self,
        output_filenames: Sequence[str],
        context: TemplateContext,
    ) -> list[RenderResult]:
        """Render multiple output formats from the same context."""
        results = []
        for name in output_filenames:
            results.append(await self.render(name, context))
        return results
