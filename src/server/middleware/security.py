"""
Security middleware for FastAPI
Adds security headers to responses
"""

from fastapi import FastAPI, Request


class SecurityHeadersMiddleware:
    """Middleware to add security headers to responses"""

    async def __call__(self, request: Request, call_next):
        """Process the request and add security headers to response"""
        # Process the request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Check if request is for Swagger UI or OpenAPI schema
        if request.url.path in ['/docs', '/redoc', '/openapi.json'] or request.url.path.startswith('/docs/'):
            # Disable CSP for documentation pages
            pass
        else:
            # Apply strict CSP for other routes
            response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response


def add_security_headers_middleware(app: FastAPI) -> None:
    """Add the security headers middleware to the FastAPI application"""
    app.middleware("http")(SecurityHeadersMiddleware())
