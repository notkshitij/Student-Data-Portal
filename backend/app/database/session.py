"""
SQLAlchemy database session management.

Provides the engine, session factory, declarative Base, and a FastAPI
dependency that yields a properly scoped database session per request.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a SQLAlchemy session.

    The session is automatically closed after the request completes,
    regardless of whether the request succeeded or raised an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
