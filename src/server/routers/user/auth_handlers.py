"""
Authentication handlers for the user router.
Includes login and password management endpoints.
"""
from datetime import timedelta
from fastapi import Depends, HTTPException, status, Body
from loguru import logger

from auth.models.auth import Token, LoginRequest, UserPublic, PasswordUpdateInput, UserInDB
from auth import security, dependencies
from . import router


@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: LoginRequest = Body(...)):
    """
    Logs in a user and returns an access token.
    Uses username and password provided in the request body.
    """
    if not dependencies.get_config_service():
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Config service not initialized",
        )

    # Check if users have been loaded
    if not dependencies.get_config_service().users.get_all_users():
        # Load user configurations if not already loaded
        try:
            await dependencies.get_config_service().users.refresh_users_cache()
        except Exception as e:
            logger.error(f"Failed to load user configurations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: Failed to load user configurations",
            )

    # Authenticate user
    user = await security.authenticate_user(
        dependencies.get_config_service().users, form_data.username, form_data.password
    )
    if not user:
        logger.warning(f"Failed login attempt for user '{form_data.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is disabled
    if user.disabled:
        logger.warning(f"Login attempt for disabled user '{form_data.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=security.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    logger.info(f"User '{form_data.username}' logged in successfully")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: UserInDB = Depends(dependencies.get_current_access_user)):
    """
    Returns the details of the currently authenticated user (excluding sensitive info).
    """
    return UserPublic(**current_user.dict())


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_password(
    password_update: PasswordUpdateInput = Body(...),
    current_user: UserInDB = Depends(dependencies.get_current_access_user)
):
    """
    Updates the password for the currently authenticated user.
    """
    if not dependencies.get_config_service():
        logger.error("Config service not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Get the current user data
    user_data = await dependencies.get_config_service().users.get_user(current_user.username)
    if not user_data:
        logger.error(f"Failed to retrieve user '{current_user.username}' for password update.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update password")

    # Verify current password
    if not security.verify_password(password_update.current_password, user_data["hashed_password"]):
        logger.warning(f"Invalid current password provided for user '{current_user.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current password",
        )

    # Manual password length validation for non-admin users
    if not current_user.admin and len(password_update.new_password) < 8:
        logger.warning(f"Password too short for user '{current_user.username}' (admin bypasses length check)")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must be at least 8 characters long."
        )

    # Hash new password
    new_hashed_password = security.get_password_hash(password_update.new_password)
    user_data["hashed_password"] = new_hashed_password
    # Save updated user data
    await dependencies.get_config_service().users.save_user_configfile(current_user.username, user_data)
    # Refresh only this user's cache
    await dependencies.get_config_service().users.refresh_users_cache(current_user.username)
    logger.info(f"Password updated for user '{current_user.username}'")
    return
