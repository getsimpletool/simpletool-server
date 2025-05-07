"""
Tools Call Message Handler

Handles the 'tools/call' request from MCP clients.
"""

from typing import Dict, Any
from loguru import logger

from mcpo_simple_server.services.mcpserver import McpServerService
from mcpo_simple_server.services.sse_transport import SseTransport
from .utils import check_client_initialized, send_sse_response, create_error_response


async def handle_tools_call(
    session_id: str,
    message: Dict[str, Any],
    sse_transport: SseTransport,
    mcpserver_service: McpServerService
) -> Dict[str, Any]:
    """
    Handle the 'tools/call' request from a client.

    This request is sent by the client to execute a specific tool.

    Args:
        session_id: The session ID for the client
        message: The JSON-RPC message from the client
        sse_transport: The SSE transport instance
        server_manager: The server manager instance

    Returns:
        The JSON-RPC response to send back to the client
    """
    logger.info(f"Handling tools/call request from client {session_id}")

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

    # Extract parameters
    params = message.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not tool_name:
        logger.warning(f"Missing tool name in tools/call request from client {session_id}")
        error_response = create_error_response(
            -32602,
            "Invalid params: tool name not specified",
            message.get("id")
        )

        # Send error through SSE as well
        await send_sse_response(
            sse_transport,
            session_id,
            error_response,
            "missing tool name error"
        )

        return error_response

    try:
        # Invoke the tool and capture its raw response (including JSON-RPC errors)
        result = await mcpserver_service.invoke_tool(tool_name, arguments)

        # Unified error propagation: pass through JSON-RPC error or status error 1:1
        if "error" in result:
            error = result["error"]
        elif result.get("status") == "error":
            # internal manager error, wrap under code -32603
            error = {"code": -32603, "message": result.get("message", "Tool execution failed")}
        else:
            error = None
        if error:
            response = {"jsonrpc": "2.0", "id": message.get("id"), "error": error}
            await send_sse_response(sse_transport, session_id, response, "tools/call error")
            return response

        # Extract the content from the result
        # The invoke_tool method returns the raw response from the server
        # which includes the JSON-RPC envelope
        content = []
        is_error = False

        # Check if the result contains a nested result from the tool server
        if "result" in result and isinstance(result["result"], dict):
            # Extract content and isError from the nested result
            content = result["result"].get("content", [])
            is_error = result["result"].get("isError", False)

        # Create the response according to MCP specification
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "content": content,
                "isError": is_error
            }
        }

        logger.debug(f"Sending tools/call response to client {session_id}")

        # Also send the response through the SSE connection to ensure the client receives it
        await send_sse_response(
            sse_transport,
            session_id,
            response,
            "tools/call"
        )

        return response

    except Exception as e:
        logger.error(f"Error processing tools/call request: {str(e)}")
        error_response = create_error_response(
            -32603,
            f"Internal error: {str(e)}",
            message.get("id")
        )

        # Send error through SSE as well
        await send_sse_response(
            sse_transport,
            session_id,
            error_response,
            "tools/call exception"
        )

        return error_response
