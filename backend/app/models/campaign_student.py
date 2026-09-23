"""
CampaignStudent model.

Junction table that tracks which students participate in which campaigns
and their submission status within each campaign.
"""

import enum
import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class SubmissionStatus(str, enum.Enum):
    """Whether the student has submitted their data for a campaign."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"


class CampaignStudent(Base):
    """Association between a student and a campaign."""

    __tablename__ = "campaign_students"
    __table_args__ = (
        UniqueConstraint("campaign_id", "student_id", name="uq_campaign_student"),
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
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        String(20), nullable=False, default=SubmissionStatus.PENDING, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="students")
    student = relationship("User", back_populates="campaign_memberships")
    imported_field_values = relationship(
        "ImportedFieldValue", back_populates="campaign_student", lazy="selectin",
    )
    submissions = relationship(
        "CampaignSubmission", back_populates="campaign_student", lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<CampaignStudent(campaign_id={self.campaign_id!r}, "
            f"student_id={self.student_id!r}, status={self.status!r})>"
        )
