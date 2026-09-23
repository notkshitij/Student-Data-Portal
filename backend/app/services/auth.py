"""
Authentication service.

Handles password hashing, token generation, and FastAPI dependencies
for protected routes.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User, UserRole
from app.models.user_session import UserSession

ph = PasswordHasher()

SESSION_COOKIE_NAME = "session_token"
# 7 days in seconds
SESSION_EXPIRATION_SECONDS = 7 * 24 * 60 * 60


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(password)


def verify_password(hash: str, password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return ph.verify(hash, password)
    except VerifyMismatchError:
        return False


def generate_session_token() -> str:
    """Generate a cryptographically secure random session token."""
    return secrets.token_urlsafe(64)


def create_user_session(db: Session, user_id: str) -> UserSession:
    """Create a new session for a user in the database."""
    token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=SESSION_EXPIRATION_SECONDS
    )
    
    session = UserSession(
        session_token=token,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()
    return session


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency to get the currently authenticated user from the session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    # Find the session in the database
    user_session = (
        db.query(UserSession)
        .filter(UserSession.session_token == token)
        .first()
    )
    
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    
    # Check expiration
    if user_session.expires_at < datetime.now(timezone.utc):
        # Clean up the expired session
        db.delete(user_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    
    # Check if user is active
    if not user_session.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )
        
    return user_session.user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency to ensure the current user is an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


def get_current_student(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency to ensure the current user is a student."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
