"""
Authentication routes.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import GenericResponse, GoogleLoginRequest, UserMeResponse
from app.models.user import UserRole
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=GenericResponse)
def login(
    login_data: GoogleLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate a user using Google OAuth authorization code."""
    try:
        id_info = auth.verify_google_oauth2_code(login_data.code)
    except ValueError:
        # Avoid detailed error messages to prevent enumeration/attacks
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your Google account could not be used to access this portal."
        )
        
    email = id_info.get("email", "").lower()
    subject_id = id_info.get("sub")
    
    # Check if user exists by email or subject_id
    user = db.query(User).filter(
        (User.email == email) | (User.google_subject_id == subject_id)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your Google account could not be used to access this portal."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your Google account could not be used to access this portal."
        )
        
    # Update Google subject ID if it was empty (e.g. initial setup)
    if not user.google_subject_id:
        user.google_subject_id = subject_id
        
    # Create session
    session = auth.create_user_session(db, str(user.id))
    
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


@router.get("/me", response_model=UserMeResponse)
def get_current_user_info(
    current_user: User = Depends(auth.get_current_user),
):
    """Return the currently authenticated user based on the session cookie."""
    return current_user


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
        secure=request.url.scheme == "https",
    )
    
    return GenericResponse(message="Successfully logged out")
