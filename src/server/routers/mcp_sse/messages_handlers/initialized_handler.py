"""
Initialized Message Handler

Handles the 'initialized' notification from MCP clients.
"""

from typing import Dict, Any
from loguru import logger

from services.sse_transport import SseTransport


async def handle_initialized(
    session_id: str,
    message: Dict[str, Any],
    sse_transport: SseTransport
) -> Dict[str, Any]:
    """
    Handle the 'initialized' notification from a client.

    This notification is sent by the client after it has processed the
    initialize response and is ready for normal operation.

    Args:
        session_id: The session ID for the client
        message: The JSON-RPC message from the client
        sse_transport: The SSE transport instance

    Returns:
        An empty dict as this is a notification
    """
    logger.info(f"Received initialized notification from client {session_id}")

    # Mark the client as initialized
    if session_id in sse_transport.client_info:
        sse_transport.client_info[session_id]["initialized"] = True
        logger.info(f"Client {session_id} is now initialized")

        # Send a notification to inform the client that the server is ready
        # This might help trigger the client to continue with normal operation
        try:
            await sse_transport.send_message(session_id, {
                "jsonrpc": "2.0",
                "method": "server/ready",
                "params": {}
            })
            logger.debug(f"Sent server/ready notification to client {session_id}")
        except Exception as e:
            logger.error(f"Error sending server/ready notification: {str(e)}")
    else:
        logger.warning(f"Received initialized notification for unknown client: {session_id}")

    # This is a notification, so no response is expected
    return {}
