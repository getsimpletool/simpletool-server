"""
Environment variable handlers for the user router.
Includes endpoints for managing global environment variables.
"""
from typing import Dict
from fastapi import Depends, HTTPException, status, Body
from loguru import logger
from auth.models.auth import UserInDB, UserPublic, UserUpdateEnv, UserUpdateSingleEnv
from auth import dependencies
from . import router


@router.get("/env", response_model=Dict[str, str])
async def get_my_env(
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Get global environment variables for the current user.
    These variables apply to all servers and take precedence over server-specific variables.
    """
    config_service = dependencies.get_config_service()
    if not config_service:
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = await config_service.users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for global environment variables.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve global environment variables")

    # Get the user's global environment variables
    user_env = user_data.get("env", {})
    # DEBUG LOGGING
    logger.debug(f"[DEBUG /user/env GET] username={current_user.username} env={user_env}")
    logger.debug(f"[DEBUG /user/env GET] user_data={user_data}")
    logger.info(f"Retrieved global environment variables for user '{current_user.username}'.")
    return user_env


@router.put("/env", response_model=Dict[str, str])
async def update_my_env(
    env_update: UserUpdateEnv = Body(...),
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Update global environment variables for the current user.
    These variables apply to all servers and take precedence over server-specific variables.
    This replaces the entire 'env' dictionary for the user.
    """
    config_service = dependencies.get_config_service()

    if not config_service:
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = await config_service.users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for global environment variables update.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve global environment variables for update")

    # Update the user's global environment variables
    user_data["env"] = env_update.env

    # Save the updated user data
    success = await config_service.users.save_user_configfile(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to update global environment variables for user '{current_user.username}' in config.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update global environment variables")

    # DEBUG LOGGING
    logger.debug(f"[DEBUG /user/env PUT] username={current_user.username} env={env_update.env}")
    logger.debug(f"[DEBUG /user/env PUT] user_data={user_data}")
    # Return the updated env dictionary
    logger.info(f"Global environment variables updated successfully for user '{current_user.username}'.")
    return user_data["env"]


@router.delete("/env", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_env(
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Delete all global environment variables for the current user.
    """
    config_service = dependencies.get_config_service()
    if not config_service:
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = await config_service.users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for global environment deletion.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete global environment variables")

    # Delete the user's global environment variables
    user_data["env"] = {}

    # Save the updated user data
    success = await config_service.users.save_user_configfile(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to delete global environment variables for user '{current_user.username}' in config.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete global environment variables")

    logger.info(f"Global environment variables deleted successfully for user '{current_user.username}'.")


@router.delete("/env/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_env_key(
    key: str,
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Delete a specific global environment variable key for the current user.
    """
    config_service = dependencies.get_config_service()
    if not config_service:
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = await config_service.users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for global environment key deletion.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete global environment variable")

    # Get the user's global environment variables
    user_env = user_data.get("env", {})

    # Check if the key exists
    if key not in user_env:
        logger.warning(f"Global environment key '{key}' not found for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment variable '{key}' not found")

    # Delete the key
    del user_env[key]

    # Update the user data
    user_data["env"] = user_env

    # Save the updated user data
    success = await config_service.users.save_user_configfile(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to update global environment after deleting key '{key}' for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update global environment variables")

    logger.info(f"Global environment key '{key}' deleted successfully for user '{current_user.username}'.")


@router.put("/env/{key}", response_model=Dict[str, str])
async def update_my_env_key(
    key: str,
    env_value: UserUpdateSingleEnv = Body(...),
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Update a specific global environment variable key for the current user.
    This only affects the specified key and leaves other global environment variables unchanged.
    """
    config_service = dependencies.get_config_service()
    if not config_service:
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )
    user_data = await config_service.users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for global environment key update.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update global environment variable")
    user_env = user_data.get("env", {})
    user_env[key] = env_value.value
    user_data["env"] = user_env
    success = await config_service.users.save_user_configfile(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to update global environment key '{key}' for user '{current_user.username}' in config.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update global environment variable")
    logger.info(f"Global environment key '{key}' updated successfully for user '{current_user.username}'.")
    return user_data["env"]
