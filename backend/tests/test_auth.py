import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.user_session import UserSession
from app.services import auth

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_password_hashing():
    password = "supersecretpassword"
    hashed = auth.hash_password(password)
    
    assert hashed != password
    assert auth.verify_password(hashed, password) is True
    assert auth.verify_password(hashed, "wrongpassword") is False


def test_successful_login(client, student_user, db_session):
    response = client.post(
        "/api/auth/login",
        json={"email": "student_auth@test.com", "password": "studentpass"},
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged in"
    
    # Check that cookie was set
    assert auth.SESSION_COOKIE_NAME in response.cookies
    token = response.cookies[auth.SESSION_COOKIE_NAME]
    
    # Verify session in DB
    session = db_session.query(UserSession).filter(UserSession.session_token == token).first()
    assert session is not None
    assert session.user_id == student_user.id
    
    # Verify last_login_at updated
    db_session.refresh(student_user)
    assert student_user.last_login_at is not None


def test_incorrect_password(client, student_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "student_auth@test.com", "password": "wrongpass"},
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
    assert auth.SESSION_COOKIE_NAME not in response.cookies


def test_nonexistent_account(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "anypassword"},
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_session_authentication_and_logout(client, student_user, db_session):
    # 1. Login
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "student_auth@test.com", "password": "studentpass"},
    )
    assert login_resp.status_code == 200
    token = login_resp.cookies[auth.SESSION_COOKIE_NAME]
    
    # 2. Access protected route
    protected_resp = client.get("/test/protected-user")
    assert protected_resp.status_code == 200
    assert protected_resp.json()["id"] == str(student_user.id)
    
    # 3. Logout
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    
    # Cookie should be cleared (TestClient handles this, but let's check DB)
    session = db_session.query(UserSession).filter(UserSession.session_token == token).first()
    assert session is None
    
    # 4. Access protected route again (should fail)
    protected_resp_after = client.get("/test/protected-user")
    assert protected_resp_after.status_code == 401


def test_expired_session(client, student_user, db_session):
    # Create an expired session directly in DB
    token = auth.generate_session_token()
    session = UserSession(
        session_token=token,
        user_id=student_user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(session)
    db_session.commit()
    
    # Force set cookie in TestClient
    client.cookies.set(auth.SESSION_COOKIE_NAME, token)
    
    response = client.get("/test/protected-user")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired session"
    
    # Verify session was deleted during cleanup
    deleted_session = db_session.query(UserSession).filter(UserSession.session_token == token).first()
    assert deleted_session is None


def test_role_protection(client, student_user, admin_user):
    # Login as student
    client.post(
        "/api/auth/login",
        json={"email": "student_auth@test.com", "password": "studentpass"},
    )
    
    # Student accessing student route -> OK
    assert client.get("/test/protected-student").status_code == 200
    # Student accessing admin route -> FORBIDDEN
    assert client.get("/test/protected-admin").status_code == 403
    
    # Login as admin
    client.post(
        "/api/auth/login",
        json={"email": "admin_auth@test.com", "password": "adminpass"},
    )
    
    # Admin accessing admin route -> OK
    assert client.get("/test/protected-admin").status_code == 200
    # Admin accessing student route -> FORBIDDEN
    assert client.get("/test/protected-student").status_code == 403

