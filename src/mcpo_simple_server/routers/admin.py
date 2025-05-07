from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from pydantic import BaseModel
from mcpo_simple_server.auth.models.auth import UserInDB, UserCreate, UserPublic
from mcpo_simple_server.auth import dependencies
from mcpo_simple_server.services.mcpserver import McpServerService
from loguru import logger

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],  # Tag for OpenAPI documentation
)


def get_mcpserver_service(request: Request) -> McpServerService:
    return request.app.state.mcpserver_service


# Server Management Endpoints


@router.post("/mcpserver", status_code=status.HTTP_201_CREATED)
async def add_mcpserver(
    request: Request,
    mcpserver_config: Dict[str, Any] = Body(
        ...,
        description="mcpServer configuration in the same format as config.json",
        example={
            "mcpServers": {
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"
                    },
                    "description": "GitHub MCP Server"
                }
            }
        }
    ),
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user),
    server_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    Add a new mcpServer dynamically at runtime.

    The configuration should match the structure in config.json:
    ```json
    {
      "mcpServers": {
        "time": {
          "command": "uvx",
          "args": [
            "mcp-server-time",
            "--local-timezone=Europe/Warsaw"
          ]
        }
      }
    }
    ```

    Returns:
        Dict containing the result of the operation and server details
    """
    logger.info(f"Admin '{admin_user.username}' attempting to add new server configuration")

    try:
        result = await server_service.add_new_mcpserver_config(mcpserver_config)
        logger.info(f"Server configuration added successfully: {result}")

        # Auto-reload tools router and OpenAPI schema
        await _reload_tools_router(request.app, server_service)

        return result
    except Exception as e:
        logger.error(f"Failed to add server configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add server configuration: {str(e)}"
        ) from e


class McpServersListResponse(BaseModel):
    mcpservers: List[Any]


@router.get("/mcpservers", response_model=McpServersListResponse, status_code=status.HTTP_200_OK, summary="List all MCP servers", description="Returns a list of all configured MCP servers.")
async def list_mcpservers(
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user),
    server_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    List all configured mcpservers and their status.

    Returns:
        Dict containing server configurations and status
    """
    logger.info(f"Admin '{admin_user.username}' requesting server list")

    try:
        mcpservers = await server_service.list_mcpservers()
        total_tools = sum(server.get("toolCount", 0) for server in mcpservers)
        logger.debug(f"Listing {len(mcpservers)} MCP servers with {total_tools} total tools")
        return {"mcpservers": mcpservers}
    except Exception as e:
        logger.error(f"Failed to list servers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list servers: {str(e)}"
        ) from e


@router.delete("/mcpserver/{mcpserver_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_mcpserver(
    request: Request,
    mcpserver_name: str,
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user),
    server_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    Remove an MCP server configuration and stop the server if running.

    Args:
        mcpserver_name: The name of the server to remove

    Returns:
        204 No Content on success
    """
    logger.info(f"Admin '{admin_user.username}' attempting to remove server '{mcpserver_name}'")
    try:
        # The service method handles everything related to server deletion
        result = await server_service.delete_mcpserver(mcpserver_name)

        if result.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", f"Failed to remove server '{mcpserver_name}'")
            )

        # Auto-reload tools router and OpenAPI schema
        await _reload_tools_router(request.app, server_service)

        logger.info(f"Server '{mcpserver_name}' removed successfully")
        return
    except Exception as e:
        logger.error(f"Failed to remove server '{mcpserver_name}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove server '{mcpserver_name}': {str(e)}"
        ) from e


@router.post("/mcpserver/{mcpserver_name}/restart", status_code=status.HTTP_200_OK)
async def restart_mcpserver(
    request: Request,
    mcpserver_name: str,
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user),
    server_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    Restart a specific MCP server.

    Args:
        mcpserver_name: The name of the server to restart

    Returns:
        Dict containing the result of the operation
    """
    logger.info(f"Admin '{admin_user.username}' attempting to restart server '{mcpserver_name}'")

    try:
        result = await server_service.restart_mcpserver(mcpserver_name)

        if result.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", f"Failed to restart server '{mcpserver_name}'")
            )

        # Auto-reload tools router and OpenAPI schema after restart
        await _reload_tools_router(request.app, server_service)

        # Return a clean response without any non-serializable objects
        return {
            "status": "success",
            "server": mcpserver_name,
            "message": result.get("message", f"Server '{mcpserver_name}' restarted successfully"),
            "tool_count": result.get("tool_count", 0)
        }
    except Exception as e:
        logger.error(f"Failed to restart server '{mcpserver_name}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to restart server '{mcpserver_name}': {str(e)}"
        ) from e


@router.post("/mcpservers/restart", status_code=status.HTTP_200_OK)
async def restart_all_mcpservers(
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user),
    server_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    Restart all mcpservers from the configuration file.

    This endpoint will:
    1. Stop all currently running servers
    2. Reload the configuration from the config file
    3. Start servers based on the updated configuration

    This is useful when you've made changes to the config file and want to apply them
    without restarting the entire application.

    Returns:
        Dict containing the result of the operation
    """
    logger.info(f"Admin '{admin_user.username}' attempting to restart all servers from configuration file")

    try:
        result = await server_service.restart_all_mcpservers()
        logger.info("All servers restarted successfully from configuration file")
        return result
    except Exception as e:
        logger.error(f"Failed to restart servers from configuration file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart servers: {str(e)}"
        ) from e


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
    import routers.tools as tools_module
    from routers.tools import ToolsRouter

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


# User Management Endpoints


@router.post("/user", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user_in: UserCreate = Body(...),
    no_users_exist: bool = Depends(dependencies.check_no_users_exist),
    current_user: Optional[UserInDB] = Depends(dependencies.get_authenticated_user)
):
    """
    Creates a new user.
    """
    logger.info(f"Attempting to create user '{user_in.username}'. Users exist: {not no_users_exist}")

    is_admin_required = not no_users_exist
    admin_username_for_log = "N/A"  # Default for logging if not required/found

    if is_admin_required:
        # If admin is required, current_user MUST exist and be an admin
        if current_user is None:
            # Should be caught by get_authenticated_user raising 401 if no auth provided
            logger.error("Admin required, but no authenticated user found (get_authenticated_user should have raised 401).")
            # Re-raise 401 just in case dependency behaviour changes or auto_error=False is used later
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        if not current_user.admin:
            logger.warning(f"Admin privileges required to create user, but user '{current_user.username}' is not an admin.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
        admin_username_for_log = current_user.username
        logger.info(f"Admin '{admin_username_for_log}' creating user '{user_in.username}' with admin status: {user_in.admin}.")
        # Admin status is taken from the request body (user_in.admin)
    else:
        # First user creation
        logger.info(f"Creating first user '{user_in.username}' as admin.")
        user_in.admin = True  # Force first user to be admin
        admin_username_for_log = "System (Initial Setup)"
    # Log which admin is performing the action (or if it's initial setup)
    logger.info(f"Admin '{admin_username_for_log}' creating user '{user_in.username}' with admin status: {user_in.admin}.")

    cfg = dependencies.get_config_service()

    # Ensure we have fresh data by refreshing the cache for this specific username
    await cfg.users.refresh_users_cache(user_in.username)

    existing_user = await cfg.users.get_user(user_in.username)
    if existing_user:
        logger.warning(f"Attempted to create user '{user_in.username}', but username already exists.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )

    # Create user data with hashed password
    from mcpo_simple_server.auth.security import get_password_hash
    user_data = {
        "username": user_in.username,
        "hashed_password": get_password_hash(user_in.password),
        "admin": user_in.admin,
        "disabled": user_in.disabled,
        "api_keys": [],
        "env": {},
        "mcpServers": {}
    }

    success = await cfg.users.add_user(user_in.username, user_data)
    if not success:
        logger.error(f"Failed to create user '{user_in.username}' in config file.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user."
        )

    data = await cfg.users.get_user(user_in.username)
    created_user = UserInDB.model_validate(data)
    logger.info(f"User '{created_user.username}' created successfully.")
    return created_user


@router.delete("/user/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_user(
    username: str,
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user)
):
    """
    Deletes a user by username. Requires admin privileges.
    """
    logger.info(f"Admin '{admin_user.username}' attempting to delete user '{username}'.")

    # Prevent admin from deleting themselves
    if username == admin_user.username:
        logger.warning(f"Admin '{admin_user.username}' attempted to delete themselves.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot delete their own account."
        )

    cfg = dependencies.get_config_service()
    user_to_delete = await cfg.users.get_user(username)
    if not user_to_delete:
        logger.warning(f"Attempted to delete non-existent user '{username}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found."
        )

    success = await cfg.users.remove_user(username)
    if not success:
        # This could be a race condition or file save error
        logger.error(f"Failed to delete user '{username}' from config file.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete user '{username}'."
        )

    logger.info(f"User '{username}' deleted successfully by admin '{admin_user.username}'.")
    return None  # 204 No Content
