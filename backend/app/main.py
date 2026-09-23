"""
Student Data Verification Portal — Backend Application

FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import health

app = FastAPI(
    title="Student Data Verification Portal",
    description="Backend API for the Student Data Verification Portal",
    version="0.1.0",
)

# CORS configuration for local development.
# In production, replace with the actual frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
