"""
Student Data Verification Portal — Backend Application

FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import health, auth, admin, student

app = FastAPI(
    title="Student Data Verification Portal",
    description="Backend API for the Student Data Verification Portal",
    version="0.1.0",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.middleware import SecurityHeadersMiddleware

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Trusted Host (if configured)
if "*" not in settings.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(student.router, prefix="/api")
