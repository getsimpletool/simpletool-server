"""
Server Lifecycle Management

This module provides the McpServerManagerLifecycle class for handling server
lifecycle operations such as starting, stopping, and reloading servers.
"""
import asyncio
import os
import json
from typing import Dict, List, Any, Optional
from loguru import logger

from mcpo_simple_server.services.config import ConfigService


class McpServerLifecycleService:
    """
    Manages server lifecycle operations such as starting, stopping, and reloading servers.
    Also includes methods for initialization, loading, and saving configurations.
    """

    def __init__(self, parent):
        self.parent = parent
        # For compatibility, expose shared state
        self.config_service: ConfigService = parent.config_service
        self.mcpservers = parent.mcpservers
        self.private_server_mapping = parent.private_server_mapping
        self.server_start_times = parent.server_start_times
        self.env_whitelist_tools = parent.env_whitelist_tools
        self.env_blacklist_tools = parent.env_blacklist_tools

    @property
    def cfg(self) -> ConfigService:
        """Access the non-optional config manager or raise if missing."""
        if self.config_service is None:
            logger.error("Config manager not provided")
            raise ValueError("Config manager not provided")
        return self.config_service

    async def initialize(self):
        """Initialize the server manager by loading config and starting all servers."""
        logger.info("Initializing McpServerManager with config manager")
        try:
            # Load configuration
            await self.cfg.main_config.load_config()

            # Log tools configuration from file
            whitelist = self.cfg.tools.get_whitelist()
            blacklist = self.cfg.tools.get_blacklist()

            if whitelist:
                logger.info(f"Tools whitelist from config file: {', '.join(whitelist)}")
            if blacklist:
                logger.info(f"Tools blacklist from config file: {', '.join(blacklist)}")

            # Initialize servers: start new or load from cache
            servers_cfg = self.cfg.mcpserver.get_all_mcpserver_configs()
            for name, srv_cfg in servers_cfg.items():
                if srv_cfg.get("disabled", False):
                    logger.info(f"Skipping disabled server: {name}")
                    continue

                if self.cfg.mcpserver.check_if_mcpserver_toolcache_exist(name):
                    cache_data = self.cfg.mcpserver.load_mcpserver_toolcache(name) or {}
                    tools = cache_data.get("tools", [])
                    # Mimic server setup without starting process; store metadata for lazy start
                    entry = {
                        "tools": tools,
                        "command": srv_cfg["command"],
                        "args": srv_cfg["args"],
                        "env": srv_cfg.get("env"),
                        "description": srv_cfg.get("description", "")
                    }
                    self.mcpservers[name] = entry
                    logger.info(f"🔧 Loaded server '{name}' from cache with {len(tools)} tools")
                else:
                    # First run: start process and fetch metadata
                    start_res = await self.add_mcpserver(
                        name, srv_cfg["command"], srv_cfg["args"],
                        srv_cfg.get("env"), srv_cfg.get("description")
                    )
                    if start_res.get("status") != "success":
                        logger.error(f"Failed to start server '{name}': {start_res.get('message')}")
                        continue

                    resp = await self.fetch_server_metadata(name)
                    if resp.get("status") == "success":
                        logger.info(f"Successfully fetched metadata for server: {name}")
                        self.mcpservers[name]["status"] = "running"
                        # Save metadata cache for faster startup
                        await self.cfg.mcpserver.save_mcpserver_toolcache(name, {"tools": resp.get("tools", [])})
                        logger.info(f"Cache saved for server: {name}")
                    else:
                        logger.warning(f"Could not fetch metadata for {name}: {resp.get('message')}")

            logger.info("McpServerManager initialization completed successfully")
        except Exception as e:
            logger.error(f"Failed to initialize McpServerManager: {str(e)}")
            raise

    async def add_new_mcpserver_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add new mcpServers configuration to config.json.

        Args:
            config: Dictionary in the format {"mcpServers": {"name": {...}}}

        Returns:
            Status and metadata for each added server
        """
        results = {"status": "success", "servers": {}}

        if "mcpServers" not in config:
            return {"status": "error", "message": "Invalid configuration format, missing 'mcpServers' key"}

        for server_name, server_config in config["mcpServers"].items():
            try:
                # Skip disabled servers
                if server_config.get("disabled", False):
                    results["servers"][server_name] = {
                        "status": "skipped",
                        "message": "Server is disabled in configuration"
                    }
                    continue

                command = server_config.get("command")
                args = server_config.get("args", [])
                env = server_config.get("env")
                description = server_config.get("description")

                if not command:
                    results["servers"][server_name] = {
                        "status": "error",
                        "message": "Missing required 'command' in server configuration"
                    }
                    continue

                # Add the server
                add_result = await self.add_mcpserver(server_name, command, args, env, description)
                results["servers"][server_name] = add_result

                # If any server fails, mark the overall status as partial
                if add_result["status"] != "success":
                    results["status"] = "partial"

            except Exception as e:
                results["servers"][server_name] = {
                    "status": "error",
                    "message": f"Failed to add server: {str(e)}"
                }
                results["status"] = "partial"

        return results

    async def add_mcpserver(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Add and start a new server subprocess.

        Args:
            name: The name of the server
            command: The command to execute
            args: Command line arguments
            env: Optional environment variables to pass to the subprocess
            description: Optional description of the server

        Returns:
            Server metadata including status
        """
        logger.info(f"Adding server: {name} with command: {command} {' '.join(args)}")
        # Check if server already exists
        if name in self.mcpservers:
            return {"status": "error", "message": f"Server '{name}' already exists"}

        # Ensure config manager is available before proceeding
        if self.config_service is None:
            logger.error("No config manager provided; cannot add server")
            return {"status": "error", "message": "Internal error: config manager not provided"}

        try:
            start_result = await self.start_mcpserver(name, command, args, env, description)
            if start_result["status"] != "success":
                return start_result

            # Update config using the config manager
            server_description = self.mcpservers[name].get("description", "")
            await self.config_service.mcpserver.add_mcpserver_to_config(name, command, args, env, server_description)

            return {
                "status": "success",
                "message": f"Server '{name}' added successfully",
                "metadata": {
                    "name": name,
                    "description": self.mcpservers[name].get("description", ""),
                    "tools": self.mcpservers[name].get("tools", []),
                    "status": self.mcpservers[name].get("status", "unknown")
                }
            }

        except Exception as e:
            logger.error(f"Failed to add server {name}: {str(e)}")
            return {"status": "error", "message": f"Failed to add server: {str(e)}"}

    async def start_mcpserver(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a server subprocess with the given configuration.

        Args:
            name: The name of the server
            command: The command to execute
            args: Command line arguments
            env: Optional environment variables to pass to the subprocess
            description: Optional description of the server

        Returns:
            Dictionary with status and metadata if successful, error otherwise
        """
        logger.info(f"Starting server: {name} with command: {command}")

        # Check if server already exists
        if name in self.mcpservers and self.mcpservers[name].get("process"):
            process = self.mcpservers[name]["process"]
            if process.returncode is None:
                logger.info(f"Server {name} is already running")
                return {
                    "status": "success",
                    "message": f"Server '{name}' is already running",
                    "metadata": self.mcpservers[name]
                }

        try:
            # Replace 'uvx' with 'uv' and handle different command formats
            final_command = command
            final_args = args.copy()

            if command == "uvx":
                final_command = "uv"

                if len(args) > 0:
                    module_name = args[0]
                    if len(args) > 1:
                        final_args = ["tool", "run", module_name] + args[1:]
                    else:
                        # If there are no arguments after the module name
                        final_args = ["tool", "run", module_name]
                    logger.info(f"Converting command for {name}: 'uvx {' '.join(args)}' to 'uv {' '.join(final_args)}'")

            # Handle uvx as the first part of the command string
            elif command.startswith("uvx "):
                new_command = "uv run " + command[4:]
                logger.info(f"Converting command for {name}: '{command}' to '{new_command}'")
                final_command = new_command
                final_args = []

            # Prepare environment variables
            process_env = None
            if env:
                # Start with current environment
                process_env = os.environ.copy()
                # Add or override with provided environment variables
                for key, value in env.items():
                    process_env[key] = value
                logger.info(f"Setting environment variables for server {name}: {', '.join(list(env.keys()))}")

            # Get subprocess stream limit from env, default 5MB
            stream_limit = int(os.getenv("SUBPROCESS_STREAM_LIMIT", str(5 * 1024 * 1024)))

            # Start the subprocess
            process = await asyncio.create_subprocess_exec(
                final_command,
                *final_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                limit=stream_limit
            )

            # Store server metadata and process
            server_info = {
                "name": name,
                "command": command,  # Store original command for config
                "args": args,        # Store original args for config
                "process": process,
                "pid": process.pid,  # Store the process PID
                "description": description or f"{name} server",
                "tools": [],
                "status": "initializing",
                "env": env           # Store environment variables
            }

            self.mcpservers[name] = server_info

            # Ensure config manager is available for retrieving stored config
            if self.config_service is None:
                logger.error("No config manager provided; cannot retrieve server config")
                raise ValueError("Internal error: config manager not provided")
            config_mgr = self.config_service

            # Check if there's a description in the config
            server_config = config_mgr.mcpserver.get_mcpserver_config(name)
            if server_config and "description" in server_config:
                self.mcpservers[name]["description"] = server_config["description"]
            elif description:
                self.mcpservers[name]["description"] = description

            # Fetch metadata from the MCP server
            metadata_result = await self.fetch_server_metadata(name)

            if metadata_result["status"] == "success":
                logger.info(f"Successfully fetched metadata for server: {name}")
                self.mcpservers[name]["status"] = "running"
                # Save metadata cache for faster startup
                await self.cfg.mcpserver.save_mcpserver_toolcache(name, {"tools": metadata_result.get("tools", [])})
                logger.info(f"Cache saved for server: {name}")
            else:
                logger.warning(f"Failed to fetch metadata for server {name}: {metadata_result.get('message')}")
                self.mcpservers[name]["status"] = "error"

            return {
                "status": "success",
                "message": f"Server '{name}' started successfully",
                "metadata": self.mcpservers[name]
            }
        except Exception as e:
            logger.error(f"Failed to start server {name}: {str(e)}")
            return {"status": "error", "message": f"Failed to start server: {str(e)}"}

    async def fetch_server_metadata(self, name: str) -> Dict[str, Any]:
        """
        Fetch metadata from an MCP server using the tools/list protocol.
        This is a simplified implementation to avoid circular imports.

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
                logger.warning(f"Server {name} is not running (exit code: {str(process.returncode)})")
                return {"status": "error", "message": f"Server '{name}' is not running"}

            # First, send the initialized notification according to MCP protocol
            init_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }

            # Send initialization notification
            init_request_str = json.dumps(init_request) + "\n"
            logger.debug(f"Sending initialization notification to {name}:\n{json.dumps(init_request, indent=4)}")
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
            logger.debug(f"Sending tools/list request to {name}:\n{json.dumps(request, indent=4)}")
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
                    logger.debug(f"Sending paginated tools/list request to {name}:\n{json.dumps(cursor_request, indent=4)}")
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
                filtered_tools = []
                for tool in tools_data:
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
                    if self.cfg.tools.is_tool_blacklisted(tool_name):
                        logger.info(f"Skipping tool '{tool_name}' (in blacklist from config file)")
                        continue

                    # Check config file whitelist
                    whitelist = self.cfg.tools.get_whitelist()
                    if whitelist and tool_name not in whitelist:
                        logger.info(f"Skipping tool '{tool_name}' (not in whitelist from config file)")
                        continue

                    # Tool passed all filters
                    filtered_tools.append(tool)

                # Log filtering summary
                if len(filtered_tools) != len(tools_data):
                    logger.info(f"Filtered from {len(tools_data)} to {len(filtered_tools)} tools based on filtering rules")

                # Update server metadata
                self.mcpservers[name]["tools"] = filtered_tools
                logger.info(f"🔧 Server {name} has {len(filtered_tools)} tools")

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

    async def stop_mcpserver(self, name: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Stop a running server subprocess.

        Args:
            name: The name of the server to stop
            timeout: Timeout in seconds to wait for the process to terminate

        Returns:
            Dictionary with status and message
        """
        logger.info(f"Stopping server: {name}")

        if name not in self.mcpservers:
            logger.warning(f"Server '{name}' not found")
            return {"status": "error", "message": f"Server '{name}' not found"}

        try:
            # Get the process
            process = self.mcpservers[name]["process"]
            logger.debug(f"Server {name} process: {process}")

            # Check if process has already exited
            if process.returncode is not None:
                logger.info(f"Server {name} already stopped (exit code: {str(process.returncode)})")
                return {"status": "success", "message": f"Server '{name}' already stopped"}

            # Try to terminate the process gracefully
            try:
                process.terminate()
            except ProcessLookupError:
                # Process doesn't exist anymore
                logger.info(f"Server {name} process already gone")
                return {"status": "success", "message": f"Server '{name}' process already gone"}
            except Exception as e:
                logger.warning(f"Error terminating server {name}: {str(e)} + ', will try force kill")
                # Continue to force kill

            # Wait for process to terminate
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
                logger.info(f"Server {name} stopped successfully")
                return {"status": "success", "message": f"Server '{name}' stopped"}
            except asyncio.TimeoutError:
                # Force kill if termination takes too long
                logger.warning(f"Timeout waiting for server {name} to terminate, force killing")
                try:
                    process.kill()
                    await process.wait()  # No timeout here, kill should be immediate
                    logger.info(f"Server {name} force killed successfully")
                    return {"status": "success", "message": f"Server '{name}' force killed"}
                except Exception as e:
                    logger.error(f"Failed to force kill server {name}: {str(e)}")
                    # Continue to return error

        except Exception as e:
            logger.error(f"Failed to stop server {name}: {str(e)}")

        # If we reach here, something went wrong but we don't want to crash the application
        # Just log the error and continue with shutdown
        return {"status": "error", "message": f"Failed to stop server: {name}"}

    async def delete_mcpserver(self, name: str) -> Dict[str, Any]:
        """
        Stop and delete a server.

        Args:
            name: The name of the server to delete

        Returns:
            Status of the operation
        """
        logger.info(f"Delete server: {name}")
        if name not in self.mcpservers:
            logger.warning(f"Server '{name}' not found")
            return {"status": "error", "message": f"Server '{name}' not found"}

        try:
            # Check if server is actually running before trying to stop it
            server_data = self.mcpservers[name]
            process = server_data.get("process")

            # Only try to stop if it's actually running
            if process and (process.returncode is None):
                logger.info(f"Stopping server: {name}")
                stop_result = await self.stop_mcpserver(name)
                if stop_result["status"] != "success":
                    # Log the error but continue with deletion
                    logger.warning(f"Failed to stop server {name}: {stop_result.get('message')}. Continuing with removal...")
            else:
                logger.info(f"Server {name} is not running, skipping stop operation")

            # Remove from servers dict
            if name in self.mcpservers:
                del self.mcpservers[name]

            # Check if it exists in server_start_times
            if name in self.server_start_times:
                del self.server_start_times[name]

            # Check and remove from private_server_mapping
            for username, private_servers in list(self.private_server_mapping.items()):
                if name in private_servers.values():
                    # Find the key for this server
                    for server_key, server_name in list(private_servers.items()):
                        if server_name == name:
                            del private_servers[server_key]
                    # If user has no more private servers, remove the entry
                    if not private_servers:
                        del self.private_server_mapping[username]

            # Update config using the config manager
            await self.cfg.mcpserver.delete_mcpserver_from_config(name)
            await self.cfg.mcpserver.delete_mcpserver_toolcache(name)

            # Force reload config to ensure it's updated everywhere
            await self.cfg.main_config.load_config()

            logger.info(f"Server '{name}' deleted successfully from config and cache")
            return {"status": "success", "message": f"Server '{name}' deleted"}
        except Exception as e:
            logger.error(f"Failed to delete server {name}: {str(e)}")
            return {"status": "error", "message": f"Failed to delete server: {name}"}

    async def restart_mcpserver(self, name: str) -> Dict[str, Any]:
        """
        Restart a specific server.

        Args:
            name: The name of the server to restart

        Returns:
            Status of the operation
        """
        logger.info(f"Restarting server: {name}")
        if name not in self.mcpservers:
            logger.warning(f"Server '{name}' not found")
            return {"status": "error", "message": f"Server '{name}' not found"}

        try:
            # First reload the configuration from file to get the latest settings
            await self.cfg.main_config.load_config()

            # Get the latest configuration from file
            server_config = self.cfg.mcpserver.get_mcpserver_config(name)
            if not server_config:
                logger.warning(f"Server '{name}' not found in configuration file")
                # Fall back to in-memory configuration if not found in file
                server_data = self.mcpservers[name]
                command = server_data["command"]
                args = server_data["args"]
                env = server_data.get("env")
                description = server_data.get("description", "")
            else:
                # Use configuration from file
                command = server_config["command"]
                args = server_config["args"]
                env = server_config.get("env")
                description = server_config.get("description", "")

            # Stop the server
            stop_result = await self.stop_mcpserver(name)
            if stop_result["status"] != "success":
                logger.warning(f"Failed to stop server {name} during reload: {stop_result['message']}")
                # Continue with restart even if stop failed

            # Start the server with the updated configuration
            start_result = await self.start_mcpserver(name, command, args, env, description)
            if start_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Failed to restart server {name}: {start_result['message']}"
                }

            # Return a clean, serializable response without any asyncio objects
            logger.info(f"Server '{name}' restarted successfully")
            return {
                "status": "success",
                "message": f"Server '{name}' restarted successfully",
                "server_name": name,
                "tool_count": len(self.mcpservers.get(name, {}).get("tools", []))
            }

        except Exception as e:
            logger.error(f"Failed to restart server {name}: {str(e)}")
            return {"status": "error", "message": f"Failed to restart server: {name}"}

    async def start_all_mcpservers(self):
        """
        Start all servers defined in the configuration.
        """
        logger.info("Starting all servers")
        servers_config = self.cfg.mcpserver.get_all_mcpserver_configs()

        # Log summary of enabled/disabled servers
        enabled_servers = [name for name, config in servers_config.items()
                           if not config.get("disabled", False)]
        disabled_servers = [name for name, config in servers_config.items()
                            if config.get("disabled", False)]

        logger.info(f"Found {len(enabled_servers)} enabled servers: {', '.join(enabled_servers) if enabled_servers else 'none'}")
        if disabled_servers:
            logger.info(f"Found {len(disabled_servers)} disabled servers that will be skipped: {', '.join(disabled_servers)}")

        for server_name, server_config in servers_config.items():
            try:
                # Skip disabled servers
                if server_config.get("disabled", False):
                    logger.info(f"Skipping disabled server: {server_name}")
                    continue

                # Get environment variables from configuration if they exist
                env = server_config.get("env")
                await self.add_mcpserver(server_name, server_config["command"], server_config["args"], env, server_config.get("description"))
                logger.info(f"Successfully initialized server: {server_name}")
            except Exception as e:
                logger.error(f"Failed to start server {server_name}: {str(e)}")

    async def stop_all_mcpservers(self) -> Dict[str, Any]:
        """
        Stop all running server processes.

        Returns:
            Dictionary with status and results for each server
        """
        logger.info("Stopping all servers")
        results = {"status": "success", "servers": {}}

        for server_name in list(self.mcpservers.keys()):
            try:
                stop_result = await self.stop_mcpserver(server_name)
                results["servers"][server_name] = stop_result

                # If any server fails to stop, mark the overall status as partial
                if stop_result["status"] != "success":
                    results["status"] = "partial"

            except Exception as e:
                logger.error(f"Error stopping server {server_name}: {str(e)}")
                results["servers"][server_name] = {
                    "status": "error",
                    "message": f"Exception during stop: {str(e)}"
                }
                results["status"] = "partial"

        return results

    async def restart_all_mcpservers(self) -> Dict[str, Any]:
        """
        Restart all MCP servers based on the current configuration file.
        This will stop all running MCP servers, reload the configuration, and start MCP servers based on the updated config.

        Returns:
            Dictionary with status and results of the operation
        """
        logger.info("Restarting all MCP servers")
        results = {"status": "success", "servers": {}}

        # First stop all running servers
        stop_results = await self.stop_all_mcpservers()
        results["stop_results"] = stop_results

        # Reload configuration from file
        try:
            await self.cfg.main_config.load_config()
            logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to reload configuration: {str(e)}",
                "stop_results": stop_results
            }

        # Start all servers based on updated configuration
        try:
            await self.start_all_mcpservers()
            logger.info("All servers restarted successfully")
        except Exception as e:
            logger.error(f"Failed to restart servers: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to restart servers: {str(e)}",
                "stop_results": stop_results
            }

        # Get updated server list
        server_list = await self.list_mcpservers()
        results["servers"] = {server["name"]: {"status": "success", "metadata": server} for server in server_list}

        return results

    async def list_mcpservers(self) -> List[Dict[str, Any]]:
        """
        List all MCP servers with their metadata.
        This is a simplified implementation to avoid circular imports.

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
