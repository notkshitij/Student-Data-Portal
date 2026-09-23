"""
UserSession model.

Stores server-side sessions for authenticated users. This ensures that
sessions can be invalidated remotely and limits session hijacking impact
by allowing strict expiration controls.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class UserSession(Base):
    """A server-side session for an authenticated user."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    # The actual token stored in the client cookie
    session_token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<UserSession(user_id={self.user_id!r}, "
            f"expires_at={self.expires_at!r})>"
        )
