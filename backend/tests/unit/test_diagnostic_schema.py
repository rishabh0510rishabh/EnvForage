"""Unit tests for max_length constraints on diagnostic report string fields.

Regression coverage for issue #439: several string fields in the diagnostic
report schema previously had no upper length bound, allowing oversized values
to pass validation and then fail (or silently truncate) at the PostgreSQL
persistence layer. Each field below should reject values that exceed its
configured ``max_length`` while accepting boundary-length values.
"""

import pytest
from pydantic import ValidationError

from app.schemas.diagnostic import CPUInfo, GPUInfo, OSInfo, PythonInfo

# (model, field, valid kwargs, max_length) for each bounded string field.
# Bounds for fields copied into denormalized columns on `diagnostic_reports` are pinned to the DB column widths so values cannot pass API validation and then overflow on write:
# GPUInfo.name -> gpu_name VARCHAR(128),
# GPUInfo.driver_version -> driver_version VARCHAR(32),
# PythonInfo.version -> python_version VARCHAR(8).
# The remaining fields are only stored in the unbounded report_data JSONB column.
BOUNDED_FIELDS = [
    (OSInfo, "name", {"version": "22.04", "architecture": "x86_64"}, 128),
    (OSInfo, "version", {"name": "Ubuntu", "architecture": "x86_64"}, 32),
    (OSInfo, "architecture", {"name": "Ubuntu", "version": "22.04"}, 32),
    (CPUInfo, "brand", {"cores": 8, "threads": 16}, 256),
    (GPUInfo, "name", {}, 128),
    (GPUInfo, "driver_version", {"name": "NVIDIA RTX 4060"}, 32),
    (PythonInfo, "version", {"path": "/usr/bin/python3"}, 8),
    (PythonInfo, "path", {"version": "3.11.4"}, 512),
]


@pytest.mark.parametrize(
    "model, field, other_fields, max_length",
    BOUNDED_FIELDS,
    ids=[f"{m.__name__}.{f}" for m, f, _, _ in BOUNDED_FIELDS],
)
def test_string_field_accepts_max_length_value(model, field, other_fields, max_length):
    """A value exactly at ``max_length`` is accepted."""
    instance = model(**{field: "a" * max_length}, **other_fields)

    assert getattr(instance, field) == "a" * max_length


@pytest.mark.parametrize(
    "model, field, other_fields, max_length",
    BOUNDED_FIELDS,
    ids=[f"{m.__name__}.{f}" for m, f, _, _ in BOUNDED_FIELDS],
)
def test_string_field_rejects_oversized_value(model, field, other_fields, max_length):
    """A value one character over ``max_length`` is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        model(**{field: "a" * (max_length + 1)}, **other_fields)

    errors = exc_info.value.errors()
    assert any(
        err["loc"] == (field,) and err["type"] == "string_too_long" for err in errors
    )


def test_optional_driver_version_still_accepts_none():
    """Bounding driver_version must not break its optional (None) default."""
    gpu = GPUInfo(name="NVIDIA RTX 4060 Laptop GPU")

    assert gpu.driver_version is None


def test_typical_realistic_report_values_are_accepted():
    """Representative real-world values comfortably fit within the new bounds."""
    os_info = OSInfo(name="Ubuntu 22.04.4 LTS", version="22.04", architecture="x86_64")
    cpu = CPUInfo(
        brand="AMD Ryzen 7 7840HS w/ Radeon 780M Graphics", cores=8, threads=16
    )
    gpu = GPUInfo(name="NVIDIA GeForce RTX 4060 Laptop GPU", driver_version="555.85")
    python = PythonInfo(version="3.11.4", path="/usr/local/bin/python3.11")

    assert os_info.name.startswith("Ubuntu")
    assert cpu.brand.startswith("AMD")
    assert gpu.driver_version == "555.85"
    assert python.version == "3.11.4"
