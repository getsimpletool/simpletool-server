"""
Configuration management module for the SimpleToolServer.

This module provides classes for managing server
"""
import asyncio
from typing import Dict, Any, Optional
from mcpo_simple_server.config import CONFIG_MAIN_FILE_PATH
from .models.memory import MemoryDBModel, ToolsConfigModel


class ConfigService:
    """
    Base class for managing configurations stored in a JSON format.
    ALL manipulations related to configuration files are handled here.
    All configuration files are stored in the same directory as the config file.
    """

    def __init__(self, storage_type: str = "json_files", settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the ConfigService.

        Args:
            storage_type:
            settings:
        """
        self.memory: MemoryDBModel = MemoryDBModel(mcpServers={}, users={}, tools=ToolsConfigModel())

        if storage_type == "files":
            if settings is not None and settings.get("config_file_path"):
                self.config_file_path = settings.get("config_file_path", CONFIG_MAIN_FILE_PATH)
            else:
                self.config_file_path = CONFIG_MAIN_FILE_PATH

            # Lock for thread safety when modifying the cache
            self.cache_lock_users = asyncio.Lock()

            from .json_files.main_file import MainFileConfigService    # pylint: disable=C0415
            from .json_files.users import UsersConfigFileService     # pylint: disable=C0415
            from .json_files.mcpservers import McpServersFileConfigService    # pylint: disable=C0415
            from .json_files.tools import ToolsConfigFileService    # pylint: disable=C0415
            self.main_config = MainFileConfigService(self)
            self.users = UsersConfigFileService(self)
            self.mcpserver = McpServersFileConfigService(self)
            self.tools = ToolsConfigFileService(self)
        else:
            raise ValueError("Invalid config type")
