"""
Servers Configuration Manager Module

This module provides the ServersConfigManager class for managing MCP server configurations.
"""
import json
import os
from typing import Dict, List, Any, Optional
from loguru import logger
from mcpo_simple_server.services.config import ConfigService
from mcpo_simple_server.services.config.models.memory import MemoryDBModel, McpServerConfigModel


class McpServersFileConfigService:
    """
    Manages MCP server configurations stored in a JSON file.

    This class is responsible for:
    - Loading server configurations from a file
    - Saving server configurations to a file
    - Adding, updating, and removing server configurations
    - Validating server configurations

    The configuration file has the following structure for servers:
    {
        "mcpServers": {
            "server_name": {
                "command": "command_to_execute",
                "args": ["arg1", "arg2", ...],
                "env": {"ENV_VAR1": "value1", ...},
                "description": "Optional description",
                "disabled": true/false  # When true, the server will not be started
            },
            ...
        }
    }
    """

    def __init__(self, parent: 'ConfigService'):
        """
        Initialize the ServersConfigManager.

        Args:
            parent: The parent ConfigService instance
        """
        self.parent = parent
        self.memory: MemoryDBModel = parent.memory

    def get_mcpserver_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration for a specific server.

        Args:
            server_name: The name of the server

        Returns:
            The server configuration dictionary or None if not found
        """
        if server_name not in self.memory.mcpServers:
            return None
        return self.memory.mcpServers[server_name].model_dump()

    def get_all_mcpserver_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all server configurations.

        Returns:
            Dictionary of server configurations
        """
        servers = {}
        for server_name, server_config in self.memory.mcpServers.items():
            servers[server_name] = server_config.model_dump()
        return servers

    async def add_mcpserver_to_config(self,
                                      server_name: str,
                                      command: str,
                                      args: List[str],
                                      env: Optional[Dict[str, str]] = None,
                                      description: Optional[str] = None,
                                      disabled: Optional[bool] = False) -> bool:
        """
        Add or update a server configuration.

        This method only updates the configuration and does not affect the server process or cache.

        Args:
            server_name: The name of the server
            command: The command to execute
            args: Command line arguments
            env: Optional environment variables
            description: Optional server description
            disabled: Optional flag to disable the server

        Returns:
            True if the operation was successful, False otherwise
        """
        try:
            # Build server config dict
            server_config = {
                "command": command,
                "args": args,
                "env": env or {},
                "description": description or "",
                "disabled": disabled
            }
            # Convert to Pydantic model for type correctness
            self.memory.mcpServers[server_name] = McpServerConfigModel(**server_config)

            # Save to file
            success = await self.parent.main_config.save_config()
            if success:
                logger.info(f"💾 Server {server_name} configuration added successfully")
            return success
        except Exception as e:
            logger.error(f"Error adding server configuration: {str(e)}")
            return False

    async def load_mcpserver_config(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """
        Add multiple servers from a configuration object.

        Args:
            config: Dictionary in the format {"mcpServers": {"name": {...}}}

        Returns:
            Dictionary mapping server names to success status
        """
        results = {}

        if "mcpServers" not in config:
            logger.error("Invalid configuration format: 'mcpServers' key is missing")
            return results

        mcpservers_config = config["mcpServers"]
        if not isinstance(mcpservers_config, dict):
            logger.error("Invalid configuration format: 'mcpServers' must be an object")
            return results

        # Process each server in the configuration
        for mcpserver_name, mcpserver_config in mcpservers_config.items():
            # We will use model to validate the configuration
            try:
                McpServerConfigModel(**mcpserver_config)
            except Exception as e:
                logger.error(f"Invalid server configuration for {mcpserver_name}: {str(e)}")
                results[mcpserver_name] = False
                continue

            # Extract server configuration
            command = mcpserver_config["command"]
            args = mcpserver_config["args"]
            env = mcpserver_config.get("env", None)
            description = mcpserver_config.get("description", None)
            disabled = mcpserver_config.get("disabled", False)

            # Add server
            success = await self.add_mcpserver_to_config(mcpserver_name, command, args, env, description, disabled)
            results[mcpserver_name] = success

        return results

    async def delete_mcpserver_from_config(self, server_name: str) -> bool:
        """
        Delete a server configuration.

        Args:
            server_name: The name of the server to delete

        Returns:
            True if the server was deleted, False if it didn't exist or there was an error
        """
        try:
            # First reload the config to ensure we have the latest version
            await self.parent.main_config.load_config()

            # Remove from the actual Pydantic model, not just a dict
            if server_name in self.memory.mcpServers:
                del self.memory.mcpServers[server_name]
                # Save to file
                success = await self.parent.main_config.save_config()
                if success:
                    logger.info(f"Server {server_name} configuration deleted successfully")
                return success
            else:
                logger.warning(f"Server {server_name} not found in configuration")
                return False
        except Exception as e:
            logger.error(f"Error deleting server configuration: {str(e)}")
            return False

    def check_if_mcpserver_toolcache_exist(self, server_name: str) -> bool:
        """Check if cache file exists for a server."""
        cache_file = os.path.join(self._ensure_cache_dir(), f"{server_name}.json")
        logger.debug(f"🔍 Checking cache file: {cache_file}")
        return os.path.exists(cache_file)

    def load_mcpserver_toolcache(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Load cache for a server if exists."""
        cache_file = os.path.join(self._ensure_cache_dir(), f"{server_name}.json")
        logger.debug(f"✅ Confirming cache from: {cache_file}")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    async def save_mcpserver_toolcache(self, server_name: str, data: Dict[str, Any]) -> bool:
        """Save cache for a server, only if not exists."""
        cache_dir = self._ensure_cache_dir()
        cache_file = os.path.join(cache_dir, f"{server_name}.json")
        if os.path.exists(cache_file):
            logger.debug(f"Cache already exists for server {server_name}, skipping save.")
            return False
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                # Write pretty-formatted JSON
                json.dump(data, f, indent=2)
            logger.info(f"💾  Cache saved for server {server_name}.")
            return True
        except Exception as e:
            logger.error(f"Failed to save cache for server {server_name}: {e}")
            return False

    async def delete_mcpserver_toolcache(self, server_name: str) -> bool:
        """Delete cache for a server if exists."""
        cache_file = os.path.join(self._ensure_cache_dir(), f"{server_name}.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            logger.info(f"🗑️  Cache deleted for server {server_name}.")
            return True
        return False

    def _ensure_cache_dir(self) -> str:
        """Ensure cache directory exists and return its path."""
        cache_dir = os.path.join(os.path.dirname(self.parent.config_file_path), "cache")
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"📁 Cache directory created: {cache_dir}")
        return cache_dir
