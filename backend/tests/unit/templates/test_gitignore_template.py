from app.compatibility.models import ResolvedEnvironment
from app.templates.engine import TemplateRenderer
from app.templates.models import TemplateContext


def make_context(
    profile_name="ml-env",
    python_version="3.11",
):
    resolved = ResolvedEnvironment(
        python_version=python_version,
        cuda_version=None,
        target_os="LINUX",
        packages=[],
    )

    return TemplateContext(
        profile_id="test-id",
        profile_name=profile_name,
        resolved=resolved,
    )


def test_gitignore_template_renders():
    context = make_context()

    renderer = TemplateRenderer()
    result = renderer.render(".gitignore", context)

    assert "__pycache__/" in result.content
    assert ".venv/" in result.content
    assert "*.pt" in result.content
    assert "data/" in result.content