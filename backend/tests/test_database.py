"""
Tests for the database foundation.

These tests verify:
1. FastAPI can connect to PostgreSQL.
2. The health endpoint reports database status correctly.
3. The database dependency provides a working SQLAlchemy session.
4. Alembic migrations can be applied.
5. The initial table exists after migrations.
6. The health endpoint handles database unavailability.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.session import Base, SessionLocal, get_db
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def test_db_engine():
    """Create a SQLAlchemy engine connected to the test database."""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_db_engine):
    """Provide a transactional database session that rolls back after each test."""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client():
    """FastAPI test client with default database dependency."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client_no_db():
    """FastAPI test client with a broken database dependency to simulate DB failure."""

    def _broken_db():
        """Yield a mock session that raises on execute(), simulating DB failure."""
        from unittest.mock import MagicMock

        mock_session = MagicMock(spec=Session)
        mock_session.execute.side_effect = Exception("Simulated database failure")
        try:
            yield mock_session
        finally:
            pass

    app.dependency_overrides[get_db] = _broken_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()



# ---------------------------------------------------------------------------
# Test 1: FastAPI can connect to PostgreSQL
# ---------------------------------------------------------------------------


def test_database_connection(test_db_engine):
    """Verify that the SQLAlchemy engine can execute a simple query."""
    with test_db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


# ---------------------------------------------------------------------------
# Test 2: Health endpoint reports database as connected
# ---------------------------------------------------------------------------


def test_health_endpoint_database_connected(client):
    """Health endpoint should return status=ok and database=connected."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


# ---------------------------------------------------------------------------
# Test 3: Database dependency provides a working session
# ---------------------------------------------------------------------------


def test_get_db_provides_working_session():
    """The get_db dependency should yield a working SQLAlchemy session."""
    gen = get_db()
    session = next(gen)
    try:
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        # Trigger cleanup
        try:
            next(gen)
        except StopIteration:
            pass


# ---------------------------------------------------------------------------
# Test 4: Alembic migration can be applied to a fresh database
# ---------------------------------------------------------------------------


def test_alembic_upgrade_head():
    """Verify that 'alembic upgrade head' runs without errors.

    This uses a subprocess to replicate the real migration workflow.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"alembic upgrade head failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Test 5: The initial table exists after alembic upgrade head
# ---------------------------------------------------------------------------


def test_system_metadata_table_exists(test_db_engine):
    """After migrations, the system_metadata table should exist."""
    inspector = inspect(test_db_engine)
    tables = inspector.get_table_names()
    assert "system_metadata" in tables, (
        f"system_metadata table not found. Existing tables: {tables}"
    )


def test_system_metadata_table_columns(test_db_engine):
    """The system_metadata table should have the expected columns."""
    inspector = inspect(test_db_engine)
    columns = {col["name"] for col in inspector.get_columns("system_metadata")}
    expected = {"id", "key", "value", "created_at", "updated_at"}
    assert expected.issubset(columns), (
        f"Missing columns: {expected - columns}. Found: {columns}"
    )


# ---------------------------------------------------------------------------
# Test 6: Health endpoint handles database unavailability
# ---------------------------------------------------------------------------


def test_health_endpoint_database_unavailable(client_no_db):
    """When the database is unreachable, the health endpoint should return 503."""
    response = client_no_db.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "disconnected"
