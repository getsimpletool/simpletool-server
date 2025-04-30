from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from services.config.models.memory import UserConfigModel as UserBase


class Token(BaseModel):
    """JWT Token model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data contained within the JWT token."""
    username: Optional[str] = None


class LoginRequest(BaseModel):
    """Model for user login request."""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern="^[a-zA-Z0-9_-]+$", 
        examples=["admin"]
    )
    password: str = Field(
        ..., 
        min_length=1, 
        examples=["admin"]
    )


class UserCreate(BaseModel):
    """Model for creating a new user."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Username (3-50 chars, alphanumeric with _ and -)",
        examples=["admin"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Plain text password (min 8 chars)",
        examples=["secure_password123"]
    )
    admin: bool = Field(
        default=False,
        description="Whether the user has admin privileges",
        examples=[False]
    )
    disabled: bool = Field(
        default=False,
        description="Whether the user account is disabled",
        examples=[False]
    )


class UserInDBBase(UserBase):
    """User model as stored in the database (config.json)."""
    hashed_password: str
    hashed_api_keys: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True  # Replaces orm_mode = True in Pydantic v2


class UserInDB(UserInDBBase):
    pass


class UserPublic(BaseModel):
    """User model for public responses (omits sensitive data)."""
    username: str
    admin: bool
    disabled: bool
    env: Dict[str, str] = Field(default_factory=dict)
    mcpServers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PasswordUpdateInput(BaseModel):
    """Model for updating password for both users and admins (no length validation)."""
    current_password: str
    new_password: str


class UserUpdateEnv(BaseModel):
    """Model for updating user environment variables."""
    env: Dict[str, str] = Field(
        ..., 
        description="Dictionary of global environment variables as key-value pairs", 
        examples=[{"API_KEY": "your-api-key", "DEBUG": "true", "ADDITIONAL_PROP": "value"}]
    )


class UserUpdateSingleEnv(BaseModel):
    """Model for updating a single environment variable."""
    value: str = Field(
        ..., 
        description="Value for the environment variable", 
        examples=["your-api-key-value"]
    )


class ServerEnvUpdate(BaseModel):
    """Model for updating environment variables for a specific server."""
    env: Dict[str, str] = Field(
        ..., 
        description="Dictionary of environment variables for a specific server", 
        examples=[{"API_KEY": "your-api-key", "DEBUG": "true", "ADDITIONAL_PROP": "value"}]
    )


class ServerEnvResponse(BaseModel):
    """Response model for server environment variables."""
    server_name: str
    env: Dict[str, str]


class PrivateServerInfo(BaseModel):
    """Information about a private server instance."""
    name: str
    status: str
    pid: Optional[int] = None
    uptime_seconds: int = 0
    tool_count: int = 0
    type: str = "private"
    base_server: str = ""


class PrivateServerListResponse(BaseModel):
    """Response model for listing private server instances."""
    servers: List[PrivateServerInfo]


class APIKeyCreateResponse(BaseModel):
    """Response model when creating an API key (shows plain text key once)."""
    api_key: str
    detail: str = "API key created successfully. Store it securely, it won't be shown again."


class APIKeyDeleteRequest(BaseModel):
    """Model for requesting API key deletion."""
    api_key: str = Field(
        ..., 
        min_length=8,
        examples=["st-key-123e4567e89b12d3a456"]
    )


class UserUpdateUserEnv(BaseModel):
    """Model for updating global user environment variables."""
    user_env: Dict[str, str] = Field(
        ..., 
        description="Dictionary of global environment variables as key-value pairs that apply to all servers", 
        examples=[{"API_KEY": "your-api-key", "DEBUG": "true", "ADDITIONAL_PROP": "value"}]
    )


class UserUpdateSingleUserEnv(BaseModel):
    """Model for updating a single global user environment variable."""
    value: str = Field(
        ..., 
        description="Value for the global environment variable", 
        examples=["your-api-key-value"]
    )
