"""
Public MCP Servers Router

This module provides functionality for managing MCP servers.
"""
from typing import Dict, Any, List
from fastapi import Depends, HTTPException, status, Body, Request
from pydantic import BaseModel
from mcpo_simple_server.auth.models.auth import UserInDB
from mcpo_simple_server.auth import dependencies
from mcpo_simple_server.services.mcpserver import McpServerService
from mcpo_simple_server.routers.admin import _reload_tools_router
from mcpo_simple_server.routers.public import router, get_mcpserver_service
from loguru import logger


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
    server_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    List all configured public mcpservers and their status.
    This endpoint is publicly accessible without authentication.

    Returns:
        Dict containing server configurations and status
    """
    logger.info("Public request for MCP server list")

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
