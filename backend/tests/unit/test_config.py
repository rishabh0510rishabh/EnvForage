"""
Unit tests for application configuration validation and security guidelines.

Verifies CORS origin formatting rules and environment-specific constraints.
"""

import pytest
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, Settings


def test_valid_cors_origins():
    """Ensure properly formatted origins pass validation seamlessly."""
    config = Settings(
        environment="development",
        allowed_origins="http://localhost:3000,https://example.com,https://app.example.com"
    )
    assert config.allowed_origins_list == [
        "http://localhost:3000",
        "https://example.com",
        "https://app.example.com"
    ]


def test_invalid_cors_origin_formats():
    """Verify that malformed origins raise Pydantic validation errors."""
    with pytest.raises(ValidationError, match=r"Wildcard '\*' not allowed in allowed_origins"):
        Settings(allowed_origins="*")

    with pytest.raises(ValidationError, match="Must not have a trailing slash"):
        Settings(allowed_origins="https://example.com/")

    with pytest.raises(ValidationError, match="Must not contain a path component"):
        Settings(allowed_origins="https://example.com/dashboard")

    with pytest.raises(ValidationError, match="Must not contain query"):
        Settings(allowed_origins="https://example.com?query=true")

    with pytest.raises(ValidationError, match="Must not contain fragment"):
        Settings(allowed_origins="https://example.com#section")

    with pytest.raises(ValidationError, match="Must not include userinfo"):
        Settings(allowed_origins="https://user:pass@example.com")

    with pytest.raises(ValidationError, match="Must start with 'http://' or 'https://'"):
        Settings(allowed_origins="frontend.example.com")

    with pytest.raises(ValidationError, match="Empty or trailing comma origins are not allowed"):
        Settings(allowed_origins="https://example.com,,https://api.com")


def test_production_rejects_dev_secret():
    """Verify that the model validator rejects the default development secret in production."""
    with pytest.raises(ValidationError, match="secret_key cannot be the default development key"):
        Settings(
            environment="production",
            secret_key=DEV_SECRET_KEY,
            allowed_origins="https://myproductionapp.com",
        )


def test_production_cors_safeguards():
    """Verify production safeguards block default localhost configurations."""
    with pytest.raises(ValidationError, match="Security Risk: ALLOWED_ORIGINS cannot default to"):
        Settings(
            environment="production",
            allowed_origins=" http://localhost:3000 ",
            secret_key="prod-safe-key-123"
        )

    prod_config = Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="prod-safe-key-123"
    )
    assert prod_config.allowed_origins_list == ["https://myproductionapp.com"]
    