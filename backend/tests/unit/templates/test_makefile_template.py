"""Tests for the Makefile output format.

Regression: "Makefile" is a valid OutputFormat with a template on disk, but it
was missing from TEMPLATE_MAP, so requests for it raised KeyError -> HTTP 500.
Also includes a contract test ensuring the schema's OutputFormat values and the
renderer's TEMPLATE_MAP cannot drift apart again.
"""
from app.compatibility.models import ResolvedEnvironment, ResolvedPackage
from app.templates.engine import TEMPLATE_MAP, TemplateRenderer
from app.templates.models import TemplateContext


def make_context(
    profile_name="myenv",
    python_version="3.11",
    cuda_version=None,
    target_os="LINUX",
    packages=None,
):
    if packages is None:
        packages = []
    resolved = ResolvedEnvironment(
        python_version=python_version,
        cuda_version=cuda_version,
        target_os=target_os,
        packages=packages,
    )
    return TemplateContext(
        profile_id="test-id",
        profile_name=profile_name,
        resolved=resolved,
    )


async def test_makefile_is_registered():
    # The core regression: "Makefile" must be in TEMPLATE_MAP.
    assert "Makefile" in TEMPLATE_MAP


async def test_makefile_renders_expected_targets():
    context = make_context(
        profile_name="myenv",
        python_version="3.11",
        packages=[ResolvedPackage(name="numpy", version="1.26.0", cuda_variant=None)],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("Makefile", context)
    # Standard make targets the template defines.
    assert ".PHONY:" in result.content
    assert "install:" in result.content
    assert "verify:" in result.content
    assert "clean:" in result.content
    assert "help:" in result.content
    # Header carries profile/python metadata.
    assert "myenv" in result.content
    assert "3.11" in result.content


async def test_all_output_formats_have_registered_templates():
    """Contract test: every API-accepted OutputFormat must map to a template
    in TEMPLATE_MAP, and each mapped template file must exist on disk. This is
    the guard that prevents the schema/renderer drift that caused #1007.
    """
    import typing
    from pathlib import Path

    from app.schemas.script import OutputFormat
    from app.templates import engine as engine_module

    output_formats = typing.get_args(OutputFormat)
    assert output_formats, "OutputFormat literal should not be empty"

    jinja_root = Path(engine_module.__file__).parent / "jinja"
    for fmt in output_formats:
        assert fmt in TEMPLATE_MAP, (
            f"OutputFormat '{fmt}' is accepted by the API but missing from "
            f"TEMPLATE_MAP"
        )
        template_file = jinja_root / TEMPLATE_MAP[fmt]
        assert template_file.is_file(), (
            f"TEMPLATE_MAP['{fmt}'] points to '{TEMPLATE_MAP[fmt]}', which does "
            f"not exist at {template_file}"
        )