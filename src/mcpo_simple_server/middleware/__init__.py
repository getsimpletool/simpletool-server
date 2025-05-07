"""
Middleware package for server
"""

from fastapi import FastAPI

from .timing import add_timing_middleware
from .cors import add_cors_middleware
from .logging import add_logging_middleware
from .security import add_security_headers_middleware
from .error_handler import add_error_handler_middleware


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application

    Args:
        app: FastAPI application instance
    """
    # Add middleware in order (outermost to innermost)
    add_error_handler_middleware(app)  # Should be first to catch errors from other middleware
    add_timing_middleware(app)
    add_logging_middleware(app)
    add_security_headers_middleware(app)
    add_cors_middleware(app)  # CORS should be last (innermost) for best performance
