"""
Admin Router Package

This package contains all the admin-related router functionality.
"""
from fastapi import APIRouter, Request
from mcpo_simple_server.services.mcpserver import McpServerService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],  # Tag for OpenAPI documentation
)

def get_mcpserver_service(request: Request) -> McpServerService:
    return request.app.state.mcpserver_service

# Import modules to register routes
from . import tools  # noqa: F401, E402
from . import user  # noqa: F401, E402

# Export the reload_tools_router function for use in other modules
from .tools import _reload_tools_router  # noqa: F401, E402
