"""Unit tests for Settings validation in app/config.py."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_development_allows_default_secret_key():
    """Development mode accepts the committed default key so local setup is not blocked."""
    config = Settings(environment="development")
    assert config.secret_key == "dev-secret-key-change-in-production"


def test_development_allows_short_secret_key():
    """Development mode does not enforce the 32 character minimum."""
    config = Settings(environment="development", secret_key="short")
    assert config.secret_key == "short"


def test_default_secret_key_rejected_in_staging():
    """The hardcoded default SECRET_KEY must be rejected in staging."""
    with pytest.raises(
        ValidationError,
        match="A strong SECRET_KEY is required",
    ):
        Settings(
            environment="staging",
            secret_key="dev-secret-key-change-in-production",
        )


def test_default_secret_key_rejected_in_production():
    """The hardcoded default SECRET_KEY must be rejected in production."""
    with pytest.raises(
        ValidationError,
        match="A strong SECRET_KEY is required",
    ):
        Settings(
            environment="production",
            secret_key="dev-secret-key-change-in-production",
        )


def test_weak_secret_key_rejected_in_staging():
    """A custom but short SECRET_KEY must be rejected in staging.

    Rejecting only the committed default still allows a deployer to ship a
    short, low-entropy secret that an attacker can brute force to forge JWTs.
    """
    with pytest.raises(
        ValidationError,
        match="shorter than the 32 character minimum",
    ):
        Settings(environment="staging", secret_key="short-key")


def test_weak_secret_key_rejected_in_production():
    """A short SECRET_KEY must be rejected in production."""
    with pytest.raises(
        ValidationError,
        match="shorter than the 32 character minimum",
    ):
        Settings(environment="production", secret_key="too-short")


def test_strong_secret_key_accepted_in_staging():
    """A SECRET_KEY of at least 32 characters is accepted in staging."""
    config = Settings(
        environment="staging",
        secret_key="a-strong-staging-secret-key-0123456789",
    )
    assert config.environment == "staging"


def test_strong_secret_key_accepted_in_production():
    """A SECRET_KEY of at least 32 characters is accepted in production."""
    config = Settings(
        environment="production",
        secret_key="a-strong-production-secret-key-0123456789",
    )
    assert config.environment == "production"
