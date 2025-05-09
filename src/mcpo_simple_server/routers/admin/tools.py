"""
Admin Tools Router

This module provides functionality for managing dynamic tool endpoints.
"""
import asyncio
from fastapi import Depends, Request, status
from mcpo_simple_server.auth.models.auth import UserInDB
from mcpo_simple_server.auth import dependencies
from mcpo_simple_server.services.mcpserver import McpServerService
from mcpo_simple_server.routers.admin import router, get_mcpserver_service
from loguru import logger


# Common helper function for dynamic tools router reload
async def _reload_tools_router(app, server_service):
    """
    Reload all dynamic tool endpoints without restarting the application.

    This helper function:
    1. Creates a new ToolsRouter instance
    2. Removes old tool routes
    3. Initializes and adds the new router
    4. Rebuilds the OpenAPI schema

    Args:
        app: The FastAPI application instance
        server_service: McpServerService instance to initialize the router with
    """
    # Remove all existing /tool/ routes from FastAPI - proper way
    routes_to_keep = []
    for route in app.routes:
        if not hasattr(route, "path") or not route.path.startswith("/tool/"):
            routes_to_keep.append(route)

    # Use API methods to properly rebuild routes
    app.router.routes = routes_to_keep

    # Create a new tools router instance
    import mcpo_simple_server.routers.tools as tools_module
    from mcpo_simple_server.routers.tools import ToolsRouter

    # Replace the global tools_router with a new instance
    tools_module.tools_router = ToolsRouter()

    # Initialize the new router with current tools
    await tools_module.tools_router.initialize(server_service)

    # Include the new router in the app
    app.include_router(tools_module.tools_router.router)

    # Force OpenAPI schema to be rebuilt
    app.openapi_schema = None
    _ = app.openapi()

    logger.info("Dynamic tool endpoints reloaded")


@router.post("/tools/reload", status_code=status.HTTP_200_OK)
async def reload_tools(
    request: Request,
    _: UserInDB = Depends(dependencies.get_current_admin_user),
    server_service: McpServerService = Depends(get_mcpserver_service),
):
    """
    Reload all dynamic tool endpoints without restarting the application.

    This will create a new tools router instance, remove the old router, and re-include the new one.
    This ensures all dynamic endpoints and OpenAPI schema are properly updated.

    Returns:
        Dict containing status and message of the reload operation.
    """
    await _reload_tools_router(request.app, server_service)

    return {"status": "success", "message": "Tool endpoints reloaded with fresh router instance"}
