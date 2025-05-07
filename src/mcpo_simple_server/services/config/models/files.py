"""
Models for configuration elements
"""
from pydantic import BaseModel, Field
from typing import Dict, Optional, List


class FileMcpServerConfigModel(BaseModel):
    """
    File configuration for a single MCP server instance.
    """
    command: str
    args: list[str]
    env: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    disabled: Optional[bool] = False


class FileToolsConfigModel(BaseModel):
    """
    File configuration model for tool filtering.
    """
    whiteList: Optional[List[str]] = Field(default_factory=list, description="List of allowed tools")
    blackList: Optional[List[str]] = Field(default_factory=list, description="List of blocked tools")


class FileMainModel(BaseModel):
    """
    Main File Configuration model.
    """
    mcpServers: Dict[str, FileMcpServerConfigModel] = {}
    tools: Optional[FileToolsConfigModel] = None
