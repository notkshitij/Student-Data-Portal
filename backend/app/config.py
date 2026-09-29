"""
Application configuration loaded from environment variables.

Uses python-dotenv to load a .env file if present.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory (one level above app/).
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


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
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://sdvp_user:sdvp_dev_password@localhost:5432/sdvp",
        )
    )
    google_client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))
    google_redirect_uri: str = field(default_factory=lambda: os.getenv("GOOGLE_REDIRECT_URI", "postmessage"))
    admin_emails: list[str] = field(
        default_factory=lambda: [
            e.strip().lower()
            for e in os.getenv("ADMIN_EMAIL", "piyushagarwalnew@gmail.com").split(",")
            if e.strip()
        ]
    )
    
    # Environment and security settings
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    enable_api_docs: bool = field(default_factory=lambda: os.getenv("ENABLE_API_DOCS", "true").lower() == "true")
    allowed_hosts: list[str] = field(default_factory=lambda: [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()])
    upload_dir: Path = field(default_factory=lambda: Path(os.getenv("UPLOAD_DIR", str(Path(__file__).resolve().parent.parent / "data" / "uploads"))))

settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
