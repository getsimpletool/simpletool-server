"""
MCP SSE Router

This module implements the SSE transport layer endpoints for the Model Context Protocol (MCP).
It provides endpoints for SSE connections and message handling according to MCP specifications.
"""
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Body, Query, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from loguru import logger
from services.sse_transport import SseTransport
from mcpo_simple_server.services.mcpserver import McpServerService
from mcpo_simple_server.routers.admin import get_mcpserver_service
from routers.mcp_sse.handlers import (
    validate_session_id,
    create_error_response,
    handle_initialize,
    handle_initialized,
    handle_cancelled,
    handle_tools_list,
    handle_tools_call
)


sse_transport: SseTransport = SseTransport()

router = APIRouter(
    prefix="/mcp",
    tags=["MCP-SSE"],
    responses={404: {"description": "Not found"}},
)


@router.post("/tool/{tool_name}")
async def invoke_tool(
    tool_name: str,
    params: Dict[str, Any] = Body(..., description="Parameters for the tool"),
    mcpserver_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    Invoke a specific tool with parameters.

    Each tool expects different parameters. You can get the list of available tools and their 
    required parameters from the /manager/tools endpoint.

    Example for get_current_time:
    ```json
    {
        "timezone": "America/New_York"
    }
    ```

    Example for convert_time:
    ```json
    {
        "source_timezone": "America/New_York",
        "time": "14:30",
        "target_timezone": "Europe/London"
    }
    ```
    """
    # Invoke the tool with the parameters directly
    result = await mcpserver_service.invoke_tool(tool_name, params)

    if "status" in result and result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.get("/sse", response_class=EventSourceResponse)
async def handle_sse_connection(request: Request, client_id: Optional[str] = Query(None, description="Optional client ID for reconnection"),
                                mcpserver_service: McpServerService = Depends(get_mcpserver_service)):
    """
    Handle SSE connection from an MCP client.

    Args:
        request: The FastAPI request object
        client_id: Optional client ID for reconnection
        server_manager: The server manager instance

    Returns:
        EventSourceResponse for SSE streaming
    """
    client_host = request.client.host if request.client else "unknown"
    client_port = request.client.port if request.client else "unknown"
    logger.info(f"Handling SSE connection request from {client_host}:{client_port}")

    # Use the SSE transport's generator directly, which now leverages the context manager internally
    return EventSourceResponse(sse_transport.handle_sse_connection(client_id), ping=5)


@router.post("/message")
async def message_endpoint(
    session_id: str = Query(..., description="Session ID for the SSE connection"),
    message: Dict[str, Any] = Body(..., description="JSON-RPC message to process"),
    mcpserver_service: McpServerService = Depends(get_mcpserver_service)
) -> Dict[str, Any]:
    """
    HTTP POST endpoint for clients to send messages to the server.

    This endpoint is dynamically provided to clients upon SSE connection.
    Clients send JSON-RPC formatted messages to this endpoint.

    Args:
        session_id: The session ID provided during SSE connection
        message: The JSON-RPC message to process
        server_manager: The server manager instance

    Returns:
        Response to the client message
    """
    # Validate the session ID
    is_valid, session_id, error = validate_session_id(session_id)
    if not is_valid and error is not None:
        error["id"] = message.get("id")  # Add the request ID to the error response
        return error

    logger.info(f"Received message from client: {session_id}")
    logger.debug(f"Message content: {json.dumps(message)}")

    # Validate JSON-RPC format
    if "jsonrpc" not in message or message.get("jsonrpc") != "2.0":
        logger.warning(f"Invalid JSON-RPC message from client {session_id}")
        return create_error_response(
            -32600,
            "Invalid JSON-RPC request",
            message.get("id")
        )

    # Extract method
    method = message.get("method")
    if not method:
        logger.warning(f"Missing method in JSON-RPC message from client {session_id}")
        return create_error_response(
            -32600,
            "Method not specified",
            message.get("id")
        )

    # Route the message to the appropriate handler based on the method
    try:
        if method == "initialize":
            return await handle_initialize(session_id, message, sse_transport)

        elif method == "initialized" or method == "notifications/initialized":
            return await handle_initialized(session_id, message, sse_transport)

        elif method == "notifications/cancelled":
            return await handle_cancelled(session_id, message, sse_transport)

        elif method == "tools/list":
            return await handle_tools_list(session_id, message, sse_transport, mcpserver_service)

        elif method == "tools/call":
            return await handle_tools_call(session_id, message, sse_transport, mcpserver_service)

        else:
            # Handle unknown methods
            logger.warning(f"Unknown method '{method}' from client {session_id}")
            return create_error_response(
                -32601,
                f"Method not found: {method}",
                message.get("id")
            )

    except Exception as e:
        logger.error(f"Error processing message with method '{method}': {str(e)}")
        return create_error_response(
            -32603,
            f"Internal error: {str(e)}",
            message.get("id")
        )


@router.get("/sessions")
async def list_active_sessions():
    """
    List all active SSE sessions.

    Returns:
        A list of active session IDs and their metadata
    """
    logger.info("Listing all active SSE sessions")

    result = []
    # Convert UUID hex string to a formatted UUID string for better readability
    for session_id, active in sse_transport.active_connections.items():
        if active:
            session_info = {
                "session_id": session_id,
                "initialized": sse_transport.client_info.get(session_id, {}).get("initialized", False),
                "client_info": sse_transport.client_info.get(session_id, {}).get("clientInfo", {}),
                "protocol_version": sse_transport.client_info.get(session_id, {}).get("protocolVersion", "unknown"),
                "connected_at": sse_transport.client_info.get(session_id, {}).get("connected_at", "unknown"),
                "queue_size": sse_transport.message_queues[session_id].qsize() if session_id in sse_transport.message_queues else 0
            }
            result.append(session_info)

    return {"total": len(result), "sessions": result}


@router.get("/servers", status_code=200)
async def list_public_servers(
    mcpserver_service: McpServerService = Depends(get_mcpserver_service)
):
    """
    List all public MCP servers available for client use.
    Does not require authentication.

    Returns:
        Dict containing only public server configurations and status
    """
    logger.info("Public API: listing available public MCP servers")

    try:
        all_servers = await mcpserver_service.list_mcpservers()

        # Filter to only include public servers
        public_servers = [
            server for server in all_servers
            if server.get("type") == "public"
        ]

        logger.info(f"Returning {len(public_servers)} public servers")
        return {"servers": public_servers}
    except Exception as e:
        logger.error(f"Error listing public servers: {str(e)}")
        # Return an empty list instead of failing for this public API
        return {"servers": []}


def get_sse_transport():
    """
    Get the SSE transport instance for dependency injection.

    Returns:
        The global SSE transport instance
    """
    return sse_transport
