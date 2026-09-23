"""
Application configuration loaded from environment variables.
"""

import os
from dataclasses import dataclass, field


def _parse_cors_origins() -> list[str]:
    """Parse comma-separated CORS origins from the environment variable."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    """Application settings populated from environment variables."""

    cors_origins: list[str] = field(default_factory=_parse_cors_origins)
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))


settings = Settings()
