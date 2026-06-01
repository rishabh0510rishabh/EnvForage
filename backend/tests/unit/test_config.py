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
    # Wildcard rejection at base parsing
    with pytest.raises(ValidationError, match="Wildcard '\\*' is not allowed"):
        Settings(allowed_origins="*")

    # Trailing slash
    with pytest.raises(ValidationError, match="Must not have a trailing slash"):
        Settings(allowed_origins="https://example.com/")

    # URL path component
    with pytest.raises(ValidationError, match="Must not contain a path component"):
        Settings(allowed_origins="https://example.com/dashboard")

    # URL query parameters
    with pytest.raises(ValidationError, match="Query/fragment components are not allowed"):
        Settings(allowed_origins="https://example.com?query=true")

    # URL userinfo components
    with pytest.raises(ValidationError, match="Userinfo components are not allowed"):
        Settings(allowed_origins="https://user:pass@example.com")

    # Missing scheme
    with pytest.raises(ValidationError, match="Must start with 'http://' or 'https://'"):
        Settings(allowed_origins="frontend.example.com")

    # Empty/trailing comma element
    with pytest.raises(ValidationError, match="Empty or trailing comma origins are not allowed"):
        Settings(allowed_origins="https://example.com,,https://api.com")


def test_production_cors_safeguards():
    """Verify production safeguards block default secret configurations and default origins."""
    # Block default dev secret key in Production
    with pytest.raises(ValidationError, match="Production environment requires a strong SECRET_KEY"):
        Settings(
            environment="production",
            allowed_origins="https://myproductionapp.com",
            secret_key=DEV_SECRET_KEY,
        )

    # Block localhost default fallback in Production (even with whitespace formatting)
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS cannot default to 'http://localhost:3000'"):
        Settings(
            environment="production",
            allowed_origins=" http://localhost:3000 ",
            secret_key="prod-safe-key-123"
        )

    # Valid Production settings should pass cleanly
    prod_config = Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="prod-safe-key-123"
    )
    assert prod_config.allowed_origins_list == ["https://myproductionapp.com"]
    
