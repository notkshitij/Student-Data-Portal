"""
Authentication routes.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import GenericResponse, LoginRequest
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=GenericResponse)
def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate a user and set a session cookie."""
    # Generic error message to prevent email enumeration
    login_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )
    
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise login_error
        
    if not user.password_hash:
        raise login_error
        
    if not auth.verify_password(user.password_hash, login_data.password):
        raise login_error
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )
        
    # Create session
    session = auth.create_user_session(db, user.id)
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    # Set secure cookie
    response.set_cookie(
        key=auth.SESSION_COOKIE_NAME,
        value=session.session_token,
        max_age=auth.SESSION_EXPIRATION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    
    return GenericResponse(message="Successfully logged in")


@router.post("/logout", response_model=GenericResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Log out a user by deleting their session and clearing the cookie."""
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    
    if token:
        # Delete session from database
        db.query(UserSession).filter(UserSession.session_token == token).delete()
        db.commit()
        
    # Always clear the cookie
    response.delete_cookie(
        key=auth.SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )
    
    return GenericResponse(message="Successfully logged out")
