"""
MCP Server Manager Module

This module provides the McpServerManager class for managing MCP servers,
including server lifecycle, tool management, and private server instances.
"""
from .lifecycle import McpServerLifecycleService
from .private import McpServerPrivateService
from .metadata import McpServerMetadataService
from .tools import McpServerToolsService
import os


class McpServerService:
    """
    Combined MCP Server Manager that provides all functionality for managing MCP servers.
    This class owns all shared state and delegates to specialized managers for lifecycle, metadata, tools, and private server management.
    """

    def __init__(self, config_service=None, config_path=None):
        self.config_service = config_service
        self.config_path = config_path

        # Keep status of mcpServers
        self.mcpservers = {}
        self.private_server_mapping = {}
        self.server_start_times = {}

        # Keep status of tools
        self.env_whitelist_tools = self._parse_env_list("TOOLS_WHITELIST")
        self.env_blacklist_tools = self._parse_env_list("TOOLS_BLACKLIST")

        # Instantiate sub-managers, passing self as parent
        self.lifecycle = McpServerLifecycleService(self)
        self.private_servers = McpServerPrivateService(self)
        self.metadata = McpServerMetadataService(self)
        self.tools = McpServerToolsService(self)

        # Optionally, forward core methods for compatibility
        self.initialize = self.lifecycle.initialize
        self.add_new_mcpserver_config = self.lifecycle.add_new_mcpserver_config
        self.add_mcpserver = self.lifecycle.add_mcpserver
        self.delete_mcpserver = self.lifecycle.delete_mcpserver

        self.start_mcpserver = self.lifecycle.start_mcpserver
        self.start_all_mcpservers = self.lifecycle.start_all_mcpservers
        self.stop_mcpserver = self.lifecycle.stop_mcpserver
        self.stop_all_mcpservers = self.lifecycle.stop_all_mcpservers
        self.restart_mcpserver = self.lifecycle.restart_mcpserver
        self.restart_all_mcpservers = self.lifecycle.restart_all_mcpservers

        self.fetch_server_metadata = self.lifecycle.fetch_server_metadata

        self.list_mcpservers = self.lifecycle.list_mcpservers

        # Metadata methods
        self.list_tools = self.metadata.list_tools

        # Delegate private server methods
        self.start_private_server = self.private_servers.start_private_server
        self.stop_private_server = self.private_servers.stop_private_server
        self.cleanup_idle_private_servers = self.private_servers.cleanup_idle_private_servers
        self.list_user_servers = self.private_servers.list_user_servers
        # Tool invocation
        self.process_tool_request = self.tools.process_tool_request
        self.invoke_tool = self.tools.invoke_tool

    def _parse_env_list(self, env_var_name: str):
        env_var = os.getenv(env_var_name, "")
        if not env_var:
            return []
        return [item.strip() for item in env_var.split(",") if item.strip()]


__all__ = ["McpServerService"]
