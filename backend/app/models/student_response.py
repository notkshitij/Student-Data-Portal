"""
StudentResponse model.

Stores the value submitted by a student for a field that requires input.
The response is kept separate from the imported value so that the
original import data is never overwritten.
"""

import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class StudentResponse(Base):
    """A student's submitted value for a single field."""

    __tablename__ = "student_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    imported_field_value_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imported_field_values.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    response_value: Mapped[str] = mapped_column(
        String(2048), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    # Relationships
    imported_field_value = relationship(
        "ImportedFieldValue", back_populates="student_response",
    )

    def __repr__(self) -> str:
        return (
            f"<StudentResponse(imported_field_value_id="
            f"{self.imported_field_value_id!r})>"
        )
