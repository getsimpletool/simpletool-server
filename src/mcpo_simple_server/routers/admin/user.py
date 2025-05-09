"""
Admin User Router

This module provides functionality for managing users.
"""
from typing import Optional
from fastapi import Body, Depends, HTTPException, status
from mcpo_simple_server.auth.models.auth import UserInDB, UserCreate, UserPublic
from mcpo_simple_server.auth import dependencies
from mcpo_simple_server.routers.admin import router
from mcpo_simple_server.auth.security import get_password_hash
from loguru import logger


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
