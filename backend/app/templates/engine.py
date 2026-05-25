"""
Template Engine — renders Jinja2 templates into setup scripts.

All rendered output passes through SafetyFilter before being returned.
This module never executes generated code; it only renders text.
"""
from collections.abc import Sequence
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.templates.models import RenderResult, TemplateContext
from app.templates.safety import validate_rendered_output

# ── Template directory ─────────────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent / "jinja"

# ── Template name → output filename mapping ────────────────────────────────────
# Note: "setup.sh" is OS-aware and will be resolved based on target_os in render()
TEMPLATE_MAP: dict[str, str] = {
    "setup.sh":           "setup/setup_linux.sh.j2",  # Default; overridden by OS in render()
    "setup.ps1":          "setup/setup_windows.ps1.j2",
    "requirements.txt":   "config/requirements.j2",
    "Dockerfile":         "config/dockerfile.j2",
    "docker-compose.yml": "config/docker-compose.yml.j2",
    "devcontainer.json":  "config/devcontainer.j2",
    "verify.sh":          "verify/verify_generic.sh.j2",
    "verify_torch.sh":    "verify/verify_torch.sh.j2",
    "verify_torch_mps.sh": "verify/verify_torch_mps.sh.j2",
    "verify_tf.sh":       "verify/verify_tf.sh.j2",
    "verify_tf_metal.sh": "verify/verify_tf_metal.sh.j2",
    "verify_opencv.sh":   "verify/verify_opencv.sh.j2",
    "environment.yml":    "config/environment.yml.j2",
    "pyproject.toml":     "config/pyproject.toml.j2",
}

# ── OS-specific setup template mapping ──────────────────────────────────────────
OS_SETUP_TEMPLATES: dict[str, str] = {
    "LINUX": "setup/setup_linux.sh.j2",
    "WSL": "setup/setup_linux.sh.j2",
    "WIN": "setup/setup_windows.ps1.j2",
    "MACOS": "setup/setup_macos.sh.j2",
}

# ── Profile-specific verify template mapping ───────────────────────────────────
PROFILE_VERIFY_TEMPLATES: dict[str, str] = {
    "pytorch-cuda":        "verify_torch.sh",
    "pytorch-mps":         "verify_torch_mps.sh",
    "tf-gpu":              "verify_tf.sh",
    "tensorflow-metal":    "verify_tf_metal.sh",
    "yolov8":              "verify_torch.sh",
    "stable-diffusion":    "verify_torch.sh",
    "opencv-beginner":     "verify_opencv.sh",
    "llm-finetune":        "verify_torch.sh",
}

def _build_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


_JINJA_ENV = _build_jinja_env()


class TemplateRenderer:
    """
    Renders setup scripts from a TemplateContext.
    All output is safety-validated before returning.
    """

    def render(
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
        # Handle OS-specific setup.sh template selection
        if output_filename == "setup.sh":
            target_os = context.resolved.target_os
            template_path = OS_SETUP_TEMPLATES.get(target_os)
            if template_path is None:
                raise KeyError(
                    f"Unknown OS target for setup.sh: '{target_os}'. "
                    f"Known: {list(OS_SETUP_TEMPLATES.keys())}"
                )
        else:
            template_path = TEMPLATE_MAP.get(output_filename)
            if template_path is None:
                raise KeyError(
                    f"Unknown output format: '{output_filename}'. "
                    f"Known: {list(TEMPLATE_MAP.keys())}"
                )

        template = _JINJA_ENV.get_template(template_path)
        rendered = template.render(**context.to_dict())
        safe_content = validate_rendered_output(rendered, template_name=template_path)

        return RenderResult(filename=output_filename, content=safe_content)

    def render_all(
        self,
        output_filenames: Sequence[str],
        context: TemplateContext,
    ) -> list[RenderResult]:
        """Render multiple output formats from the same context."""
        return [self.render(name, context) for name in output_filenames]
