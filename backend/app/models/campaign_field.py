"""
CampaignField model.

Represents a single column/field within a campaign. Fields are dynamic —
they are created from the Excel column headers at import time, not
hard-coded into the application.
"""

import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class CampaignField(Base):
    """A dynamic field (Excel column) belonging to a campaign."""

    __tablename__ = "campaign_fields"
    __table_args__ = (
        UniqueConstraint("campaign_id", "field_name", name="uq_campaign_field_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    field_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="fields")
    imported_values = relationship(
        "ImportedFieldValue", back_populates="campaign_field", lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<CampaignField(campaign_id={self.campaign_id!r}, "
            f"field_name={self.field_name!r})>"
        )
