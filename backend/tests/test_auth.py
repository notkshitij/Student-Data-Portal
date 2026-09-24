import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.models.user_session import UserSession
from app.services import auth

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_successful_login(client, student_user, db_session, mock_google_auth):
    response = client.post(
        "/api/auth/login",
        json={"code": "valid_code_student"},
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


def test_invalid_google_code(client, mock_google_auth):
    response = client.post(
        "/api/auth/login",
        json={"code": "invalid_or_expired_code"},
    )
    
    assert response.status_code == 401
    assert "could not be used" in response.json()["detail"]
    assert auth.SESSION_COOKIE_NAME not in response.cookies


def test_invalid_domain(client, mock_google_auth):
    # Tests that the verify function throws ValueError for bad domain, 
    # and the route returns 401
    response = client.post(
        "/api/auth/login",
        json={"code": "invalid_domain"},
    )
    
    assert response.status_code == 401


def test_unverified_email(client, mock_google_auth):
    response = client.post(
        "/api/auth/login",
        json={"code": "unverified_email"},
    )
    
    assert response.status_code == 401


def test_nonexistent_account(client, mock_google_auth):
    # Suppose a student logs in with valid poornima email, but they are not in the DB
    # We should reject them because only imported students or admins can log in
    def _mock_verify_new(code: str):
        return {
            "sub": "new_sub_999",
            "email": "not_in_db@poornima.edu.in",
            "email_verified": True,
            "hd": "poornima.edu.in"
        }
    client.app.dependency_overrides.clear() # clear test dummy routers if any conflicts
    import _pytest.monkeypatch
    m = _pytest.monkeypatch.MonkeyPatch()
    m.setattr(auth, "verify_google_oauth2_code", _mock_verify_new)

    response = client.post(
        "/api/auth/login",
        json={"code": "some_code"},
    )
    
    assert response.status_code == 401


def test_session_authentication_and_logout(client, student_user, db_session, mock_google_auth):
    # 1. Login
    login_resp = client.post(
        "/api/auth/login",
        json={"code": "valid_code_student"},
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


def test_current_user_me(client, student_user, db_session, mock_google_auth):
    # 1. Access unauthenticated -> 401
    resp1 = client.get("/api/auth/me")
    assert resp1.status_code == 401

    # 2. Login
    login_resp = client.post(
        "/api/auth/login",
        json={"code": "valid_code_student"},
    )
    assert login_resp.status_code == 200

    # 3. Access authenticated -> 200 with user data
    resp2 = client.get("/api/auth/me")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["id"] == str(student_user.id)
    assert data["email"] == student_user.email
    assert data["role"] == (student_user.role.value if hasattr(student_user.role, 'value') else student_user.role)
    assert data["is_active"] is True
    # Ensure sensitive data is not returned
    assert "password_hash" not in data
    assert "google_subject_id" not in data

    # 4. Logout -> 200
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200

    # 5. Access unauthenticated -> 401
    resp3 = client.get("/api/auth/me")
    assert resp3.status_code == 401


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


def test_role_protection(client, student_user, admin_user, mock_google_auth):
    # Login as student
    client.post(
        "/api/auth/login",
        json={"code": "valid_code_student"},
    )
    
    # Student accessing student route -> OK
    assert client.get("/test/protected-student").status_code == 200
    # Student accessing admin route -> FORBIDDEN
    assert client.get("/test/protected-admin").status_code == 403
    
    # Login as admin
    client.post(
        "/api/auth/login",
        json={"code": "valid_code_admin"},
    )
    
    # Admin accessing admin route -> OK
    assert client.get("/test/protected-admin").status_code == 200
    # Admin accessing student route -> FORBIDDEN
    assert client.get("/test/protected-student").status_code == 403


def test_verify_google_oauth2_code_sends_correct_payload(monkeypatch):
    """
    Ensures that the token exchange uses the correct redirect_uri (postmessage).
    """
    from app.services.auth import verify_google_oauth2_code
    
    # We will capture the data sent to requests.post
    captured_data = {}
    
    class MockResponse:
        def __init__(self):
            self.ok = True
        def json(self):
            return {"id_token": "mocked_jwt"}
            
    def mock_post(url, data):
        captured_data.update(data)
        return MockResponse()
        
    def mock_verify_id_token(*args, **kwargs):
        return {
            "email_verified": True,
            "email": "student@poornima.edu.in",
            "hd": "poornima.edu.in",
            "sub": "mock_sub"
        }
        
    monkeypatch.setattr("app.services.auth.requests.post", mock_post)
    monkeypatch.setattr("app.services.auth.id_token.verify_oauth2_token", mock_verify_id_token)
    
    verify_google_oauth2_code("some_code")
    
    from app.config import settings
    assert settings.google_redirect_uri == "postmessage"
    assert captured_data.get("redirect_uri") == "postmessage"
    assert captured_data.get("grant_type") == "authorization_code"
    assert captured_data.get("code") == "some_code"

def test_admin_email_bypass(monkeypatch, client, db_session):
    """
    Ensures that the configured ADMIN_EMAIL bypasses the poornima domain requirement.
    """
    from app.config import settings
    # Ensure settings.admin_email is what we expect
    assert settings.admin_email == "piyushagarwalnew@gmail.com"
    
    # 1. Ensure the admin user exists in DB
    admin = db_session.query(User).filter(User.email == "piyushagarwalnew@gmail.com").first()
    if not admin:
        admin = User(
            email="piyushagarwalnew@gmail.com",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
    
    # 2. Mock google auth to return this admin email without poornima domain
    def _mock_verify_admin(code: str):
        return {
            "sub": "new_sub_admin",
            "email": "piyushagarwalnew@gmail.com",
            "email_verified": True,
            "hd": None  # No domain for gmail
        }
    monkeypatch.setattr(auth, "verify_google_oauth2_code", _mock_verify_admin)
    
    response = client.post(
        "/api/auth/login",
        json={"code": "admin_code"},
    )
    
    assert response.status_code == 200
    assert auth.SESSION_COOKIE_NAME in response.cookies
    
    # Check that google_subject_id was associated
    db_session.refresh(admin)
    assert admin.google_subject_id == "new_sub_admin"

def test_arbitrary_gmail_rejected(monkeypatch, client):
    """
    Ensures that an arbitrary gmail account (not the ADMIN_EMAIL and not poornima) is rejected.
    """
    from app.config import settings
    assert settings.admin_email == "piyushagarwalnew@gmail.com"
    
    def _mock_verify_arbitrary(code: str):
        return {
            "sub": "new_sub_hacker",
            "email": "hacker@gmail.com",
            "email_verified": True,
            "hd": None
        }
    monkeypatch.setattr(auth, "verify_google_oauth2_code", _mock_verify_arbitrary)
    
    response = client.post(
        "/api/auth/login",
        json={"code": "hacker_code"},
    )
    
    assert response.status_code == 401
