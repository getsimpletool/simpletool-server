"""
Server handlers for the user router.
Includes endpoints for managing server-specific environment variables and private server instances.
"""
from typing import Dict, Any, List
from fastapi import Depends, HTTPException, status, Body, Request
from loguru import logger

from auth.models.auth import UserInDB, UserPublic, ServerEnvUpdate, UserUpdateSingleEnv
from auth import dependencies
from server.services.mcpserver import McpServerService
from . import router


def get_mcpserver_service(request: Request) -> McpServerService:
    return request.app.state.mcpserver_service

# --- Server-Specific Environment Variables Endpoints ---


@router.get("/server/{server_name}", response_model=Dict[str, Any])
async def get_server_config(
    server_name: str,
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Get server-specific configuration for the current user.
    """
    if not dependencies.get_config_service():
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = dependencies.get_config_service().users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for server configuration.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve server configuration")

    # Get the server configuration
    server_configs = user_data.get("mcpServers", {})
    server_config = server_configs.get(server_name, {})

    logger.info(f"Retrieved server configuration for server '{server_name}' for user '{current_user.username}'.")
    return server_config


@router.put("/server/{server_name}/env", response_model=UserPublic)
async def update_server_env(
    server_name: str,
    env_update: ServerEnvUpdate = Body(...),
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Update environment variables for a specific server for the current user.
    """
    if not dependencies.get_config_service():
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = dependencies.get_config_service().users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for server environment update.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update server environment variables")

    # Get or create the server configuration
    server_configs = user_data.get("mcpServers", {})
    if server_name not in server_configs:
        server_configs[server_name] = {}

    # Update the server environment variables
    server_configs[server_name]["env"] = env_update.env

    # Update the user data
    user_data["mcpServers"] = server_configs

    # Save the updated user data
    success = await dependencies.get_config_service().users.add_user(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to update server environment variables for server '{server_name}' for user '{current_user.username}' in config.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update server environment variables")

    # Return the updated user model
    updated_user = UserInDB(**user_data)
    logger.info(f"Server environment variables updated successfully for server '{server_name}' for user '{current_user.username}'.")
    return updated_user


@router.delete("/server/{server_name}/env", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server_env(
    server_name: str,
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Delete environment variables for a specific server for the current user.
    """
    if not dependencies.get_config_service():
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = dependencies.get_config_service().users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for server environment deletion.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete server environment variables")

    # Get the server configuration
    server_configs = user_data.get("mcpServers", {})
    if server_name not in server_configs:
        logger.warning(f"Server '{server_name}' not found in configuration for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Server '{server_name}' not found")

    # Delete the server environment variables
    if "env" in server_configs[server_name]:
        server_configs[server_name]["env"] = {}

    # Update the user data
    user_data["mcpServers"] = server_configs

    # Save the updated user data
    success = await dependencies.get_config_service().users.add_user(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to delete server environment variables for server '{server_name}' for user '{current_user.username}' in config.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete server environment variables")

    logger.info(f"Server environment variables deleted successfully for server '{server_name}' for user '{current_user.username}'.")


@router.delete("/server/{server_name}/env/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server_env_key(
    server_name: str,
    key: str,
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Delete a specific environment variable key for a specific server for the current user.
    """
    if not dependencies.get_config_service():
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = dependencies.get_config_service().users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for server environment key deletion.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete server environment variable")

    # Get the server configuration
    server_configs = user_data.get("mcpServers", {})
    if server_name not in server_configs:
        logger.warning(f"Server '{server_name}' not found in configuration for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Server '{server_name}' not found")

    # Get the server environment variables
    server_env = server_configs[server_name].get("env", {})

    # Check if the key exists
    if key not in server_env:
        logger.warning(f"Server environment key '{key}' not found for server '{server_name}' for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment variable '{key}' not found for server '{server_name}'")

    # Delete the key
    del server_env[key]

    # Update the server configuration
    server_configs[server_name]["env"] = server_env

    # Update the user data
    user_data["mcpServers"] = server_configs

    # Save the updated user data
    success = await dependencies.get_config_service().users.add_user(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to update server environment after deleting key '{key}' for server '{server_name}' for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update server environment variables")

    logger.info(f"Server environment key '{key}' deleted successfully for server '{server_name}' for user '{current_user.username}'.")


@router.put("/server/{server_name}/env/{key}", response_model=UserPublic)
async def update_server_env_key(
    server_name: str,
    key: str,
    env_value: UserUpdateSingleEnv = Body(...),
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Update a specific environment variable key for a specific server for the current user.
    """
    if not dependencies.get_config_service():
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = dependencies.get_config_service().users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for server environment key update.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update server environment variable")

    # Get or create the server configuration
    server_configs = user_data.get("mcpServers", {})
    if server_name not in server_configs:
        server_configs[server_name] = {}

    # Get or create the server environment variables
    if "env" not in server_configs[server_name]:
        server_configs[server_name]["env"] = {}

    # Update the key
    server_configs[server_name]["env"][key] = env_value.value

    # Update the user data
    user_data["mcpServers"] = server_configs

    # Save the updated user data
    success = await dependencies.get_config_service().users.add_user(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to update server environment key '{key}' for server '{server_name}' for user '{current_user.username}' in config.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update server environment variable")

    # Return the updated user model
    updated_user = UserInDB(**user_data)
    logger.info(f"Server environment key '{key}' updated successfully for server '{server_name}' for user '{current_user.username}'.")
    return updated_user


# --- Private Server Instances Endpoints ---


@router.get("/servers", response_model=List[Dict[str, Any]])
async def list_my_servers(
    current_user: UserInDB = Depends(dependencies.get_current_access_user),
    mcpserver_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    List private server instances for the current user.
    """
    try:
        servers = await mcpserver_service.list_user_servers(current_user.username)
        logger.info(f"Listed private servers for user '{current_user.username}'.")
        return servers
    except Exception as e:
        logger.error(f"Error listing private servers for user '{current_user.username}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list private servers: {str(e)}"
        )


@router.post("/servers/{server_name}", response_model=Dict[str, Any])
async def start_private_server(
    server_name: str,
    current_user: UserInDB = Depends(dependencies.get_current_access_user),
    mcpserver_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    Start a private server instance for the current user.
    """
    try:
        server_info = await mcpserver_service.start_private_server(current_user.username, server_name)
        logger.info(f"Started private server '{server_name}' for user '{current_user.username}'.")
        return server_info
    except Exception as e:
        logger.error(f"Error starting private server '{server_name}' for user '{current_user.username}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start private server: {str(e)}"
        )


@router.delete("/servers/{server_name}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_private_server(
    server_name: str,
    current_user: UserInDB = Depends(dependencies.get_current_access_user),
    mcpserver_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    Stop a private server instance for the current user.
    """
    try:
        await mcpserver_service.stop_private_server(current_user.username, server_name)
        logger.info(f"Stopped private server '{server_name}' for user '{current_user.username}'.")
    except Exception as e:
        logger.error(f"Error stopping private server '{server_name}' for user '{current_user.username}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop private server: {str(e)}"
        )
