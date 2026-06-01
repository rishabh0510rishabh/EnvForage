import pytest
from pydantic import ValidationError
from app.config import Settings, DEV_SECRET_KEY

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
    # Trailing slash
    with pytest.raises(ValidationError, match="Must not have a trailing slash"):
        Settings(allowed_origins="https://example.com/")

    # URL path component
    with pytest.raises(ValidationError, match="Must not contain a path component"):
        Settings(allowed_origins="https://example.com/dashboard")

    # Missing scheme
    with pytest.raises(ValidationError, match="Must start with 'http://' or 'https://'"):
        Settings(allowed_origins="frontend.example.com")

    # Empty/trailing comma element
    with pytest.raises(ValidationError, match="Empty or trailing comma origins are not allowed"):
        Settings(allowed_origins="https://example.com,,https://api.com")

def test_production_cors_safeguards():
    """Verify production safeguards block wildcards or default fallback settings."""
    # Block Wildcard in Production
    with pytest.raises(ValidationError, match="Wildcard '\\*' CORS origin is strictly forbidden"):
        Settings(environment="production", allowed_origins="*", secret_key="prod-safe-key-123")

    # Block localhost default fallback in Production
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS cannot default to 'http://localhost:3000'"):
        Settings(environment="production", secret_key="prod-safe-key-123")

    # Valid Production settings should pass cleanly
    prod_config = Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="prod-safe-key-123"
    )
    assert prod_config.allowed_origins_list == ["https://myproductionapp.com"]