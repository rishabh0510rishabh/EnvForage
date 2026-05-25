"""Unit tests for validate_profiles.py CLI utility."""
import tempfile
from pathlib import Path
from typing import Any

import yaml
from click.testing import CliRunner

from scripts.validate_profiles import main, validate_profile_file


def _valid_profile() -> dict[str, Any]:
    return {
        "slug": "pytorch-cuda",
        "name": "PyTorch CUDA",
        "description": "Full PyTorch GPU environment with CUDA support.",
        "tags": ["deep-learning", "gpu", "pytorch"],
        "os_support": ["LINUX", "WSL"],
        "cuda_required": True,
        "python_versions": ["3.10", "3.11"],
        "cuda_versions": ["11.8", "12.1"],
        "status": "ACTIVE",
        "packages": [
            {
                "name": "torch",
                "version_spec": "2.1.2",
                "cuda_variant": "cu118",
                "install_order": 0,
            },
            {
                "name": "numpy",
                "version_spec": "1.26.4",
                "install_order": 1,
            }
        ],
    }


def test_validate_valid_single_profile():
    """Verify that a valid single profile YAML file passes validation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(_valid_profile(), tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is True
        assert not errors
    finally:
        tmp_path.unlink()


def test_validate_valid_multi_profile():
    """Verify that a valid multi-profile list YAML file passes validation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump({"profiles": [_valid_profile(), _valid_profile()]}, tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is True
        assert not errors
    finally:
        tmp_path.unlink()


def test_validate_invalid_yaml_syntax():
    """Verify that malformed YAML syntax is caught."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        tmp.write("profiles:\n  - slug: pytorch-cuda\n  name: unmatched-indentation")
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is False
        assert any("YAML Syntax Error" in err for err in errors)
    finally:
        tmp_path.unlink()


def test_validate_pydantic_errors():
    """Verify that missing or invalid fields fail schema validation."""
    data = _valid_profile()
    del data["slug"]  # Missing required field
    data["os_support"] = ["INVALID_OS"]  # Invalid OS string

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is False
        assert len(errors) >= 2
        assert any("slug" in err and "Field required" in err for err in errors)
        assert any("os_support" in err and "Invalid os_support" in err for err in errors)
    finally:
        tmp_path.unlink()


def test_logical_error_cuda_required_without_versions():
    """Logical check: cuda_required=True but cuda_versions is empty."""
    data = _valid_profile()
    data["cuda_required"] = True
    data["cuda_versions"] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is False
        assert any("cuda_required is True, but cuda_versions is empty" in err for err in errors)
    finally:
        tmp_path.unlink()


def test_logical_error_duplicate_packages():
    """Logical check: duplicate package names within the same profile."""
    data = _valid_profile()
    data["packages"].append({
        "name": "torch",  # Duplicate package name
        "version_spec": "2.2.0",
        "install_order": 2
    })

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is False
        assert any("Duplicate package names found: ['torch']" in err for err in errors)
    finally:
        tmp_path.unlink()


def test_logical_error_duplicate_install_orders():
    """Logical check: duplicate install_order values."""
    data = _valid_profile()
    data["packages"][1]["install_order"] = 0  # Duplicate install_order

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is False
        assert any("Duplicate install_order values found: [0]" in err for err in errors)
    finally:
        tmp_path.unlink()


def test_logical_error_cuda_variant_mismatch():
    """Logical check: package cuda_variant (e.g. cu124) doesn't match any cuda_versions (e.g. 11.8, 12.1)."""
    data = _valid_profile()
    data["packages"][0]["cuda_variant"] = "cu124"  # 12.4 not in cuda_versions

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, errors = validate_profile_file(tmp_path)
        assert is_valid is False
        assert any("Package 'torch' specifies cuda_variant 'cu124' (mapped to '12.4'), which is not compatible" in err for err in errors)
    finally:
        tmp_path.unlink()


def test_cli_runner_success():
    """Verify that a valid profile file returns exit code 0."""
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(_valid_profile(), tmp)
        tmp_path = Path(tmp.name)

    try:
        result = runner.invoke(main, [str(tmp_path)])
        assert result.exit_code == 0
        assert "PASSED" in result.output
        assert "Validation succeeded" in result.output
    finally:
        tmp_path.unlink()


def test_cli_runner_failure():
    """Verify that an invalid profile file returns exit code 1."""
    runner = CliRunner()
    data = _valid_profile()
    data["cuda_required"] = True
    data["cuda_versions"] = []  # Fail logical check

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = runner.invoke(main, [str(tmp_path)])
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Validation failed" in result.output
    finally:
        tmp_path.unlink()


def test_cli_runner_skipped_non_profile_yaml():
    """Verify that non-profile files are skipped and validation succeeds."""
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump({"some_key": "some_value"}, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = runner.invoke(main, [str(tmp_path)])
        assert result.exit_code == 0
        assert "SKIPPED (not a profile)" in result.output
        assert "Validation succeeded" in result.output
    finally:
        tmp_path.unlink()
