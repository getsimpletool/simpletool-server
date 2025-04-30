"""
Models for configuration elements
"""
from pydantic import BaseModel, Field
from typing import Dict, Optional, List


class ToolsConfigModel(BaseModel):
    """
    Configuration model for tool filtering.
    """
    whiteList: Optional[List[str]] = Field(default_factory=list, description="List of allowed tools")
    blackList: Optional[List[str]] = Field(default_factory=list, description="List of blocked tools")


class McpServerConfigModel(BaseModel):
    """
    Configuration for a single MCP server instance.
    """
    command: str
    args: list[str]
    env: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    disabled: Optional[bool] = False


class UserMcpServerConfigModel(BaseModel):
    """
    Configuration for a single MCP server instance under User configuration.
    """
    args: Optional[list[str]] = None
    env: Optional[Dict[str, str]] = None
    disabled: Optional[bool] = False


class UserConfigModel(BaseModel):
    """User configuration model for config manager."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    hashed_password: str
    admin: bool = False
    disabled: bool = False
    api_keys: Optional[list[str]] = None
    env: Dict[str, str] = Field(default_factory=dict, description="Global environment variables that apply to all servers")
    mcpServers: Dict[str, UserMcpServerConfigModel] = Field(default_factory=dict, description="Server-specific configurations")


class MemoryDBModel(BaseModel):
    """Configuration model."""
    mcpServers: Dict[str, McpServerConfigModel] = Field(default_factory=dict, description="Server-specific configurations")
    users: Dict[str, UserConfigModel] = Field(default_factory=dict, description="User-specific configurations")
    tools: Optional[ToolsConfigModel] = Field(default_factory=ToolsConfigModel, description="Tool-specific configurations")
