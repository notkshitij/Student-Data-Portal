"""
User model.

Supports ADMIN and STUDENT roles. Authentication endpoints will be
implemented in a later phase; this model only defines the schema.
"""

import enum
import uuid

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class UserRole(str, enum.Enum):
    """User roles within the application."""

    ADMIN = "ADMIN"
    STUDENT = "STUDENT"


class User(Base):
    """Application user — either an administrator or a student."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True,
    )
    google_subject_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        String(20), nullable=False, index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Relationships
    campaign_memberships = relationship(
        "CampaignStudent", back_populates="student", lazy="selectin",
    )
    created_campaigns = relationship(
        "Campaign", back_populates="created_by_user", lazy="selectin",
    )
    imports = relationship(
        "Import", back_populates="uploaded_by_user", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(email={self.email!r}, role={self.role!r})>"
