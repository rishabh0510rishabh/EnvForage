from app.compatibility.models import ResolvedEnvironment, ResolvedPackage
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


async def test_poetry_template_renders_basic():
    context = make_context(
        profile_name="myenv",
        python_version="3.10",
        packages=[
            ResolvedPackage(name="numpy", version="1.24.0", cuda_variant=None),
            ResolvedPackage(name="pandas", version="2.0.0", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("pyproject.poetry.toml", context)
    # Check headers
    assert "myenv" in result.content
    assert "3.10" in result.content
    # Check Poetry TOML format
    assert "[tool.poetry]" in result.content
    assert "[tool.poetry.dependencies]" in result.content
    assert 'python = "3.10.*"' in result.content
    assert 'numpy = "1.24.0"' in result.content
    assert 'pandas = "2.0.0"' in result.content
    # Check build-system
    assert "[build-system]" in result.content
    assert "poetry-core" in result.content


async def test_poetry_template_no_cuda():
    context = make_context(
        profile_name="cpu-env",
        python_version="3.9",
        cuda_version=None,
        packages=[
            ResolvedPackage(name="scipy", version="1.10.0", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("pyproject.poetry.toml", context)
    assert "CUDA" not in result.content
    assert 'scipy = "1.10.0"' in result.content


async def test_poetry_template_with_cuda():
    context = make_context(
        profile_name="gpu-env",
        python_version="3.11",
        cuda_version="11.8",
        packages=[
            ResolvedPackage(name="torch", version="2.0.0", cuda_variant="cu118"),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("pyproject.poetry.toml", context)
    assert "# CUDA     : 11.8" in result.content
    assert 'torch = "2.0.0+cu118"' in result.content


async def test_poetry_template_python_version_locked():
    """Verify Python version uses minor-version wildcard, not caret range."""
    context = make_context(
        profile_name="lock-test",
        python_version="3.12",
    )
    renderer = TemplateRenderer()
    result = await renderer.render("pyproject.poetry.toml", context)
    assert 'python = "3.12.*"' in result.content
    assert 'python = "^3.12"' not in result.content
