"""
SSE Transport Layer for MCP

This module implements the Server-Sent Events (SSE) transport layer for the Model Context Protocol (MCP).
It provides functionality for real-time communication between the SimpleTool server and MCP applications.
"""

from mcpo_simple_server.services.sse_transport.transport import SseTransport

__all__ = ["SseTransport"]
