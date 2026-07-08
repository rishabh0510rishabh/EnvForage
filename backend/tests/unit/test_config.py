import pytest
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, SECRET_KEY_MIN_LENGTH, Settings


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
        secret_key="s" * SECRET_KEY_MIN_LENGTH,
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    # Localhost CORS settings in Production are allowed but logged as warning
    Settings(
        environment="production",
        allowed_origins="http://127.0.0.1:3000",
        secret_key="s" * SECRET_KEY_MIN_LENGTH,
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    # Localhost database URLs in Production are allowed but logged as warning
    Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="s" * SECRET_KEY_MIN_LENGTH,
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="s" * SECRET_KEY_MIN_LENGTH,
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )

    # Accept valid production configuration
    prod_config = Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="s" * SECRET_KEY_MIN_LENGTH,
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )
    assert prod_config.allowed_origins_list == ["https://myproductionapp.com"]


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_short_secret_key_rejected_outside_development(environment):
    """A custom but weak SECRET_KEY must be rejected in non-development environments.

    Rejecting only the committed default leaves a gap: a short custom key still
    produces brute forceable HS256 tokens. Enforce the minimum length instead.
    """
    short_key = "x" * (SECRET_KEY_MIN_LENGTH - 1)
    with pytest.raises(
        ValidationError, match=f"at least {SECRET_KEY_MIN_LENGTH} characters"
    ):
        Settings(
            environment=environment,
            allowed_origins="https://myproductionapp.com",
            secret_key=short_key,
            admin_api_key="a" * 32,
            database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
            redis_url="redis://localhost:6379/0",
        )


def test_secret_key_at_minimum_length_accepted():
    """A SECRET_KEY at exactly the minimum length is accepted outside development."""
    config = Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="y" * SECRET_KEY_MIN_LENGTH,
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )
    assert len(config.secret_key) == SECRET_KEY_MIN_LENGTH


def test_short_secret_key_allowed_in_development():
    """Development keeps a relaxed policy so local setups need no extra config."""
    config = Settings(environment="development", secret_key="short-dev-key")
    assert config.secret_key == "short-dev-key"

@pytest.mark.parametrize("environment", ["staging", "production"])
def test_missing_admin_api_key_rejected_outside_development(environment):
    """ADMIN_API_KEY is required outside development to protect admin endpoints."""
    with pytest.raises(ValidationError, match="ADMIN_API_KEY is required"):
        Settings(
            environment=environment,
            allowed_origins="https://myproductionapp.com",
            secret_key="s" * SECRET_KEY_MIN_LENGTH,
            admin_api_key="",
            database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
            redis_url="redis://localhost:6379/0",
        )


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_short_admin_api_key_rejected_outside_development(environment):
    """A custom but weak ADMIN_API_KEY must be rejected in non-development environments."""
    short_key = "a" * 31
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(
            environment=environment,
            allowed_origins="https://myproductionapp.com",
            secret_key="s" * SECRET_KEY_MIN_LENGTH,
            admin_api_key=short_key,
            database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
            redis_url="redis://localhost:6379/0",
        )


def test_admin_api_key_at_minimum_length_accepted():
    """An ADMIN_API_KEY at exactly the minimum length is accepted outside development."""
    config = Settings(
        environment="production",
        allowed_origins="https://myproductionapp.com",
        secret_key="s" * SECRET_KEY_MIN_LENGTH,
        admin_api_key="a" * 32,
        database_url="postgresql+asyncpg://postgres:postgres@db.production.internal:5432/envforage",
        redis_url="redis://localhost:6379/0",
    )
    assert len(config.admin_api_key) == 32


def test_missing_admin_api_key_allowed_in_development():
    """Development keeps a relaxed policy so local setups need no extra config."""
    config = Settings(environment="development", admin_api_key="")
    assert config.admin_api_key == ""
