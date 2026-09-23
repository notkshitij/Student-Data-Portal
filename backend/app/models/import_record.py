"""
Import model.

Tracks each Excel file import: who uploaded it, which campaign it
belongs to, the original filename, row count, and processing status.
"""

import enum
import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ImportStatus(str, enum.Enum):
    """Processing status of an Excel import."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Import(Base):
    """Metadata for an Excel file import."""

    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(512), nullable=False,
    )
    row_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    status: Mapped[ImportStatus] = mapped_column(
        String(20), nullable=False, default=ImportStatus.PENDING, index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        String(2048), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="imports")
    uploaded_by_user = relationship("User", back_populates="imports")

    def __repr__(self) -> str:
        return (
            f"<Import(campaign_id={self.campaign_id!r}, "
            f"filename={self.original_filename!r}, status={self.status!r})>"
        )
