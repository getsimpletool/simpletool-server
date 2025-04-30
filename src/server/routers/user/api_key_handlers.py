"""
API Key handlers for the user router.
Includes endpoints for creating and managing API Keys used for tool access.
"""
from fastapi import Depends, HTTPException, status, Body
from loguru import logger
from auth.models.auth import APIKeyCreateResponse, APIKeyDeleteRequest, UserInDB
from auth import dependencies, security
from . import router


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_my_api_key(current_user: UserInDB = Depends(dependencies.get_current_access_user)):
    """
    Generates a new API Key for the currently authenticated user,
    stores its plain text, and returns the plain text key ONCE.
    API Keys are used for tool access and authentication.
    """
    config_service = dependencies.get_config_service()

    if not config_service:
        logger.error("Config manager not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = await config_service.users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for API Key creation.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API Key")

    # Generate a new API Key
    plain_key, _ = security.create_api_key(current_user.username)

    # Add the plain key to the user's API keys
    user_data["api_keys"].append(plain_key)

    # Save the updated user data
    success = await config_service.users.add_user(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to save API Key for user '{current_user.username}' in config.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API Key")

    logger.info(f"API Key created successfully for user '{current_user.username}'.")
    return {"api_key": plain_key, "detail": "API Key created successfully. Store it securely, it won't be shown again."}


@router.delete("/api-keys", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_api_key(
    key_info: APIKeyDeleteRequest = Body(...),
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Deletes an API Key for the currently authenticated user, identified by its full key.
    """
    config_service = dependencies.get_config_service()

    if not config_service:
        logger.error("Config manager not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = await config_service.users.get_user(current_user.username)
    if not user_data or "api_keys" not in user_data or not user_data["api_keys"]:
        logger.warning(f"No API Keys found for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

    key_to_delete = key_info.api_key
    if key_to_delete not in user_data["api_keys"]:
        logger.warning(f"API Key '{key_to_delete}' not found for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")
    user_data["api_keys"].remove(key_to_delete)

    # Save the updated user data
    success = await config_service.users.add_user(current_user.username, user_data)
    if not success:
        logger.error(f"Failed to delete API Key for user '{current_user.username}' in config.")
        # Don't raise 500, maybe the key was already gone. Log it.
        # Proceed to return 204 as the key is effectively gone or deletion failed post-check
    else:
        logger.info(f"API Key deleted successfully for user '{current_user.username}'.")
