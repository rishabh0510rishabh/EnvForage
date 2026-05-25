"""Unit tests to verify custom template directory overrides and ChoiceLoader integration."""
from unittest.mock import MagicMock, patch

import pytest
from jinja2.sandbox import SecurityError

from app.compatibility.models import ResolvedEnvironment
from app.config import Settings
from app.templates.engine import TemplateRenderer
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


def test_default_rendering_without_custom_dir():
    """Verify that when no custom_template_dir is defined, default templates render normally."""
    context = make_context(profile_name="default-test", python_version="3.10")
    renderer = TemplateRenderer()

    result = renderer.render("environment.yml", context)
    assert "default-test" in result.content
    assert "python=3.10" in result.content


def test_custom_template_override_precedence(tmp_path):
    """Verify that a template in custom_template_dir takes precedence over the default one."""
    # 1. Set up a mock custom template folder and write a custom environment.yml.j2
    custom_dir = tmp_path / "custom_templates"
    config_dir = custom_dir / "config"
    config_dir.mkdir(parents=True)

    custom_template = config_dir / "environment.yml.j2"
    custom_template.write_text(
        "name: OVERRIDDEN_{{ profile.name }}\ncustom_indicator: yes",
        encoding="utf-8"
    )

    # 2. Mock get_settings() inside engine.py to return our custom_template_dir
    mock_settings = MagicMock(spec=Settings)
    mock_settings.custom_template_dir = custom_dir

    context = make_context(profile_name="myenv")
    renderer = TemplateRenderer()

    with patch("app.templates.engine.get_settings", return_value=mock_settings):
        result = renderer.render("environment.yml", context)

    assert "OVERRIDDEN_myenv" in result.content
    assert "custom_indicator: yes" in result.content
    # The default template contents should NOT be present
    assert "channels:" not in result.content


def test_custom_templates_subject_to_sandbox_hardening(tmp_path):
    """Verify that overridden templates from custom_template_dir are still fully sandboxed."""
    custom_dir = tmp_path / "custom_templates"
    config_dir = custom_dir / "config"
    config_dir.mkdir(parents=True)

    # Create an unsafe custom template attempting SSTI
    unsafe_template = config_dir / "environment.yml.j2"
    unsafe_template.write_text(
        "name: {{ ''.__class__ }}",
        encoding="utf-8"
    )

    mock_settings = MagicMock(spec=Settings)
    mock_settings.custom_template_dir = custom_dir

    context = make_context(profile_name="myenv")
    renderer = TemplateRenderer()

    with patch("app.templates.engine.get_settings", return_value=mock_settings):
        with pytest.raises(SecurityError) as exc_info:
            renderer.render("environment.yml", context)

    assert "access to attribute" in str(exc_info.value) or "is blocked" in str(exc_info.value)
