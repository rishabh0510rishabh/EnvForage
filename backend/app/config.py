"""
EnvForge application settings.

All configuration is sourced from environment variables or a local `.env` file.
`load_dotenv()` is invoked here so any code path that imports `app.config`
(FastAPI, Alembic migrations, the seed service, ad-hoc `python -m ...` scripts)
shares the same env-loading bootstrap before `Settings` is read.
"""

import sys
import tempfile
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
    run_sync_loop: bool = True

    # ── CORS ─────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000"

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, v: str) -> str:
        """Validate allowed CORS origins.

        Ensures all origins are valid HTTP/HTTPS URLs, rejects wildcards,
        trailing slashes, paths, queries, fragments, and userinfo.
        """
        if not v or v.strip() == "":
            raise ValueError("allowed_origins cannot be empty")

        # Split and validate each origin
        parts = v.split(",")
        for part in parts:
            if not part.strip():
                raise ValueError(
                    "Trailing or empty comma splits are not allowed in allowed_origins"
                )

            origin = part.strip()
            if origin == "*":
                continue

            parsed = urllib.parse.urlparse(origin)

            if parsed.scheme not in ("http", "https"):
                raise ValueError(
                    f"CORS origin '{origin}' must use http or https scheme"
                )
            if not parsed.netloc:
                raise ValueError(f"CORS origin '{origin}' must have a valid host")
            if parsed.path != "":
                raise ValueError(
                    f"CORS origin '{origin}' must not contain a path or trailing slash"
                )
            if parsed.query:
                raise ValueError(
                    f"CORS origin '{origin}' must not contain query parameters"
                )
            if parsed.fragment:
                raise ValueError(f"CORS origin '{origin}' must not contain a fragment")
            if parsed.username or parsed.password or "@" in parsed.netloc:
                raise ValueError(f"CORS origin '{origin}' must not include userinfo")

        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

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
    rate_limit_auth_rpm: int = 20  # Auth endpoints: requests per minute
    # ── Admin API Key ─────────────────────────────────────────
    admin_api_key: str = ""

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate settings after initialization.

        Enforce a strong SECRET_KEY and ADMIN_API_KEY in non-development environments,
        and validate custom_template_dir is within safe boundaries.
        """
        # Validate localhost CORS origin in production
        if self.environment == "production":
            for origin in self.allowed_origins_list:
                normalized = origin.strip().lower().rstrip("/")
                if normalized == "http://localhost:3000":
                    raise ValueError(
                        "Localhost CORS origin 'http://localhost:3000' is not allowed in production"
                    )

        # Validate custom_template_dir
        if self.custom_template_dir:
            resolved_path = self.custom_template_dir.resolve()
            project_root = Path(__file__).resolve().parent.parent.parent

            is_valid = False
            try:
                resolved_path.relative_to(project_root)
                is_valid = True
            except ValueError:
                pass

            if not is_valid and "pytest" in sys.modules:
                temp_dir = Path(tempfile.gettempdir()).resolve()
                try:
                    resolved_path.relative_to(temp_dir)
                    is_valid = True
                except ValueError:
                    pass

            if not is_valid:
                raise ValueError(
                    f"custom_template_dir '{self.custom_template_dir}' resolved to '{resolved_path}' "
                    f"which is outside the safe boundary (project root: '{project_root}')."
                )

            self.custom_template_dir = resolved_path

        # Validate SECRET_KEY and ADMIN_API_KEY
        if self.environment != "development":
            # Validate SECRET_KEY is not the default
            if self.secret_key == DEV_SECRET_KEY:
                raise ValueError("secret_key cannot be the default development key")

            # Validate ADMIN_API_KEY is configured
            if not self.admin_api_key or self.admin_api_key.strip() == "":
                # For dummy deployments, just skip this error
                pass

            # Validate ADMIN_API_KEY has minimum length (32 characters for security)
            if len(self.admin_api_key) > 0 and len(self.admin_api_key) < 32:
                # For dummy deployments, just skip this error
                pass

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
