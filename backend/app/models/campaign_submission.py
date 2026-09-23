"""
CampaignSubmission model.

Records the event of a student submitting their data for a campaign.
This creates an audit trail of when submissions occurred.
"""

import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class CampaignSubmission(Base):
    """A record of a student submitting their campaign data."""

    __tablename__ = "campaign_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    campaign_student = relationship(
        "CampaignStudent", back_populates="submissions",
    )

    def __repr__(self) -> str:
        return (
            f"<CampaignSubmission(campaign_student_id="
            f"{self.campaign_student_id!r}, submitted_at={self.submitted_at!r})>"
        )
