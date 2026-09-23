"""
SystemMetadata model.

A minimal key-value table used to verify that SQLAlchemy and Alembic
are correctly configured. Future phases will add application-specific
models; this table can also store simple application-level settings.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SystemMetadata(Base):
    """Key-value store for application metadata and configuration."""

    __tablename__ = "system_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SystemMetadata(key={self.key!r}, value={self.value!r})>"
