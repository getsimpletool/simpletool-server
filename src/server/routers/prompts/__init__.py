"""
Public Prompts Router

This module provides API endpoints for accessing public prompts.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/prompts", tags=["Prompts"])

# Import handlers to register routes
from . import handlers  # noqa: F401, E402
