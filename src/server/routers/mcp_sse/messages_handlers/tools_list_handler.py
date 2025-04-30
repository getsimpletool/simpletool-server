"""
Tools List Message Handler

Handles the 'tools/list' request from MCP clients.
"""

from typing import Dict, Any
from loguru import logger

from server.services.mcpserver import McpServerService
from services.sse_transport import SseTransport
from .utils import check_client_initialized, send_sse_response


async def handle_tools_list(
    session_id: str,
    message: Dict[str, Any],
    sse_transport: SseTransport,
    server_manager: McpServerService
) -> Dict[str, Any]:
    """
    Handle the 'tools/list' request from a client.

    This request is sent by the client to get a list of available tools.

    Args:
        session_id: The session ID for the client
        message: The JSON-RPC message from the client
        sse_transport: The SSE transport instance
        server_manager: The server manager instance

    Returns:
        The JSON-RPC response to send back to the client
    """
    logger.info(f"Handling tools/list request from client {session_id}")

    # Check if client is initialized
    is_initialized, error_response = check_client_initialized(
        sse_transport,
        session_id,
        message.get("id")
    )

    if not is_initialized and error_response is not None:
        # Send error through SSE as well
        await send_sse_response(
            sse_transport,
            session_id,
            error_response,
            "client not initialized error"
        )
        return error_response

    try:
        # Get the list of tools from the server manager
        # This follows the MCP specification for tools/list response
        tools = await server_manager.list_tools()

        # Format the tools according to MCP specification
        formatted_tools = []
        for tool in tools:
            formatted_tool = {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {})
            }
            formatted_tools.append(formatted_tool)

        # Create the response according to MCP specification
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "tools": formatted_tools
            }
        }

        logger.debug(f"Sending tools/list response to client {session_id} with {len(formatted_tools)} tools")

        # Also send the response through the SSE connection to ensure the client receives it
        # This is critical for tools/list which might time out otherwise
        await send_sse_response(
            sse_transport,
            session_id,
            response,
            "tools/list"
        )

        return response

    except Exception as e:
        logger.error(f"Error processing tools/list request: {str(e)}")
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": message.get("id")
        }

        # Send error response through SSE as well
        await send_sse_response(
            sse_transport,
            session_id,
            error_response,
            "tools/list error"
        )

        return error_response
