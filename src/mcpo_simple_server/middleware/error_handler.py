"""
Error handling middleware for FastAPI
Provides consistent error responses
"""

import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Configure logger
logger = logging.getLogger("api.errors")


class ErrorHandlerMiddleware:
    """Middleware to handle errors and provide consistent responses"""

    async def __call__(self, request: Request, call_next):
        """Process the request and handle any errors"""
        try:
            return await call_next(request)
        except Exception as e:
            # Log the error with traceback
            logger.error(
                f"Unhandled exception: {str(e)}\n"
                f"Request path: {request.url.path}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            # Return a JSON response with error details
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": str(e) if request.app.debug else "An unexpected error occurred",
                },
            )


def add_error_handler_middleware(app: FastAPI) -> None:
    """Add the error handler middleware to the FastAPI application"""
    app.middleware("http")(ErrorHandlerMiddleware())
