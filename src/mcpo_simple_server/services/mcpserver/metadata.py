"""
Server Metadata Management

This module provides the McpServerManagerMetadata class for fetching and managing
metadata for MCP servers and tools.
"""
import json
import asyncio
from typing import Dict, List, Any
from loguru import logger


class McpServerMetadataService:
    """
    Manages metadata for MCP servers and tools, including fetching server metadata
    and listing available servers and tools.
    """

    def __init__(self, parent):
        self.parent = parent
        self.config_service = parent.config_service
        self.mcpservers = parent.mcpservers
        self.private_server_mapping = parent.private_server_mapping
        self.env_whitelist_tools = parent.env_whitelist_tools
        self.env_blacklist_tools = parent.env_blacklist_tools

    async def fetch_server_metadata(self, name: str) -> Dict[str, Any]:
        """
        Fetch metadata from an MCP server using the tools/list protocol.

        Args:
            name: The name of the server to fetch metadata for

        Returns:
            Dictionary with status and metadata if successful
        """
        logger.info(f"Fetching metadata for server: {name}")
        if name not in self.mcpservers:
            logger.warning(f"Server '{name}' not found")
            return {"status": "error", "message": f"Server '{name}' not found"}

        try:
            server_data = self.mcpservers[name]
            process = server_data["process"]

            # Check if process is still running
            if process.returncode is not None:
                logger.warning(f"Server {name} is not running (exit code: {process.returncode})")
                return {"status": "error", "message": f"Server '{name}' is not running"}

            # First, send the initialized notification according to MCP protocol
            init_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }

            # Send initialization notification
            init_request_str = json.dumps(init_request) + "\n"
            logger.debug(f"Sending initialization notification to {name}: {str(init_request_str)}")
            process.stdin.write(init_request_str.encode())
            await process.stdin.drain()

            # Wait a moment for the server to process the initialization
            await asyncio.sleep(0.5)

            # Prepare tools/list request according to MCP protocol
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            # Send request to stdin
            request_str = json.dumps(request) + "\n"
            logger.debug(f"Sending tools/list request to {name}: {str(request_str)}")
            process.stdin.write(request_str.encode())
            await process.stdin.drain()

            # Read response from stdout
            response_line = await process.stdout.readline()

            if not response_line:
                logger.warning(f"Empty response from server {name}")
                return {"status": "error", "message": "Empty response from server"}

            # Parse JSON response
            try:
                response = json.loads(response_line)

                # Check if response is valid
                if "jsonrpc" not in response or "result" not in response:
                    logger.warning(f"Invalid JSON-RPC response from server {name}")
                    return {"status": "error", "message": "Invalid JSON-RPC response"}
                else:
                    logger.debug(f"Received response from {name}:\n{json.dumps(response, indent=4)}")

                # Extract tools from response
                tools_data = response.get("result", {}).get("tools", [])
                next_cursor = response.get("result", {}).get("nextCursor")

                # Handle pagination if needed
                while next_cursor:
                    # Prepare next request with cursor
                    cursor_request = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                        "params": {"cursor": next_cursor}
                    }

                    # Send request
                    cursor_request_str = json.dumps(cursor_request) + "\n"
                    logger.debug(f"Sending paginated tools/list request to {name}: {str(cursor_request_str)}")
                    process.stdin.write(cursor_request_str.encode())
                    await process.stdin.drain()

                    # Read response
                    cursor_response_line = await process.stdout.readline()

                    if not cursor_response_line:
                        logger.warning(f"Empty paginated response from server {name}")
                        break

                    # Parse response
                    cursor_response = json.loads(cursor_response_line)
                    logger.debug(f"Received paginated response from {name}:\n{json.dumps(cursor_response, indent=4)}")

                    # Add tools to the list
                    cursor_tools = cursor_response.get("result", {}).get("tools", [])
                    tools_data.extend(cursor_tools)

                    # Update cursor
                    next_cursor = cursor_response.get("result", {}).get("nextCursor")

                # Filter tools based on whitelist and blacklist
                filtered_tools = self.filter_tools(tools_data)

                # Update server metadata
                self.mcpservers[name]["tools"] = filtered_tools
                self.mcpservers[name]["status"] = "running"

                # Generate server description that lists the tools it contains
                if not self.mcpservers[name].get("description"):
                    tool_names = [str(tool.get("name", "")) for tool in filtered_tools]
                    tools_list = ", ".join(tool_names)
                    self.mcpservers[name]["description"] = f"Server '{name}' containing {len(filtered_tools)} tools: {tools_list}"

                return {
                    "status": "success",
                    "message": f"Metadata fetched successfully for server '{name}'",
                    "tools": filtered_tools
                }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse response from server {name}: {str(e)}")
                return {"status": "error", "message": f"Invalid response from server: {str(e)}"}

        except Exception as e:
            logger.error(f"Failed to fetch metadata for server {name}: {str(e)}")
            return {"status": "error", "message": f"Failed to fetch metadata: {str(e)}"}

    def filter_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter tools based on whitelist and blacklist configurations.

        Args:
            tools: List of tool metadata to filter

        Returns:
            Filtered list of tools
        """
        filtered_tools = []
        for tool in tools:
            tool_name = tool.get("name", "")

            # Skip if tool doesn't have a name
            if not tool_name:
                continue

            # Check environment variable whitelist
            if self.env_whitelist_tools and tool_name not in self.env_whitelist_tools:
                logger.info(f"Skipping tool '{tool_name}' (not in TOOLS_WHITELIST environment variable)")
                continue

            # Check environment variable blacklist
            if self.env_blacklist_tools and tool_name in self.env_blacklist_tools:
                logger.info(f"Skipping tool '{tool_name}' (in TOOLS_BLACKLIST environment variable)")
                continue

            # Check config file blacklist
            if self.config_service and self.config_service.tools and self.config_service.tools.is_tool_blacklisted(tool_name):
                logger.info(f"Skipping tool '{tool_name}' (in blacklist from config file)")
                continue

            # Check config file whitelist
            whitelist = []
            if self.config_service and self.config_service.tools:
                whitelist = self.config_service.tools.get_whitelist()

            if whitelist and tool_name not in whitelist:
                logger.info(f"Skipping tool '{tool_name}' (not in whitelist from config file)")
                continue

            # Tool passed all filters
            filtered_tools.append(tool)

        # Log filtering summary
        if len(filtered_tools) != len(tools):
            logger.info(f"Filtered from {len(tools)} to {len(filtered_tools)} tools based on filtering rules")

        return filtered_tools

    async def list_servers(self) -> List[Dict[str, Any]]:
        """
        List all servers with their metadata.

        Returns:
            List of server metadata
        """
        result = []

        for server_name, server_data in self.mcpservers.items():
            # Skip private servers when listing all servers
            if "-" in server_name and any(server_name in private_servers.values()
                                          for private_servers in self.private_server_mapping.values()):
                continue

            # Get process status
            process = server_data.get("process")
            status = server_data.get("status", "unknown")

            if process and process.returncode is not None:
                status = "stopped"

            # Create server metadata entry
            server_info = {
                "name": server_name,
                "description": server_data.get("description", ""),
                "status": status,
                "tools": server_data.get("tools", []),
                "toolCount": len(server_data.get("tools", []))
            }

            result.append(server_info)

        return result

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools across all running servers.

        Returns:
            List of tool metadata
        """
        all_tools = []

        for server_name, server_data in self.mcpservers.items():
            # Skip servers that aren't running
            process = server_data.get("process")
            if process and process.returncode is not None:
                continue

            # Get tools from this server
            server_tools = server_data.get("tools", [])

            # Add server name to each tool metadata
            for tool in server_tools:
                tool_copy = tool.copy()
                tool_copy["server"] = server_name
                all_tools.append(tool_copy)

        return all_tools

    async def get_tool_metadata(self, tool_name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific tool.

        Args:
            tool_name: The name of the tool

        Returns:
            Tool metadata or error if not found
        """
        for server_name, server_data in self.mcpservers.items():
            for tool in server_data.get("tools", []):
                if tool.get("name") == tool_name:
                    # Add server name to tool metadata
                    tool_with_server = tool.copy()
                    tool_with_server["server"] = server_name
                    return {
                        "status": "success",
                        "tool": tool_with_server
                    }

        return {
            "status": "error",
            "message": f"Tool '{tool_name}' not found"
        }
