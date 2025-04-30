"""
MCP SSE Utilities

This module provides utility functions for the MCP SSE transport layer.
"""

import uuid
from typing import Dict, Any, Optional, Tuple
from loguru import logger

from services.sse_transport import SseTransport


def create_error_response(error_code: int, error_message: str, request_id: Any) -> Dict[str, Any]:
    """
    Create a JSON-RPC error response.

    Args:
        error_code: The JSON-RPC error code
        error_message: The error message
        request_id: The request ID from the client message

    Returns:
        A JSON-RPC error response
    """
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": error_code,
            "message": error_message
        },
        "id": request_id
    }


def validate_session_id(session_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validate a session ID and ensure it's in the correct format.

    Args:
        session_id: The session ID to validate

    Returns:
        A tuple of (is_valid, normalized_session_id, error_response)
        If is_valid is False, error_response will contain a JSON-RPC error response
    """
    try:
        # Convert to UUID and back to string to ensure correct format
        normalized_session_id = str(uuid.UUID(session_id))
        return True, normalized_session_id, None
    except ValueError:
        logger.warning(f"Invalid session ID format: {session_id}")
        error_response = create_error_response(
            -32602,
            f"Invalid session ID format: {session_id}",
            None  # We don't have a request ID here
        )
        return False, session_id, error_response


async def send_sse_response(
    sse_transport: SseTransport,
    session_id: str,
    response: Dict[str, Any],
    log_prefix: str
) -> None:
    """
    Send a response through the SSE transport.

    Args:
        sse_transport: The SSE transport instance
        session_id: The session ID to send the response to
        response: The response to send
        log_prefix: A prefix for log messages
    """
    try:
        await sse_transport.send_message(session_id, response)
        logger.debug(f"Sent {log_prefix} response through SSE to client {session_id}")
    except Exception as e:
        logger.error(f"Error sending {log_prefix} response through SSE: {str(e)}")


def check_client_initialized(
    sse_transport: SseTransport,
    session_id: str,
    request_id: Any
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if a client is initialized.

    Args:
        sse_transport: The SSE transport instance
        session_id: The session ID to check
        request_id: The request ID from the client message

    Returns:
        A tuple of (is_initialized, error_response)
        If is_initialized is False, error_response will contain a JSON-RPC error response
    """
    if session_id not in sse_transport.client_info or not sse_transport.client_info[session_id].get("initialized", False):
        logger.warning(f"Client {session_id} tried to use tools before initialization")
        error_response = create_error_response(
            -32002,
            "Client not initialized",
            request_id
        )
        return False, error_response

    return True, None
