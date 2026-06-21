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


async def test_conda_template_renders_basic():
    context = make_context(
        profile_name="myenv",
        python_version="3.10",
        packages=[
            ResolvedPackage(name="numpy", version="1.24.0", cuda_variant=None),
            ResolvedPackage(name="pandas", version="2.0.0", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "myenv" in result.content
    assert "3.10" in result.content
    assert "numpy" in result.content
    assert "pandas" in result.content


async def test_conda_template_no_cuda():
    context = make_context(
        profile_name="cpu-env",
        python_version="3.9",
        cuda_version=None,
        packages=[
            ResolvedPackage(name="scipy", version="1.10.0", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "cpu-env" in result.content
    assert "scipy" in result.content


async def test_conda_template_with_cuda():
    context = make_context(
        profile_name="gpu-env",
        python_version="3.11",
        cuda_version="11.8",
        packages=[
            ResolvedPackage(name="torch", version="2.0.0", cuda_variant="cu118"),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "gpu-env" in result.content
    assert "3.11" in result.content
    assert "torch" in result.content


async def test_conda_template_contains_channels():
    """Output must include the channels section with conda-forge."""
    context = make_context(profile_name="myenv", python_version="3.10")
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "channels:" in result.content
    assert "conda-forge" in result.content
    assert "defaults" in result.content


async def test_conda_template_contains_install_comment():
    """Output must include the conda env create install instruction."""
    context = make_context(profile_name="myenv", python_version="3.10")
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "conda env create -f environment.yml" in result.content


async def test_conda_template_python_version_uses_single_equals():
    """Conda requires 'python=3.10' not 'python==3.10'."""
    context = make_context(profile_name="myenv", python_version="3.10")
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "python=3.10" in result.content
    assert "python==3.10" not in result.content


async def test_conda_template_empty_packages():
    """Template renders cleanly with no packages — only python dependency."""
    context = make_context(profile_name="empty-env", python_version="3.11", packages=[])
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "empty-env" in result.content
    assert "python=3.11" in result.content
    assert "dependencies:" in result.content


async def test_conda_template_includes_warnings_comments():
    context = make_context(
        profile_name="warn-env",
        python_version="3.11",
        packages=[
            ResolvedPackage(name="numpy", version="1.26.4", cuda_variant=None),
            ResolvedPackage(name="torch", version="2.1.2", cuda_variant="cu118"),
        ],
    )
    context.warnings = [
        "This profile mixes conda-managed packages with pip-installed GPU wheels."
    ]
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "# WARNING: This profile mixes conda-managed packages" in result.content


async def test_conda_template_cuda_variant_goes_to_pip_section():
    """Packages with CUDA variant ('+' in spec) must appear under pip: section."""
    context = make_context(
        profile_name="gpu-env",
        python_version="3.11",
        cuda_version="11.8",
        packages=[
            ResolvedPackage(name="torch", version="2.0.0", cuda_variant="cu118"),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "pip:" in result.content
    assert "torch" in result.content


async def test_conda_template_name_field_matches_profile():
    """The 'name:' field must exactly match the profile name."""
    context = make_context(profile_name="pytorch-cuda", python_version="3.11")
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert "name: pytorch-cuda" in result.content


def _extract_channels(rendered: str) -> list[str]:
    """Extract ordered channel list from rendered environment.yml content."""
    lines = rendered.splitlines()
    try:
        i = lines.index("channels:") + 1
    except ValueError:
        return []
    out: list[str] = []
    for line in lines[i:]:
        if not line.startswith("  - "):
            break
        out.append(line.replace("  - ", "", 1).strip())
    return out


async def test_conda_template_cuda_adds_pytorch_nvidia_channels():
    """When cuda_version is set, channels must include pytorch and nvidia in correct order."""
    context = make_context(
        profile_name="cuda-env",
        python_version="3.11",
        cuda_version="12.1",
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert _extract_channels(result.content) == [
        "pytorch",
        "nvidia",
        "conda-forge",
        "defaults",
    ]


async def test_conda_template_rocm_adds_pytorch_channel():
    """When rocm_version is set, channels must include pytorch but not nvidia."""
    context = make_context(
        profile_name="rocm-env",
        python_version="3.11",
    )
    context.resolved = context.resolved.__class__(
        python_version=context.resolved.python_version,
        cuda_version=None,
        target_os=context.resolved.target_os,
        rocm_version="5.6",
        packages=context.resolved.packages,
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert _extract_channels(result.content) == ["pytorch", "conda-forge", "defaults"]


async def test_conda_template_cpu_only_no_gpu_channels():
    """Without cuda or rocm, channels must only have conda-forge and defaults."""
    context = make_context(
        profile_name="cpu-env",
        python_version="3.10",
        cuda_version=None,
    )
    renderer = TemplateRenderer()
    result = await renderer.render("environment.yml", context)
    assert _extract_channels(result.content) == ["conda-forge", "defaults"]
