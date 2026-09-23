"""
AuditLog model.

Records significant actions within the application for accountability
and debugging. Uses JSON for flexible detail storage since audit
entries are append-only and don't need relational querying on their
internal structure.
"""

import uuid

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AuditLog(Base):
    """Append-only audit trail for significant application events."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    entity_id: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(action={self.action!r}, "
            f"entity_type={self.entity_type!r}, "
            f"entity_id={self.entity_id!r})>"
        )
