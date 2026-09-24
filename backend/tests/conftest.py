"""
Shared pytest fixtures for the backend.
"""

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.main import app
from app.models.user import User, UserRole
from app.services import auth

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(settings.database_url, pool_pre_ping=True)
    yield eng
    eng.dispose()

@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    
    # Dummy protected routes for testing dependencies
    test_router = APIRouter(tags=["test_dummy"])
    
    @test_router.get("/test/protected-user")
    def protected_user(user: User = Depends(auth.get_current_user)):
        return {"id": str(user.id)}
        
    @test_router.get("/test/protected-admin")
    def protected_admin(user: User = Depends(auth.get_current_admin)):
        return {"id": str(user.id)}
        
    @test_router.get("/test/protected-student")
    def protected_student(user: User = Depends(auth.get_current_student)):
        return {"id": str(user.id)}
        
    app.include_router(test_router)
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()
    
    # Remove the dummy router to avoid conflicts across test files if not needed, 
    # but include_router modifies the global app. It's fine for testing.

@pytest.fixture
def mock_google_auth(monkeypatch):
    """Mocks the Google OAuth verification function."""
    def _mock_verify(code: str):
        if code == "valid_code_student":
            return {
                "sub": "student_google_sub_123",
                "email": "student_auth@poornima.edu.in",
                "email_verified": True,
                "hd": "poornima.edu.in"
            }
        elif code == "valid_code_admin":
            return {
                "sub": "admin_google_sub_456",
                "email": "admin_auth@poornima.org",
                "email_verified": True,
                "hd": "poornima.org"
            }
        elif code == "invalid_domain":
            return {
                "sub": "invalid_domain_123",
                "email": "hacker@gmail.com",
                "email_verified": True,
                "hd": None
            }
        elif code == "unverified_email":
            return {
                "sub": "unverified_123",
                "email": "unverified@poornima.edu.in",
                "email_verified": False,
                "hd": "poornima.edu.in"
            }
        else:
            raise ValueError("Invalid code or Google error")
            
    monkeypatch.setattr(auth, "verify_google_oauth2_code", _mock_verify)

@pytest.fixture()
def student_user(db_session):
    user = User(
        email="student_auth@poornima.edu.in",
        google_subject_id="student_google_sub_123",
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture()
def admin_user(db_session):
    user = User(
        email="admin_auth@poornima.org",
        google_subject_id="admin_google_sub_456",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    return user
