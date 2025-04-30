"""
Configuration management module for the MCP server.

This module provides classes for managing server and user configurations.
"""
import json
from typing import Dict, Any
from loguru import logger
from server.services.config import ConfigService
from server.services.config.models.files import FileMainModel, FileToolsConfigModel
from server.services.config.models.memory import MemoryDBModel, McpServerConfigModel, ToolsConfigModel


class MainFileConfigService:

    def __init__(self, parent: 'ConfigService'):
        self.parent = parent
        self.memory: MemoryDBModel = self.parent.memory

    async def load_config(self) -> Dict[str, Any]:
        """
        Load main configuration from the config file and save in Memory.

        Returns:
            The loaded main configuration file
        """
        logger.info(f"Loading configuration from {self.parent.config_file_path}")
        try:
            with open(self.parent.config_file_path, "r", encoding="utf-8") as config_file:
                main_file_config = json.load(config_file)
                # Convert the loaded JSON to a Pydantic model
                # > mcpServers
                for server_name, server_config in main_file_config.get("mcpServers", {}).items():
                    self.memory.mcpServers[server_name] = McpServerConfigModel(**server_config)
                # > tools
                self.memory.tools = ToolsConfigModel(**main_file_config.get("tools", {}))
            logger.info(f"Configuration loaded successfully from {self.parent.config_file_path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading config: {str(e)}")
            # Initialize empty configuration and persist it to prevent future load errors
            self.memory.mcpServers = {}
            try:
                file = FileMainModel()
                file.tools = FileToolsConfigModel()
                with open(self.parent.config_file_path, "w", encoding="utf-8") as cf:
                    json.dump(file.model_dump(), cf, indent=2)
                logger.info(f"Created new config file at {self.parent.config_file_path}")
            except Exception as write_e:
                logger.error(f"Failed to write new config file: {str(write_e)}")

        return self.memory.model_dump()

    async def save_config(self) -> bool:
        """
        Save current main configuration. Copy content of memory to json main file

        Returns:
            True if the save was successful, False otherwise
        """
        try:
            # Create a file model directly from the current memory state
            # This ensures we save exactly what's in memory
            main_file_content = FileMainModel(**self.memory.model_dump())

            # Write the config to the file
            with open(self.parent.config_file_path, "w", encoding="utf-8") as config_file:
                json.dump(main_file_content.model_dump(), config_file, indent=4)

            logger.info(f"Configuration saved successfully to {self.parent.config_file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            return False

    def get_section(self, section_name: str) -> Dict[str, Any]:
        """
        Get a specific section from the memory configuration.

        Args:
            section_name: The name of the section

        Returns:
            The section data as a dictionary, or an empty dict if not found
        """
        return self.memory.model_dump().get(section_name, {})
