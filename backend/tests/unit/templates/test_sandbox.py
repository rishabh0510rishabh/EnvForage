"""Unit tests to verify template engine sandboxing restrictions and functionality."""

import pytest
from jinja2.sandbox import SandboxedEnvironment, SecurityError

from app.compatibility.models import ResolvedEnvironment
from app.templates.engine import _JINJA_ENV, TemplateRenderer
from app.templates.models import TemplateContext


def make_context(
    profile_name="myenv",
    python_version="3.10",
    cuda_version=None,
    packages=None,
):
    if packages is None:
        packages = []
    resolved = ResolvedEnvironment(
        python_version=python_version,
        cuda_version=cuda_version,
        target_os="LINUX",
        packages=packages,
    )
    return TemplateContext(
        profile_id="test-id",
        profile_name=profile_name,
        resolved=resolved,
    )


async def test_sandbox_environment_active():
    """Verify that _JINJA_ENV is an instance of SandboxedEnvironment."""
    assert isinstance(_JINJA_ENV, SandboxedEnvironment)


async def test_sandbox_blocks_unsafe_attributes():
    """Verify that accessing dangerous python class internals is restricted."""
    env = _JINJA_ENV

    # Attempting template injection with dangerous attributes
    unsafe_templates = [
        "{{ ''.__class__ }}",
        "{{ [].__class__.__mro__ }}",
        "{{ ().__class__.__bases__[0].__subclasses__() }}",
        "{{ self.__init__.__globals__ }}",
    ]

    for t_str in unsafe_templates:
        template = env.from_string(t_str)
        with pytest.raises(SecurityError) as exc_info:
            template.render()
        assert "access to attribute" in str(exc_info.value) or "is blocked" in str(
            exc_info.value
        )


async def test_sandbox_allows_safe_filters_and_rendering():
    """Verify that safe built-in filters (default, replace) execute perfectly."""
    env = _JINJA_ENV

    # Test 'default' filter
    template_default = env.from_string("{{ value | default('fallback') }}")
    assert template_default.render() == "fallback"
    assert template_default.render(value="custom") == "custom"

    # Test 'replace' filter
    template_replace = env.from_string("{{ value | replace('.', '-') }}")
    assert template_replace.render(value="3.11") == "3-11"


async def test_sandbox_integration_with_renderer():
    """Verify that TemplateRenderer works cleanly under the sandboxed environment."""
    context = make_context(
        profile_name="sandbox-test",
        python_version="3.10",
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "sandbox-test" in result.content
    assert "python=3.10" in result.content
