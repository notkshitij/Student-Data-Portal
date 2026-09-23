"""
Authentication schemas.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class GenericResponse(BaseModel):
    """A generic response message."""

    message: str
