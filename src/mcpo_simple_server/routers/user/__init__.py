"""
User router module for handling user-related endpoints.
This module organizes the user router into separate handler files for better maintainability.
"""
import os
from fastapi import APIRouter


# Define what should be exported from this module
__all__ = ["router", "ADMIN_DEFAULT_PASSWORD"]

# Create the main router
router = APIRouter(
    prefix="/user",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)

# Get default admin password from environment variable with fallback to 'admin'
ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin")

# Import handler modules to register routes with FastAPI
# These imports are needed to register the routes with the router
# Must be imported after router is defined to avoid circular imports
from . import auth_handlers  # noqa: F401, E402
from . import api_key_handlers  # noqa: F401, E402
from . import env_handlers  # noqa: F401, E402
from . import server_handlers  # noqa: F401, E402
from . import prompt_handlers  # noqa: F401, E402
