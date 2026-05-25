"""Unit tests for profiles.yaml Pydantic validation schemas."""
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from app.schemas.seed_profile import ProfileSeedSchema, ProfilesYamlSchema

SEEDS_FILE = (
    Path(__file__).resolve().parents[3] / "seeds" / "profiles.yaml"
)


def _valid_profile() -> dict[str, Any]:
    return {
        "slug": "pytorch-cuda",
        "name": "PyTorch CUDA",
        "description": "Test profile",
        "tags": ["gpu"],
        "os_support": ["LINUX", "WSL"],
        "cuda_required": True,
        "python_versions": ["3.10", "3.11"],
        "cuda_versions": ["11.8"],
        "status": "ACTIVE",
        "last_validated": "2024-12-01",
        "packages": [
            {
                "name": "torch",
                "version_spec": "2.1.2",
                "cuda_variant": "cu118",
                "install_order": 0,
            }
        ],
    }


def test_valid_profile_parses():
    profile = ProfileSeedSchema.model_validate(_valid_profile())
    assert profile.slug == "pytorch-cuda"
    assert profile.packages[0].name == "torch"
    assert profile.last_validated == date(2024, 12, 1)


def test_missing_slug_raises():
    data = _valid_profile()
    del data["slug"]
    with pytest.raises(ValidationError):
        ProfileSeedSchema.model_validate(data)


def test_invalid_os_support_raises():
    data = _valid_profile()
    data["os_support"] = ["MAC"]
    with pytest.raises(ValidationError):
        ProfileSeedSchema.model_validate(data)


def test_missing_package_version_spec_raises():
    data = _valid_profile()
    del data["packages"][0]["version_spec"]
    with pytest.raises(ValidationError):
        ProfileSeedSchema.model_validate(data)


def test_invalid_status_raises():
    data = _valid_profile()
    data["status"] = "active"
    with pytest.raises(ValidationError):
        ProfileSeedSchema.model_validate(data)


def test_non_string_description_raises():
    data = _valid_profile()
    data["description"] = ["not", "a", "string"]
    with pytest.raises(ValidationError):
        ProfileSeedSchema.model_validate(data)


def test_profiles_yaml_root_schema():
    root = ProfilesYamlSchema.model_validate(
        {"profiles": [_valid_profile()]}
    )
    assert len(root.profiles) == 1


def test_profiles_yaml_missing_profiles_raises():
    with pytest.raises(ValidationError):
        ProfilesYamlSchema.model_validate({})


def test_shipped_profiles_yaml_validates():
    data = yaml.safe_load(SEEDS_FILE.read_text(encoding="utf-8"))
    root = ProfilesYamlSchema.model_validate(data)
    assert len(root.profiles) >= 6
