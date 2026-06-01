"""
EnvForge application settings.

All configuration is sourced from environment variables or a local `.env` file.
`load_dotenv()` is invoked here so any code path that imports `app.config`
(FastAPI, Alembic migrations, the seed service, ad-hoc `python -m ...` scripts)
shares the same env-loading bootstrap before `Settings` is read.
"""

import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

DEV_SECRET_KEY = "dev-secret-key-change-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = DEV_SECRET_KEY
    app_name: str = "EnvForage"
    app_version: str = "1.0.0"
    custom_template_dir: Path | None = None

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/envforge"

    # ── Redis ─────────────────────────────────────────────────
    # If set, the rate limiter will use Redis instead of in-memory storage.
    # Required in production for multi-worker correctness.
    # Format: redis://:password@host:port/db  or  redis://host:port/db
    redis_url: str | None = None
    resolver_cache_ttl_seconds: int = 86400

    # ── CORS ─────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Split and normalize comma-separated allowed origins into a list of strings."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @field_validator("allowed_origins", mode="after")
    @classmethod
    def validate_origins(cls, v: str) -> str:
        """Validate format parameters of individual CORS entries inside allowed_origins."""
        origins = [o.strip() for o in v.split(",")]
        for origin in origins:
            if not origin:
                raise ValueError("Empty or trailing comma origins are not allowed.")
            if origin == "*":
                raise ValueError("Wildcard '*' is not allowed in ALLOWED_ORIGINS.")

            parsed = urllib.parse.urlparse(origin)
            if not parsed.scheme or parsed.scheme not in ("http", "https"):
                raise ValueError(f"Invalid origin '{origin}': Must start with 'http://' or 'https://'.")
            if not parsed.netloc:
                raise ValueError(f"Invalid origin '{origin}': Missing host/domain.")
            if parsed.query or parsed.fragment:
                raise ValueError(f"Invalid origin '{origin}': Query/fragment components are not allowed.")
            if parsed.username or parsed.password:
                raise ValueError(f"Invalid origin '{origin}': Userinfo components are not allowed.")
            if parsed.path and parsed.path != "/":
                raise ValueError(f"Invalid origin '{origin}': Must not contain a path component ('{parsed.path}').")
            if origin.endswith("/"):
                raise ValueError(f"Invalid origin '{origin}': Must not have a trailing slash.")
        return v

    # ── AI / LLM ─────────────────────────────────────────────
    envforge_llm_provider: Literal["openai", "openrouter", "ollama", "mock"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o"
    ollama_base_url: str = "http://llm:11434"
    ollama_model: str = "llama3"
    ai_max_tokens: int = 2048
    ai_temperature: float = 0.3

    # ── Pagination ────────────────────────────────────────────
    default_page_size: int = 20
    max_page_size: int = 100

    # ── Rate Limiting ─────────────────────────────────────────
    rate_limit_ai_rpm: int = 10  # AI troubleshoot: requests per minute
    rate_limit_repair_rpm: int = 20  # Repair endpoint: requests per minute
    rate_limit_general_rpm: int = 60  # General API: requests per minute

    # ── Admin API Key ─────────────────────────────────────────
    admin_api_key: str = ""

    @model_validator(mode="after")
    def validate_production_safeguards(self) -> "Settings":
        """Validate security baselines when running in a production ecosystem."""
        if self.environment == "production":
            # 1. Existing secret key check
            if self.secret_key == DEV_SECRET_KEY:
                raise ValueError("Production environment requires a strong SECRET_KEY.")

            # 2. Check for unintended fallback to localhost default in production (normalized check)
            if "http://localhost:3000" in self.allowed_origins_list:
                raise ValueError(
                    "Security Risk: ALLOWED_ORIGINS cannot default to 'http://localhost:3000' in production. "
                    "Please explicitly set your production ALLOWED_ORIGINS environment variable."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()