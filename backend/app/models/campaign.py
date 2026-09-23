"""
Campaign model.

A campaign represents a single data-collection effort. An administrator
creates a campaign, imports student data from an Excel file, and publishes
it so that students can fill in their missing information.
"""

import enum
import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class CampaignStatus(str, enum.Enum):
    """Lifecycle states for a campaign."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class Campaign(Base):
    """A data-collection campaign."""

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        String(20), nullable=False, default=CampaignStatus.DRAFT, index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    # Relationships
    created_by_user = relationship(
        "User", back_populates="created_campaigns",
    )
    students = relationship(
        "CampaignStudent", back_populates="campaign", lazy="selectin",
    )
    fields = relationship(
        "CampaignField", back_populates="campaign", lazy="selectin",
        order_by="CampaignField.field_order",
    )
    imports = relationship(
        "Import", back_populates="campaign", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Campaign(name={self.name!r}, status={self.status!r})>"
