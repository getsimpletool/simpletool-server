"""
CORS middleware for FastAPI
Handles Cross-Origin Resource Sharing (CORS) headers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors_middleware(
    app: FastAPI,
    allow_origins=None,
    allow_credentials=True,
    allow_methods=None,
    allow_headers=None,
) -> None:
    """
    Add CORS middleware to the FastAPI application
    
    Args:
        app: FastAPI application instance
        allow_origins: List of origins that should be permitted to make cross-origin requests
        allow_credentials: Indicate that cookies should be supported for cross-origin requests
        allow_methods: List of HTTP methods that should be allowed for cross-origin requests
        allow_headers: List of HTTP request headers that should be supported for cross-origin requests
    """
    if allow_origins is None:
        allow_origins = ["*"]
    
    if allow_methods is None:
        allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    
    if allow_headers is None:
        allow_headers = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )
