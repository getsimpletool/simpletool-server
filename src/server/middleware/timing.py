"""
Timing middleware for FastAPI
Adds X-Process-Time header to responses showing processing time in milliseconds
"""

import time
from fastapi import FastAPI, Request

class ProcessTimeMiddleware:
    """Middleware to add processing time header to responses"""

    async def __call__(self, request: Request, call_next):
        """Process the request and add timing header to response"""
        # Record start time
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate process time in milliseconds
        process_time = (time.time() - start_time) * 1000

        # Add custom header (rounded to 2 decimal places)
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        return response


def add_timing_middleware(app: FastAPI) -> None:
    """Add the timing middleware to the FastAPI application"""
    app.middleware("http")(ProcessTimeMiddleware())
