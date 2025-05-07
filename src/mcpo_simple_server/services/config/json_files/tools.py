"""
Tools Configuration Service Module

This module provides the ToolsConfigService class for managing tool filtering configurations.
"""

from typing import List, Optional
# from loguru import logger
from mcpo_simple_server.services.config import ConfigService
from mcpo_simple_server.services.config.models.memory import MemoryDBModel, ToolsConfigModel


class ToolsConfigFileService:
    """
    Manages tool filtering configurations stored in a JSON file.

    This class is responsible for:
    - Getting and updating whitelist and blacklist settings

    The configuration file has the following structure for tools:
    {
        "tools": {
            "whiteList": ["tool1", "tool2", ...],
            "blackList": ["tool3", "tool4", ...]
        },
        ...
    }
    """

    def __init__(self, parent: ConfigService):
        """
        Initialize the ToolsConfigService.

        Args:
            parent: The parent ConfigService instance
        """
        self.parent = parent
        self.memory: MemoryDBModel = self.parent.memory

    def get_whitelist(self) -> List[str]:
        """
        Get the list of whitelisted tools.

        Returns:
            List of tool names that are whitelisted
        """
        if self.memory.tools is None:
            return []
        return self.memory.tools.model_dump().get("whiteList", [])

    def get_blacklist(self) -> List[str]:
        """
        Get the list of blacklisted tools.

        Returns:
            List of tool names that are blacklisted
        """
        if self.memory.tools is None:
            return []
        return self.memory.tools.model_dump().get("blackList", [])

    def is_tool_whitelisted(self, tool_name: Optional[str] = None) -> bool:
        """
        Check if a tool is whitelisted or if whitelist is active.

        Args:
            tool_name: Name of the tool to check. If None, just checks if whitelist is active.

        Returns:
            If tool_name is provided:
                True if the tool is in the whitelist or the whitelist is empty
            If tool_name is None:
                True if the whitelist is not empty (meaning whitelist is active)
        """
        whitelist = self.get_whitelist()

        # If no tool name provided, just check if whitelist is active
        if tool_name is None:
            return len(whitelist) > 0

        # If whitelist is empty, all tools are allowed
        if not whitelist:
            return True

        # Otherwise, check if the tool is in the whitelist
        return tool_name in whitelist

    def is_tool_blacklisted(self, tool_name: str) -> bool:
        """
        Check if a tool is blacklisted.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if the tool is in the blacklist, False otherwise
        """
        blacklist = self.get_blacklist()
        return tool_name in blacklist

    async def set_whitelist(self, whitelist: List[str]) -> bool:
        """
        Set the whitelist of tools.

        Args:
            whitelist: List of tool names to whitelist

        Returns:
            True if the operation was successful, False otherwise
        """
        if self.memory.tools is None:
            self.memory.tools = ToolsConfigModel()

        self.memory.tools.whiteList = whitelist
        return await self.parent.main_config.save_config()

    async def set_blacklist(self, blacklist: List[str]) -> bool:
        """
        Set the blacklist of tools.

        Args:
            blacklist: List of tool names to blacklist

        Returns:
            True if the operation was successful, False otherwise
        """
        if self.memory.tools is None:
            self.memory.tools = ToolsConfigModel()

        self.memory.tools.blackList = blacklist
        return await self.parent.main_config.save_config()

    async def add_to_whitelist(self, tool_name: str) -> bool:
        """
        Add a tool to the whitelist.

        Args:
            tool_name: Name of the tool to add to the whitelist

        Returns:
            True if the operation was successful, False otherwise
        """
        if self.memory.tools is None:
            self.memory.tools = ToolsConfigModel()

        whitelist = self.get_whitelist()
        if tool_name not in whitelist:
            whitelist.append(tool_name)
            return await self.set_whitelist(whitelist)
        return True

    async def add_to_blacklist(self, tool_name: str) -> bool:
        """
        Add a tool to the blacklist.

        Args:
            tool_name: Name of the tool to add to the blacklist

        Returns:
            True if the operation was successful, False otherwise
        """
        if self.memory.tools is None:
            self.memory.tools = ToolsConfigModel()

        blacklist = self.get_blacklist()
        if tool_name not in blacklist:
            blacklist.append(tool_name)
            return await self.set_blacklist(blacklist)
        return True

    async def remove_from_whitelist(self, tool_name: str) -> bool:
        """
        Remove a tool from the whitelist.

        Args:
            tool_name: Name of the tool to remove from the whitelist

        Returns:
            True if the operation was successful, False otherwise
        """
        if self.memory.tools is None:
            self.memory.tools = ToolsConfigModel()

        whitelist = self.get_whitelist()
        if tool_name in whitelist:
            whitelist.remove(tool_name)
            return await self.set_whitelist(whitelist)
        return True

    async def remove_from_blacklist(self, tool_name: str) -> bool:
        """
        Remove a tool from the blacklist.

        Args:
            tool_name: Name of the tool to remove from the blacklist

        Returns:
            True if the operation was successful, False otherwise
        """
        if self.memory.tools is None:
            self.memory.tools = ToolsConfigModel()

        blacklist = self.get_blacklist()
        if tool_name in blacklist:
            blacklist.remove(tool_name)
            return await self.set_blacklist(blacklist)
        return True

    async def clear_whitelist(self) -> bool:
        """
        Clear the whitelist.

        Returns:
            True if the operation was successful, False otherwise
        """
        return await self.set_whitelist([])

    async def clear_blacklist(self) -> bool:
        """
        Clear the blacklist.

        Returns:
            True if the operation was successful, False otherwise
        """
        return await self.set_blacklist([])
