"""
Tool Management

This module provides the McpServerManagerTools class for handling tool requests,
invocation, and related functionality for MCP servers.
"""
import json
import time
from typing import Dict, Any, Optional
from loguru import logger


class McpServerToolsService:
    """
    Manages tool requests, invocation, and related functionality for MCP servers.
    """

    def __init__(self, parent):
        self.parent = parent
        self.config_service = parent.config_service
        self.mcpservers = parent.mcpservers
        self.private_server_mapping = parent.private_server_mapping
        self.server_start_times = parent.server_start_times
        self.env_whitelist_tools = parent.env_whitelist_tools
        self.env_blacklist_tools = parent.env_blacklist_tools

    async def process_tool_request(self, method: str, params: Dict[str, Any], username: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a tool request from an MCP client.

        Args:
            method: The MCP method name (e.g., 'tools/list', 'tools/call')
            params: The parameters for the method
            username: Optional username for private server instances

        Returns:
            The result of processing the tool request
        """
        logger.info(f"Processing tool request: {method} with params: {params}")

        # Handle tools/list request
        if method == "tools/list":
            # Return list of all available tools
            tools = await self.parent.list_tools()
            return {"tools": tools}

        # Handle tools/call request
        elif method == "tools/call":
            # Check required parameters
            if "name" not in params:
                return {"error": {"code": -32602, "message": "Missing required parameter: name"}}

            tool_name = params["name"]
            arguments = params.get("arguments", {})

            # Invoke the tool
            result = await self.invoke_tool(tool_name, arguments, username)
            return result

        # Handle unknown method
        else:
            logger.warning(f"Unknown method: {method}")
            return {"error": {"code": -32601, "message": f"Method not found: {method}"}}

    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any], username: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a request to a tool and get its response.

        Args:
            tool_name: The name of the tool to invoke
            arguments: Parameters to send to the tool
            username: Optional username for private server instances

        Returns:
            Tool response or error
        """
        logger.info(f"Invoking tool: {tool_name} with params: {arguments}")

        # Find which server has this tool
        server_name = None
        for name, server_data in self.mcpservers.items():
            if "tools" in server_data and any(tool["name"] == tool_name for tool in server_data["tools"]):
                server_name = name
                break

        if not server_name:
            logger.warning(f"Tool '{tool_name}' not found in any server")
            return {"status": "error", "message": f"Tool '{tool_name}' not found in any server"}

        # Check if we need to use a private server instance
        if username:
            # Check if the user has environment variables for this server
            user_env = await self.parent.get_user_env_for_server(username, server_name)

            if user_env:
                # User has custom environment variables, use private server
                private_server_name = f"{server_name}-{username}"

                # Check if the private server is running
                if username not in self.private_server_mapping or server_name not in self.private_server_mapping[username]:
                    # Start the private server
                    logger.info(f"🚀 Starting private server '{private_server_name}' for user '{username}' 👤")
                    start_result = await self.parent.start_private_server(username, server_name)
                    if start_result.get("status") != "success":
                        logger.warning(f"❌ Failed to start private server: {start_result.get('message')}")
                        return start_result

                # Update the server name to the private server
                server_name = private_server_name
                logger.info(f"🔒 Using private server '{server_name}' for user '{username}' 🚀")

                # Update the server start time
                self.server_start_times[server_name] = time.time()

        server = self.mcpservers[server_name]
        # Lazy-start cached servers if not running
        if "process" not in server:
            logger.info(f"🐢 Lazy-starting server '{server_name}' for tool '{tool_name}'")
            # Use stored metadata to start process
            cmd = server.get("command")
            # Validate command type
            if not isinstance(cmd, str):
                logger.error(f"❌ Cannot lazy-start server '{server_name}': invalid command")
                return {"status": "error", "message": "Invalid server command"}
            args = server.get("args", [])
            # Validate args
            if not isinstance(args, list):
                args = []
            env = server.get("env")
            desc = server.get("description", "")
            start_res = await self.parent.start_mcpserver(server_name, cmd, args, env, desc)
            if start_res.get("status") != "success":
                logger.error(f"❌ Failed lazy-start server '{server_name}': {start_res.get('message')}")
                return start_res
            server = self.mcpservers[server_name]

        process = server["process"]

        try:
            # Check if process is still running
            if process.returncode is not None:
                logger.warning(f"Server '{server_name}' has exited, attempting to restart...")
                command = server["command"]
                args = server["args"]
                env = server.get("env", {})
                description = server.get("description", "")
                await self.parent.delete_mcpserver(server_name)
                await self.parent.start_mcpserver(server_name, command, args, env, description)
                process = self.mcpservers[server_name]["process"]

            # Prepare request with tool name according to MCP specification
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Log detailed request information
            logger.debug(f"Sending request to server '{server_name}' for tool '{tool_name}':")
            logger.debug(f"Request payload: {json.dumps(request, indent=2)}")

            # Send request to stdin
            request_str = json.dumps(request) + "\n"
            process.stdin.write(request_str.encode())
            await process.stdin.drain()

            # Read response from stdout
            response_line = await process.stdout.readline()
            if not response_line:
                logger.warning(f"No response from server '{server_name}' for tool '{tool_name}'")
                return {"status": "error", "message": "No response from server"}

            # Parse JSON response
            try:
                response = json.loads(response_line)
                logger.debug(f"Received response from server '{server_name}' for tool '{tool_name}':")
                logger.debug(f"Response payload: {json.dumps(response, indent=2)}")

                # Check if response is valid
                if "jsonrpc" not in response:
                    logger.warning(f"Invalid JSON-RPC response from server '{server_name}'")
                    return {"status": "error", "message": "Invalid JSON-RPC response"}

                # Check for JSON-RPC errors and propagate them directly
                if "error" in response:
                    error = response["error"]
                    logger.warning(f"Error in response from server '{server_name}': {error}")
                    # Return raw JSON-RPC error for 1:1 mapping
                    return {"error": error}

                # Return the full response object
                if "result" in response:
                    return response
                else:
                    logger.warning(f"Missing 'result' in response from server '{server_name}'")
                    return {"status": "error", "message": "Missing 'result' in response"}

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse response from server '{server_name}': {str(e)}")
                return {"status": "error", "message": f"Invalid JSON response: {str(e)}"}

        except Exception as e:
            logger.error(f"Error invoking tool '{tool_name}' on server '{server_name}': {str(e)}")
            return {"status": "error", "message": f"Error invoking tool: {str(e)}"}
