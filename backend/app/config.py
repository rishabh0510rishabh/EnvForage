from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Helper function for CORS
def parse_cors(v: Any) -> list[str]:
    if isinstance(v, str):
        return [o.strip() for o in v.split(",")]
    return v

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = "dev-secret-key-change-in-production"
    app_name: str = "EnvForage"
    # Database & Redis
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/envforge"
    redis_url: str | None = None
    # CORS (Fix for your test failure)
    allowed_origins: Annotated[list[str], BeforeValidator(parse_cors)] = ["http://localhost:8080"]
    # Admin & Security
    admin_api_key: str = ""
    # AI & Limits
    rate_limit_auth_rpm: int = 100
    custom_template_dir: Path | None = None

    @field_validator("database_command_timeout_seconds", mode="before")
    @classmethod
    def validate_db_timeout(cls, v: Any) -> float:
        val = float(v or 30.0)
        if val <= 0 or val > 300:
            raise ValueError("Timeout must be between 0 and 300")
        return val

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment != "development":
            if self.secret_key == "dev-secret-key-change-in-production":
                raise ValueError("secret_key cannot be the default development key")
        return self