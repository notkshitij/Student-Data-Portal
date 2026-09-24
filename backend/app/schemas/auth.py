"""
Authentication schemas.
"""

from pydantic import BaseModel, EmailStr, Field


class GoogleLoginRequest(BaseModel):
    """Payload for Google OAuth 2.0 authorization code login."""
    code: str


class GenericResponse(BaseModel):
    """A generic response message."""

    message: str

import uuid
from app.models.user import UserRole
from pydantic import ConfigDict

class UserMeResponse(BaseModel):
    """Payload returning the currently authenticated user details."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
