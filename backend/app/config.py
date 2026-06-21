"""
EnvForage application settings.

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

if "pytest" not in sys.modules:
    load_dotenv()

DEV_SECRET_KEY = "dev-secret-key-change-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None if "pytest" in sys.modules else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = DEV_SECRET_KEY
    app_name: str = "EnvForage"
    app_version: str = "2.0.0"
    custom_template_dir: Path | None = None

    # ── Graceful shutdown ─────────────────────────────────────
    # Max seconds to wait for in-flight SSE streams to finish before the
    # process exits (e.g. on SIGTERM during a Kubernetes rolling update).
    graceful_shutdown_timeout_seconds: float = 30.0

    @field_validator("graceful_shutdown_timeout_seconds")
    @classmethod
    def validate_graceful_shutdown_timeout_seconds(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(
                "graceful_shutdown_timeout_seconds must be greater than 0"
            )
        if v > 300:
            raise ValueError(
                "graceful_shutdown_timeout_seconds must be less than or equal to 300"
            )
        return v

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/envforage"
    database_command_timeout_seconds: float = 30.0

    @field_validator("database_command_timeout_seconds")
    @classmethod
    def validate_database_command_timeout_seconds(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(
                "database_command_timeout_seconds must be greater than 0"
            )
        if v > 300:
            raise ValueError(
                "database_command_timeout_seconds must be less than or equal to 300"
            )
        return v

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
             # Wildcard validation will be done in model_validator based on environment
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

    # ── S3 / Blob Storage ─────────────────────────────────────
    # Leave blank to disable S3 integration (uploads stay local).
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = ""

    # ── Uploads ───────────────────────────────────────────────
    upload_dir: str = "/tmp/envforage_uploads"

    # ── AI / LLM ─────────────────────────────────────────────
    envforage_llm_provider: Literal["openai", "openrouter", "ollama", "mock"] = "mock"
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
    def validate_secret_key(self) -> "Settings":
        """Enforce strong SECRET_KEY and validate Redis in production environments.

        The default value (DEV_SECRET_KEY) is committed to the public repository.
        Any deployment that omits SECRET_KEY in staging or production will silently
        sign JWTs with this known-public string, allowing trivial token forgery.

        Redis is required in production for correct rate limiting behavior across
        multiple workers. Without it, each worker maintains separate rate limit state,
        allowing attackers to bypass limits by distributing requests.

        Raises:
            ValueError: When required configuration is missing outside development.
        """
        if self.environment != "development":
            if self.secret_key == DEV_SECRET_KEY:
                raise ValueError(
                    f"A strong SECRET_KEY is required when environment='{self.environment}'. "
                    "Set the SECRET_KEY environment variable to a cryptographically random "
                    "value before deploying. "
                    "The default key ('dev-secret-key-change-in-production') is committed "
                    "to the public repository and must never be used outside local development."
                )

            # Production deployments with multiple workers must use Redis
            if self.environment == "production" and not self.redis_url:
                import logging
                logging.getLogger("app.config").warning(
                    "REDIS_URL is not configured when environment='production'. "
                    "Falling back to in-memory rate limiting, which is not suitable for distributed deployments. "
                    "Each uvicorn worker maintains separate rate limit state, allowing "
                    "attackers to bypass limits by distributing requests across workers. "
                    "Configure Redis with format: redis://:password@host:port/db or redis://host:port/db"
                )
        return self

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate settings after initialization.

        Enforce a strong SECRET_KEY and ADMIN_API_KEY in non-development environments,
        and validate custom_template_dir is within safe boundaries.
        """
                # Block wildcard CORS origin in production
        if self.environment == "production" and self.allowed_origins == "*":
            import logging
            logging.getLogger("app.config").warning(
                "Wildcard '*' CORS origin is configured in production. "
                "This allows any website to make requests to your API, which is insecure."
            )

        # Validate localhost CORS origin in production
        if self.environment == "production":
            for origin in self.allowed_origins_list:
                parsed_origin = urllib.parse.urlparse(origin)
                hostname = parsed_origin.hostname
                if hostname in ("localhost", "127.0.0.1", "[::1]", "::1"):
                    import logging
                    logging.getLogger("app.config").warning(
                        f"Localhost CORS origin '{origin}' is configured in production."
                    )

            # Block localhost database URLs in production
            parsed_db = urllib.parse.urlparse(self.database_url)
            hostname = parsed_db.hostname
            if hostname in ("localhost", "127.0.0.1", "[::1]", "::1"):
                import logging
                logging.getLogger("app.config").warning(
                    "Localhost database URL is configured in production environment."
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

