from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP: Needs to allow Google OAuth flows.
        # We might not strictly apply CSP here if the frontend is separate.
        # But if we do, this is an API. APIs usually don't need extensive CSP except default-src 'none'.
        # Assuming this is just the backend API:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        
        # HSTS only in production (we'll check request.url.scheme or let reverse proxy handle it)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
        return response
