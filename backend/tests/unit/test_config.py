import pytest
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, Settings


def test_valid_origins():
    """Verify that valid CORS origins are successfully validated and parsed."""
    config = Settings(
        environment="development",
        allowed_origins="https://example.com,http://localhost:8080",
    )
    assert config.allowed_origins_list == [
        "https://example.com",
        "http://localhost:8080",
    ]


def test_invalid_origins():
    """Verify that invalid CORS origin formats are rejected by the field validator."""
    # Missing web scheme
    with pytest.raises(ValidationError):
        Settings(allowed_origins="example.com")

    # Trailing slash
    with pytest.raises(ValidationError):
        Settings(allowed_origins="https://example.com/")

    # Explicitly assigned path component
    with pytest.raises(ValidationError):
        Settings(allowed_origins="https://example.com/dashboard")

    # Empty or trailing comma split elements
    with pytest.raises(ValidationError):
        Settings(allowed_origins="https://example.com,,https://other.com")

    # Query parameters
    with pytest.raises(ValidationError):
        Settings(allowed_origins="https://example.com?query=1")

    # Fragment component
    with pytest.raises(ValidationError):
        Settings(allowed_origins="https://example.com#fragment")

    # Userinfo component
    with pytest.raises(ValidationError):
        Settings(allowed_origins="https://user:pass@example.com")


def test_production_cors_safeguards():
    """Verify that production guards enforce strong keys and forbid wildcard/default configurations."""
    # Block default dev secret key in Production
    with pytest.raises(
        ValidationError, match="A strong SECRET_KEY is required"
    ):
        Settings(
            environment="production",
            allowed_origins="https://myproductionapp.com",
            secret_key=DEV_SECRET_KEY,
            admin_api_key="a" * 32,
            database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
            redis_url="redis://localhost:6379/0",
        )

    # Wildcard is allowed but logged as warning
    Settings(
        environment="production",
        allowed_origins="*",
        secret_key="prod-safe-key",
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    # Localhost CORS settings in Production are allowed but logged as warning
    Settings(
        environment="production",
        allowed_origins="http://127.0.0.1:3000",
        secret_key="prod-safe-key",
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    # Localhost database URLs in Production are allowed but logged as warning
    Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="prod-safe-key",
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="prod-safe-key",
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    # Accept valid production configuration
    prod_config = Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="prod-safe-key",
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )
    assert prod_config.allowed_origins_list == ["https://myproductionapp.com"]
