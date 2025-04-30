"""
Initialize Message Handler

Handles the 'initialize' message from MCP clients.
"""

import json
from typing import Dict, Any
from datetime import datetime
from loguru import logger
from config import APP_VERSION, APP_NAME
from services.sse_transport import SseTransport
from .utils import send_sse_response


async def handle_initialize(
    session_id: str,
    message: Dict[str, Any],
    sse_transport: SseTransport
) -> Dict[str, Any]:
    """
    Handle the 'initialize' message from a client.

    This is the first message sent by a client to establish capabilities
    and protocol version.

    Args:
        session_id: The session ID for the client
        message: The JSON-RPC message from the client
        sse_transport: The SSE transport instance

    Returns:
        The JSON-RPC response to send back to the client
    """
    logger.info(f"Handling initialize request from client {session_id}")

    params = message.get("params", {})
    client_protocol_version = params.get("protocolVersion", "2024-11-05")
    client_capabilities = params.get("capabilities", {})
    client_info = params.get("clientInfo", {})

    logger.info(f"Client {session_id} requested protocol version: {client_protocol_version}")
    logger.debug(f"Client capabilities: {client_capabilities}")
    logger.debug(f"Client info: {client_info}")

    client_data = {
        "protocolVersion": client_protocol_version,
        "capabilities": client_capabilities,
        "clientInfo": client_info,
        "initialized": False,
        "connected_at": datetime.now().isoformat()
    }

    sse_transport.client_info[session_id] = client_data
    logger.debug(f"Updated client info for {session_id}: {json.dumps(client_data)}")

    # Create the response with server capabilities according to MCP specification
    response = {
        "jsonrpc": "2.0",
        "id": message.get("id"),
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": APP_NAME,
                "version": str(APP_VERSION)
            },
            "capabilities": {
                "tools": {
                    "execution": True,
                    "streaming": True
                },
                "roots": {
                    "listChanged": True
                }
            }
        }
    }

    logger.debug(f"Sending initialize response to client {session_id}: {json.dumps(response)}")

    # Also send the response through the SSE connection to ensure the client receives it
    # This is a workaround for clients that might not properly handle the HTTP response
    await send_sse_response(
        sse_transport,
        session_id,
        response,
        "initialize"
    )

    # Return the response but don't mark as initialized yet
    # The client will send an 'initialized' notification after receiving this response
    return response
