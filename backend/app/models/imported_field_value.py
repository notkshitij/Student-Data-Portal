"""
ImportedFieldValue model.

Stores the original value imported from the Excel spreadsheet for a
specific field of a specific student in a campaign. The `requires_student_input`
flag indicates whether the student must provide this value (the cell
contained `[COLLECT]` in the uploaded Excel file).

This record is immutable after import — student responses are stored
separately in the `student_responses` table.
"""

import uuid

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ImportedFieldValue(Base):
    """The imported value of a field for a student within a campaign."""

    __tablename__ = "imported_field_values"
    __table_args__ = (
        UniqueConstraint(
            "campaign_student_id",
            "campaign_field_id",
            name="uq_imported_value_student_field",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    imported_value: Mapped[str | None] = mapped_column(
        String(2048), nullable=True,
    )
    requires_student_input: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    campaign_student = relationship(
        "CampaignStudent", back_populates="imported_field_values",
    )
    campaign_field = relationship(
        "CampaignField", back_populates="imported_values",
    )
    student_response = relationship(
        "StudentResponse",
        back_populates="imported_field_value",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ImportedFieldValue(student={self.campaign_student_id!r}, "
            f"field={self.campaign_field_id!r}, "
            f"requires_input={self.requires_student_input})>"
        )
