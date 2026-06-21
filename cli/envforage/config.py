import sys
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

console = Console()


class CliSettings(BaseSettings):
    api_url: str = Field(default="http://localhost:8000", description="EnvForage backend API URL")
    timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    auto_update: bool = Field(default=False, description="Enable automatic prompts/checks for updates")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_config() -> CliSettings:
    """Load configuration, gracefully handling validation errors with a clean message."""
    try:
        return CliSettings()
    except ValidationError as e:
        console.print(
            "[bold red]Configuration Error:[/bold red] The configuration file contains invalid data."
        )
        for error in e.errors():
            loc = ".".join(map(str, error["loc"]))
            console.print(f"  - [cyan]{loc}[/cyan]: {error['msg']}")
        sys.exit(1)
