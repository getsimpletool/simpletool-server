import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
from . import security
from mcpo_simple_server.auth.models.auth import UserInDB, TokenData
from mcpo_simple_server.services.config import ConfigService

# Replace OAuth2 with a simpler bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Authorization")

# Get admin bearer hack token from environment variable
ADMIN_BEARER_HACK = os.getenv("ADMIN_BEARER_HACK", "")
if ADMIN_BEARER_HACK:
    logger.info("ADMIN_BEARER_HACK environment variable is set. Static admin Bearer token is enabled.")

# Config manager will be set from main.py
CONFIG_SERVICE: Optional[ConfigService] = None   # pylint: disable=C0103


def set_config_service(config_srv: ConfigService):
    """Set the config service instance to be used by auth dependencies."""
    global CONFIG_SERVICE
    CONFIG_SERVICE = config_srv
    logger.info("Auth dependencies: Config service set")

    # Initialize the users directory
    users_dir = os.path.join(os.path.dirname(config_srv.config_file_path), "users")
    if not os.path.exists(users_dir):
        os.makedirs(users_dir, exist_ok=True)
    logger.info(f"Users directory set to: {users_dir}")


def get_config_service() -> ConfigService:
    if CONFIG_SERVICE is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Config service not initialized"
        )
    return CONFIG_SERVICE


async def get_current_user_from_token(auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Optional[UserInDB]:
    if auth is None:
        return None

    token = auth.credentials

    # Check if token matches ADMIN_BEARER_HACK
    if ADMIN_BEARER_HACK and token == ADMIN_BEARER_HACK:
        logger.info("Authentication successful using ADMIN_BEARER_HACK")
        # Return a synthetic admin user
        return UserInDB(
            username="admin",
            admin=True,
            disabled=False,
            hashed_password="",  # Not needed for this authentication method
            hashed_api_keys=[]
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data: Optional[TokenData] = security.verify_token(token)
    if token_data is None or token_data.username is None:
        logger.warning(f"Token data: {token_data}")
        logger.warning("Token verification failed or username missing in token.")
        raise credentials_exception

    if not CONFIG_SERVICE:
        logger.error("Config manager not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    user_data = await CONFIG_SERVICE.users.get_user(username=token_data.username)
    if user_data is None:
        logger.warning(f"User '{token_data.username}' from token not found in config.")
        raise credentials_exception

    return UserInDB(**user_data)


async def get_user_from_api_key(auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Optional[UserInDB]:
    if auth is None:
        logger.debug("No API key provided in request.")
        return None

    api_key = auth.credentials

    if not CONFIG_SERVICE:
        logger.error("Config manager not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    all_users = CONFIG_SERVICE.users.get_all_users()

    for username, user_data in all_users.items():
        if "api_keys" not in user_data or not user_data["api_keys"]:
            continue

        # Convert single API key to a list if needed
        api_keys_list = user_data["api_keys"]
        if isinstance(api_keys_list, str):
            api_keys_list = [api_keys_list]

        # Direct comparison of plain text API keys
        if api_key in api_keys_list:
            logger.info(f"API key authentication successful for user '{username}'")
            return UserInDB(**user_data)

    logger.warning("API key authentication failed. Invalid API key.")
    return None


async def get_authenticated_user(
    token_user: Optional[UserInDB] = Depends(get_current_user_from_token),
    api_key_user: Optional[UserInDB] = Depends(get_user_from_api_key)
) -> UserInDB:
    """
    Get the authenticated user from either a JWT token or an API key.

    This dependency will first check for a valid JWT token, then fall back to API key.
    If neither is valid, it will raise a 401 Unauthorized exception.
    """
    user = token_user or api_key_user

    if user is None:
        logger.warning("Authentication failed. No valid token or API key provided.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled:
        logger.warning(f"Authentication failed. User '{user.username}' is disabled.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


async def get_current_access_user(current_user: Optional[UserInDB] = Depends(get_current_user_from_token)) -> UserInDB:
    """
    Get the current authenticated user via access token only (no API key).
    """
    if current_user is None:
        logger.warning("Access token authentication failed. No valid token provided.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.disabled:
        logger.warning(f"Authentication failed. User '{current_user.username}' is disabled.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: UserInDB = Depends(get_current_access_user)) -> UserInDB:
    """
    Get the current authenticated user and verify they have admin privileges.
    """
    if not current_user.admin:
        logger.warning(f"Admin access denied for user '{current_user.username}'.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user


async def get_username(
    api_key_user: Optional[UserInDB] = Depends(get_user_from_api_key)
) -> Optional[str]:
    """
    Get the username of the authenticated user, if any.

    This dependency will try to extract the username from an API key.
    If no valid authentication is provided, it will return None, allowing for both
    authenticated and unauthenticated access to the endpoint.

    Returns:
        The username of the authenticated user, or None if no valid authentication was provided
    """
    # Only API keys are accepted for tool and public prompts; fallback to guest
    if api_key_user:
        return api_key_user.username
    return None


async def check_no_users_exist() -> bool:
    """Check if no users exist in the system yet."""
    if not CONFIG_SERVICE:
        logger.error("Config manager not set in auth dependencies")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )
    return len(CONFIG_SERVICE.users.get_all_users()) == 0
