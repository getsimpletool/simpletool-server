from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List


class UserConfig(BaseModel):
    """User configuration model for config manager."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    hashed_password: str
    admin: bool = False
    disabled: bool = False
    api_keys: Optional[list[str]] = None
    env: Dict[str, str] = Field(default_factory=dict,
                                description="Global environment variables that apply to all servers")
    mcpServers: Dict[str, Dict[str, Any]] = Field(default_factory=dict,
                                                  description="Server-specific configurations")

    class Config:
        extra = "allow"
