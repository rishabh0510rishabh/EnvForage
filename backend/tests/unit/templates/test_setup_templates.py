import pytest

from app.compatibility.models import ResolvedEnvironment, ResolvedPackage
from app.templates.engine import TemplateRenderer
from app.templates.models import TemplateContext


def make_context(
    profile_name="pytorch-env",
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
        profile_id="test-profile",
        profile_name=profile_name,
        resolved=resolved,
    )


@pytest.mark.asyncio
async def test_setup_linux_cuda_with_torch_packages():
    """Verify setup.sh renders both TORCH_INDEX and PyPI blocks when cuda_variant packages exist."""
    context = make_context(
        profile_name="PyTorch CUDA",
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        packages=[
            ResolvedPackage(name="torch", version="2.1.2", cuda_variant="cu118"),
            ResolvedPackage(name="numpy", version="1.26.4", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("setup.sh", context)

    assert 'TORCH_INDEX="https://download.pytorch.org/whl/cu118"' in result.content
    assert '"torch==2.1.2+cu118"' in result.content
    assert '"numpy==1.26.4"' in result.content
    assert '--index-url "$TORCH_INDEX"' in result.content


@pytest.mark.asyncio
async def test_setup_linux_cuda_without_cuda_variant_packages():
    """Verify setup.sh does NOT render an empty TORCH_INDEX pip install for non-PyTorch CUDA profiles."""
    context = make_context(
        profile_name="TensorFlow GPU",
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        packages=[
            ResolvedPackage(name="tensorflow", version="2.14.0", cuda_variant=None),
            ResolvedPackage(name="numpy", version="1.26.4", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("setup.sh", context)

    # TORCH_INDEX should not be rendered when no packages have cuda_variant
    assert "TORCH_INDEX" not in result.content
    assert '--index-url "$TORCH_INDEX"' not in result.content
    assert '"tensorflow==2.14.0"' in result.content
    assert '"numpy==1.26.4"' in result.content


@pytest.mark.asyncio
async def test_setup_linux_cpu_only():
    """Verify setup.sh renders CPU-only installation cleanly."""
    context = make_context(
        profile_name="OpenCV Beginner",
        python_version="3.11",
        cuda_version=None,
        target_os="LINUX",
        packages=[
            ResolvedPackage(name="opencv-python", version="4.9.0.80", cuda_variant=None),
            ResolvedPackage(name="numpy", version="1.26.4", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("setup.sh", context)

    assert "TORCH_INDEX" not in result.content
    assert '"opencv-python==4.9.0.80"' in result.content
    assert '"numpy==1.26.4"' in result.content


@pytest.mark.asyncio
async def test_setup_windows_python_launcher_check():
    """Verify setup.ps1 separates the py launcher binary from version argument."""
    context = make_context(
        profile_name="Windows Setup",
        python_version="3.11",
        target_os="WIN",
        packages=[
            ResolvedPackage(name="numpy", version="1.26.4", cuda_variant=None),
        ],
    )
    renderer = TemplateRenderer()
    result = await renderer.render("setup.ps1", context)

    assert '& py "-$RequiredPython" --version' in result.content
    assert '& "py -' not in result.content
    assert '& $PythonBin @PythonArgs -m venv $VenvDir' in result.content
