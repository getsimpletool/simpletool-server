"""
Cancelled Message Handler

Handles the 'notifications/cancelled' notification from MCP clients.
"""

from typing import Dict, Any
from loguru import logger


async def handle_cancelled(
    session_id: str,
    message: Dict[str, Any],
    sse_transport: Any
) -> Dict[str, Any]:
    """
    Handle the 'cancelled' notification from a client.

    This notification is sent by the client when it cancels a previous request.

    Args:
        session_id: The session ID for the client
        message: The JSON-RPC message from the client
        sse_transport: The SSE transport instance (unused but kept for consistent interface)

    Returns:
        An empty dict as this is a notification
    """
    logger.info(f"Received cancelled notification from client {session_id}")

    # Extract the request ID and reason
    params = message.get("params", {})
    request_id = params.get("requestId")
    reason = params.get("reason", "Unknown reason")

    logger.info(f"Client {session_id} cancelled request {request_id}: {reason}")

    # This is a notification, so no response is expected
    return {}
