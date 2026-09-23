"""
Health check endpoint.

Reports the status of the FastAPI application and PostgreSQL connectivity.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Return health status including database connectivity.

    Returns HTTP 200 with database: "connected" when PostgreSQL is reachable.
    Returns HTTP 503 with database: "disconnected" when PostgreSQL is unavailable.
    Internal errors are logged but never exposed in the response.
    """
    from fastapi.responses import JSONResponse

    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        logger.exception("Database health check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "disconnected"},
        )
