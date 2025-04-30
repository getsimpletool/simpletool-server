"""
Private Server Management

This module provides the McpServerManagerPrivateServers class for managing
user-specific private server instances.
"""
import time
from typing import Dict, List, Any, Optional
from loguru import logger


class McpServerPrivateService:
    """
    Manages user-specific private server instances, including creation,
    management, and cleanup of idle servers.
    """

    def __init__(self, parent):
        self.parent = parent
        self.config_service = parent.config_service
        self.mcpservers = parent.mcpservers
        self.private_server_mapping = parent.private_server_mapping
        self.server_start_times = parent.server_start_times

    async def get_user_env_for_server(self, username: str, server_name: str) -> Optional[Dict[str, str]]:
        """
        Get user-specific environment variables for a server.

        Args:
            username: The username
            server_name: The server name

        Returns:
            Dictionary of environment variables or None if not defined
        """
        # Get user configuration
        user_config = self.config_service.users.get_user(username)
        if not user_config:
            return None

        # Check if user has server-specific environment variables
        server_env = user_config.get("serverEnv", {}).get(server_name)
        if server_env:
            return server_env

        # Check if user has global environment variables
        global_env = user_config.get("env")
        if global_env:
            return global_env

        return None

    async def get_server_timeout(self, username: str, server_name: str) -> int:
        """
        Get the timeout value for a private server instance.

        Args:
            username: The username
            server_name: The server name

        Returns:
            Timeout in seconds (default: 3600)
        """
        # Default timeout: 1 hour
        default_timeout = 3600

        # Get user configuration
        user_config = self.config_service.users.get_user(username)
        if not user_config:
            return default_timeout

        # Check if user has server-specific timeout
        server_timeout = user_config.get("serverTimeouts", {}).get(server_name)
        if server_timeout is not None:
            return server_timeout

        # Check if user has global timeout
        global_timeout = user_config.get("serverTimeout")
        if global_timeout is not None:
            return global_timeout

        return default_timeout

    async def get_private_server_name(self, username: str, server_name: str) -> str:
        """
        Generate a private server name for a user.

        Args:
            username: The username
            server_name: The base server name

        Returns:
            Private server name in the format {server_name}-{username}
        """
        return f"{server_name}-{username}"

    async def start_private_server(self, username: str, server_name: str) -> Dict[str, Any]:
        """
        Start a private server instance for a user.

        Args:
            username: The username
            server_name: The server name

        Returns:
            Status of the operation
        """
        logger.info(f"Starting private server for user {username} based on {server_name}")

        # Check if base server exists
        if server_name not in self.mcpservers:
            logger.warning(f"Base server '{server_name}' not found")
            return {"status": "error", "message": f"Base server '{server_name}' not found"}

        # Generate private server name
        private_server_name = await self.get_private_server_name(username, server_name)

        # Check if private server already exists
        if private_server_name in self.mcpservers:
            logger.info(f"Private server '{private_server_name}' already exists")
            return {"status": "success", "message": f"Private server '{private_server_name}' already exists"}

        try:
            # Get base server configuration
            base_server = self.mcpservers[server_name]
            command = base_server["command"]
            args = base_server["args"]
            env = base_server.get("env", {}).copy() if base_server.get("env") else {}
            description = f"Private {base_server.get('description', server_name)} for {username}"

            # Get user-specific environment variables
            user_env = await self.get_user_env_for_server(username, server_name)
            if user_env:
                # Merge user environment with base environment
                env.update(user_env)

            # Start the private server
            start_result = await self.parent.add_server(private_server_name, command, args, env, description)

            if start_result["status"] != "success":
                return start_result

            # Record start time for timeout tracking
            self.server_start_times[private_server_name] = time.time()

            # Update private server mapping for quick lookup
            if username not in self.private_server_mapping:
                self.private_server_mapping[username] = {}
            self.private_server_mapping[username][server_name] = private_server_name

            return {
                "status": "success",
                "message": f"Private server '{private_server_name}' started successfully",
                "metadata": start_result.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"Failed to start private server for user {username} based on {server_name}: {str(e)}")
            return {"status": "error", "message": f"Failed to start private server: {str(e)}"}

    async def stop_private_server(self, username: str, server_name: str) -> Dict[str, Any]:
        """
        Stop a private server instance for a user.

        Args:
            username: The username
            server_name: The server name

        Returns:
            Status of the operation
        """
        logger.info(f"Stopping private server for user {username} based on {server_name}")

        # Check if user has private servers
        if username not in self.private_server_mapping:
            logger.warning(f"No private servers found for user {username}")
            return {"status": "error", "message": f"No private servers found for user {username}"}

        # Check if user has a private server for this base server
        if server_name not in self.private_server_mapping[username]:
            logger.warning(f"No private server found for user {username} based on {server_name}")
            return {"status": "error", "message": f"No private server found for user {username} based on {server_name}"}

        # Get private server name
        private_server_name = self.private_server_mapping[username][server_name]

        try:
            # Stop the private server
            stop_result = await self.parent.stop_server(private_server_name)

            if stop_result["status"] != "success":
                return stop_result

            # Remove from private server mapping
            del self.private_server_mapping[username][server_name]
            if not self.private_server_mapping[username]:
                del self.private_server_mapping[username]

            # Remove from server start times
            if private_server_name in self.server_start_times:
                del self.server_start_times[private_server_name]

            return {
                "status": "success",
                "message": f"Private server '{private_server_name}' stopped successfully"
            }

        except Exception as e:
            logger.error(f"Failed to stop private server for user {username} based on {server_name}: {str(e)}")
            return {"status": "error", "message": f"Failed to stop private server: {str(e)}"}

    async def cleanup_idle_private_servers(self) -> Dict[str, Any]:
        """
        Clean up idle private server instances.

        Returns:
            Status of the operation with details of cleaned up servers
        """
        logger.info("Cleaning up idle private servers")
        results = {"status": "success", "cleaned_servers": []}
        current_time = time.time()

        # Collect private servers to clean up
        servers_to_clean = []
        for username, private_servers in self.private_server_mapping.items():
            for base_server_name, private_server_name in private_servers.items():
                # Check if server has a start time recorded
                if private_server_name not in self.server_start_times:
                    continue

                # Get server timeout
                timeout = await self.get_server_timeout(username, base_server_name)

                # Check if server has been idle for too long
                idle_time = current_time - self.server_start_times[private_server_name]
                if idle_time > timeout:
                    servers_to_clean.append((username, base_server_name, private_server_name, idle_time))

        logger.info(f"Found {len(servers_to_clean)} idle private servers to clean up")

        # Stop idle servers
        for username, base_server_name, private_server_name, idle_time in servers_to_clean:
            logger.info(f"Idle private server {private_server_name} (idle for {idle_time:.1f} seconds)")
            try:
                logger.info(f"Stopping idle private server {private_server_name} (idle for {idle_time:.1f} seconds)")
                stop_result = await self.stop_private_server(username, base_server_name)

                if stop_result["status"] == "success":
                    results["cleaned_servers"].append({
                        "username": username,
                        "server_name": base_server_name,
                        "private_server_name": private_server_name,
                        "idle_time": idle_time
                    })
                else:
                    logger.warning(f"Failed to stop idle private server {private_server_name}: {stop_result['message']}")

            except Exception as e:
                logger.error(f"Error cleaning up private server {private_server_name}: {str(e)}")

        # Update result status
        if not results["cleaned_servers"]:
            results["message"] = "No idle private servers to clean up"
        else:
            results["message"] = f"Cleaned up {len(results['cleaned_servers'])} idle private servers"

        return results

    async def list_user_servers(self, username: str) -> List[Dict[str, Any]]:
        """
        List private server instances for a specific user.

        Args:
            username: The username

        Returns:
            List of server metadata
        """
        result = []

        # Check if user has private servers
        if username not in self.private_server_mapping:
            return result

        # Get all private servers for this user
        for base_server_name, private_server_name in self.private_server_mapping[username].items():
            if private_server_name in self.mcpservers:
                server_data = self.mcpservers[private_server_name]

                # Get process status
                process = server_data.get("process")
                status = server_data.get("status", "unknown")

                if process and process.returncode is not None:
                    status = "stopped"

                # Calculate idle time
                idle_time = None
                if private_server_name in self.server_start_times:
                    idle_time = time.time() - self.server_start_times[private_server_name]

                # Create server metadata entry
                server_info = {
                    "name": private_server_name,
                    "base_server": base_server_name,
                    "description": server_data.get("description", ""),
                    "status": status,
                    "tools": server_data.get("tools", []),
                    "toolCount": len(server_data.get("tools", [])),
                    "idle_time": idle_time
                }

                result.append(server_info)

        return result
