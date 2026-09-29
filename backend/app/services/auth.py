"""
Authentication service.

Handles password hashing, token generation, and FastAPI dependencies
for protected routes.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models.user import User, UserRole
from app.models.user_session import UserSession

SESSION_COOKIE_NAME = "session_token"
# 7 days in seconds
SESSION_EXPIRATION_SECONDS = 7 * 24 * 60 * 60

def verify_google_oauth2_code(code: str) -> dict:
    """Exchanges an auth code for tokens and verifies the ID token."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code"
    }
    resp = requests.post(token_url, data=data)
    if not resp.ok:
        raise ValueError("Failed to exchange code with Google")
    
    tokens = resp.json()
    id_token_jwt = tokens.get("id_token")
    if not id_token_jwt:
        raise ValueError("No ID token returned from Google")

    request = google_requests.Request()
    try:
        id_info = id_token.verify_oauth2_token(
            id_token_jwt, request, settings.google_client_id
        )
    except ValueError as e:
        raise ValueError(f"Invalid ID token: {str(e)}")
        
    # Check email verified and domain
    if not id_info.get("email_verified"):
        raise ValueError("Google email is not verified")
        
    email = id_info.get("email", "").lower()
    domain = id_info.get("hd")
    allowed_domains = {"poornima.edu.in", "poornima.org"}
    
    # Allow explicitly configured admin email(s), regardless of domain
    if email in settings.admin_emails:
        return id_info
    
    # Sometimes 'hd' might be missing if it's a regular gmail account, 
    # but we strictly require these domains for students.
    if domain not in allowed_domains and not any(email.endswith(f"@{d}") for d in allowed_domains):
        raise ValueError(f"Domain not allowed: {domain or email.split('@')[-1]}")
        
    return id_info


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
