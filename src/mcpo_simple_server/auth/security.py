import os
import uuid
import hmac
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from mcpo_simple_server.auth.models.auth import UserInDB, TokenData

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Use environment variables with defaults
SALT_PEPPER = os.getenv("SALT", "default_insecure_pepper")  # Get pepper from env
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_insecure_secret_key")  # Get JWT secret from env
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
API_KEY_PREFIX = "st-"  # Prefix for generated API keys

# --- Password Hashing ---
# Use bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password, incorporating the SALT pepper."""
    # Combine password and pepper before verification
    password_with_pepper = plain_password + SALT_PEPPER
    try:
        return pwd_context.verify(password_with_pepper, hashed_password)
    except Exception:  # Broad exception for passlib errors
        return False


def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt, incorporating the SALT pepper."""
    # Combine password and pepper before hashing
    password_with_pepper = password + SALT_PEPPER
    return pwd_context.hash(password_with_pepper)

# --- JWT Handling ---


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verifies a JWT token and returns the payload as TokenData if valid."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None  # Or raise credential_exception if preferred
        # Validate payload against the Pydantic model
        token_data = TokenData(username=username)
        return token_data
    except (JWTError, ValidationError):
        # Log the error appropriately in a real application
        return None  # Or raise credential_exception

# --- API Key Handling ---


def create_api_key(username: str) -> Tuple[str, str]:
    """
    Generates a new secure API key (plain text) and its hash.
    API keys are used for tool access and authentication.

    Args:
        username: The username to encode in the API key

    Returns:
        Tuple of (plain_key, hashed_key)
    """
    # Create a secure hash of the username using HMAC with our salt
    username_hmac = hmac.new(
        SALT_PEPPER.encode(),
        username.encode(),
        hashlib.sha256
    ).hexdigest()[:32]  # Use first 32 chars for better security

    # Get current Unix timestamp
    timestamp = int(time.time())

    # Generate a UUID version 1 (time-based) for the API key
    # Format example: st-<uuid1>-<username_hmac>-<timestamp>
    uuid_str = str(uuid.uuid1())

    # Combine the prefix, UUID string, username HMAC, and timestamp
    plain_key = f"{API_KEY_PREFIX}{uuid_str}-{username_hmac}-{timestamp}"

    hashed_key = get_api_key_hash(plain_key)
    return plain_key, hashed_key


def extract_username_hmac_from_api_key(api_key: str) -> Optional[str]:
    """
    Extracts the username HMAC from an API key if it follows the correct format.

    Args:
        api_key: The API key to extract the username HMAC from

    Returns:
        The extracted username HMAC or None if the key doesn't follow the expected format
    """
    try:
        # The username HMAC is the part after the last dash
        parts = api_key.split('-')
        if len(parts) < 4:  # Need at least prefix, uuid parts, username HMAC, and timestamp
            return None

        username_hmac = parts[-2]  # Get the second last part
        return username_hmac
    except Exception:
        # If any error occurs during extraction, return None
        return None


def verify_username_hmac(username: str, hmac_value: str) -> bool:
    """
    Verifies if a given HMAC value corresponds to a username.

    Args:
        username: The username to verify
        hmac_value: The HMAC value to verify against

    Returns:
        True if the HMAC matches the username, False otherwise
    """
    calculated_hmac = hmac.new(
        SALT_PEPPER.encode(),
        username.encode(),
        hashlib.sha256
    ).hexdigest()[:32]

    return hmac.compare_digest(calculated_hmac, hmac_value)


def get_api_key_hash(api_key: str) -> str:
    """
    Hashes an API key using bcrypt, incorporating the SALT pepper.
    API keys are used for tool access and authentication.
    """
    # Combine key and pepper before hashing
    key_with_pepper = api_key + SALT_PEPPER
    return pwd_context.hash(key_with_pepper)


def verify_api_key(plain_key: str, hashed_keys: List[str]) -> bool:
    """Verifies a plain API key against a list of hashed keys."""
    for hashed_key in hashed_keys:
        try:
            if pwd_context.verify(plain_key, hashed_key):
                return True
        except Exception:  # Broad exception for passlib errors
            continue
    return False


async def authenticate_user(user_manager, username: str, password: str):
    """
    Authenticate a user with username and password.
    Returns the user model if authentication is successful, None otherwise.
    """
    user_data = await user_manager.get_user(username=username)
    if not user_data:
        return None

    # Convert user data to UserInDB model
    user = UserInDB(**user_data)

    if not verify_password(password, user.hashed_password):
        return None

    return user
