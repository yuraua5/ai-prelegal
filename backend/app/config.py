"""Application settings, loaded from environment variables.

Only minimal settings live here for now (step-03). The Anthropic API key is
read but not yet used; step-12 will fail-fast on it when AI is enabled.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded once at startup. Reads from process env or a `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Where the FastAPI app binds inside the container (matches Dockerfile).
    prelegal_host: str = Field(default="0.0.0.0")
    prelegal_port: int = Field(default=8000)

    # Empty by default; step-12 will require this to be set.
    anthropic_api_key: str = Field(default="")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings accessor — re-used across requests."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
