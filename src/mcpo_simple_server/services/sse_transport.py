"""
SSE Transport Layer for MCP

This module implements the Server-Sent Events (SSE) transport layer for the Model Context Protocol (MCP).
It provides functionality for real-time communication between the SimpleTool server and MCP applications.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, Set
from loguru import logger


class SseTransport:
    """
    Server-Sent Events (SSE) transport implementation for MCP.

    This class manages SSE connections, message routing, and event formatting
    according to the MCP specification.
    """

    def __init__(self):
        # Store message queues for each connection
        self.message_queues: Dict[str, asyncio.Queue] = {}
        # Store client information including protocol version and capabilities
        self.client_info: Dict[str, Dict[str, Any]] = {}
        # Keep track of active connections
        self.active_connections: Dict[str, bool] = {}
        # Flag to indicate if shutdown is in progress
        self.shutting_down: bool = False
        # Store connection tasks to cancel them during shutdown
        self.connection_tasks: Set[asyncio.Task] = set()

    async def handle_sse_connection(self, client_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle a new SSE connection from a client.

        Args:
            client_id: Optional client ID. If not provided, a new UUID will be generated.

        Returns:
            An async generator that yields SSE events.
        """
        # Check if shutdown is in progress
        if self.shutting_down:
            logger.warning("Server is shutting down, rejecting new connection")
            return

        # Use the provided client_id or generate a new one with dashes
        if client_id:
            # Ensure the client_id is in the correct format with dashes
            try:
                # Convert to UUID and back to string to ensure correct format
                session_id = str(uuid.UUID(client_id))
            except ValueError:
                # If not a valid UUID, generate a new one
                session_id = str(uuid.uuid4())
                logger.warning(f"Invalid client_id provided: {client_id}, generated new UUID: {session_id}")
        else:
            # Generate a new UUID with dashes
            session_id = str(uuid.uuid4())

        logger.info(f"New SSE connection established for client: {session_id}")

        # Create a message queue for this client if it doesn't exist
        if session_id not in self.message_queues:
            self.message_queues[session_id] = asyncio.Queue()
            self.client_info[session_id] = {
                "initialized": False,
                "protocolVersion": "2024-11-05",  # Default protocol version
                "capabilities": {},
                "clientInfo": {}
            }

        async with SseConnection(session_id, self) as connection:
            # Send the initial endpoint event with the message URI
            # Use the session_id query parameter format expected by MCP clients
            endpoint_uri = f"/mcp/message?session_id={session_id}"

            # Format the endpoint event according to SSE specification
            # The event field specifies the event type, and the data field contains the event data
            yield {
                "event": "endpoint",
                "data": endpoint_uri
            }

            logger.debug(f"Sent endpoint event with URI: {endpoint_uri}")

            # Process messages from the queue
            try:
                while connection.is_active():
                    # Wait for a message from the queue with a timeout
                    try:
                        message = await asyncio.wait_for(
                            self.message_queues[session_id].get(),
                            timeout=5  # Reduced timeout to check for shutdown more frequently
                        )

                        # Format the message as an SSE event according to the specification
                        # The message must be serialized to JSON and sent as the 'data' field
                        message_data = json.dumps(message)
                        logger.debug(f"Sending message to client {session_id}: {message_data}")

                        yield {
                            "event": "message",
                            "data": message_data
                        }

                    except asyncio.TimeoutError:
                        # Check if we're shutting down before sending keep-alive
                        if self.shutting_down:
                            logger.debug(f"Shutdown in progress, closing connection for client {session_id}")
                            break

                        # Send a keep-alive comment to prevent connection timeout
                        yield {"comment": "keep-alive"}
            except asyncio.CancelledError:
                logger.info(f"SSE connection task cancelled for client {session_id}")
                raise
            except Exception as e:
                logger.error(f"Error in SSE connection for client {session_id}: {str(e)}")

    async def send_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific client.

        Args:
            session_id: The session ID to send the message to
            message: The message to send

        Returns:
            True if the message was sent successfully, False otherwise
        """
        # Check if shutdown is in progress
        if self.shutting_down:
            logger.warning("Server is shutting down, not sending message")
            return False

        # Normalize session_id to ensure it's in the correct format
        try:
            normalized_session_id = str(uuid.UUID(session_id))
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id}")
            return False

        if normalized_session_id not in self.message_queues:
            logger.warning(f"Cannot send message to unknown client: {normalized_session_id}")
            return False

        try:
            # Add message to the client's queue
            await self.message_queues[normalized_session_id].put(message)
            logger.debug(f"Message queued for client {normalized_session_id}: {json.dumps(message)}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to client {normalized_session_id}: {str(e)}")
            return False

    async def shutdown(self) -> None:
        """
        Forcefully shut down all active SSE connections.

        This method should be called when the server is shutting down to ensure
        all clients are properly disconnected.
        """
        logger.info("Forcefully shutting down SSE transport...")

        # Mark as shutting down to prevent new connections and messages
        self.shutting_down = True

        # Close all active connections
        active_sessions = [
            session_id for session_id, active in self.active_connections.items()
            if active
        ]

        if active_sessions:
            logger.warning(f"Force terminating {len(active_sessions)} active SSE connections: {active_sessions}")

            # Immediately mark all connections as inactive
            for session_id in active_sessions:
                self.active_connections[session_id] = False
                logger.debug(f"Marked connection {session_id} as inactive")
        else:
            logger.info("No active SSE connections to terminate")

        # Cancel all connection tasks to force immediate disconnection
        tasks_to_cancel = list(self.connection_tasks)
        if tasks_to_cancel:
            logger.warning(f"Cancelling {len(tasks_to_cancel)} connection tasks")

            for task in tasks_to_cancel:
                if not task.done() and not task.cancelled():
                    try:
                        task.cancel()
                        logger.debug(f"Cancelled connection task: {task}")
                    except Exception as e:
                        logger.error(f"Error cancelling task {task}: {str(e)}")

            # Wait for all tasks to be cancelled with a short timeout
            try:
                # Use asyncio.wait with return_exceptions=True to handle cancellation
                _, pending = await asyncio.wait(
                    tasks_to_cancel,
                    timeout=0.5,
                    return_when=asyncio.ALL_COMPLETED
                )

                if pending:
                    logger.warning(f"{len(pending)} tasks still pending after cancellation timeout")

                    # Attempt to cancel again more aggressively
                    for task in pending:
                        if not task.done() and not task.cancelled():
                            try:
                                task.cancel()
                                logger.debug(f"Forcefully cancelled pending task: {task}")
                            except Exception as e:
                                logger.error(f"Error in aggressive task cancellation: {str(e)}")
            except Exception as e:
                logger.error(f"Error waiting for tasks to cancel: {str(e)}")
        else:
            logger.info("No SSE connection tasks to cancel")

        # Clear all message queues to prevent memory leaks
        logger.debug("Clearing message queues")
        for session_id, queue in list(self.message_queues.items()):
            try:
                # Drain the queue
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except Exception:
                        pass
                logger.debug(f"Cleared message queue for session {session_id}")
            except Exception as e:
                logger.error(f"Error clearing message queue for session {session_id}: {str(e)}")

        # Reset all data structures
        self.message_queues.clear()
        self.client_info.clear()
        self.active_connections.clear()
        self.connection_tasks.clear()

        logger.info("SSE transport shutdown complete")


class SseConnection:
    """
    A context manager for SSE connections.

    This class manages the lifecycle of a single SSE connection and ensures
    proper cleanup when the connection is closed or when a shutdown occurs.
    """

    def __init__(self, session_id: str, transport: 'SseTransport'):
        self.session_id = session_id
        self.transport = transport
        self.active = False
        self.shutdown_monitor_task = None

    async def __aenter__(self):
        """Set up the connection when entering the context."""
        self.active = True
        self.transport.active_connections[self.session_id] = True

        # Register current task for potential cancellation during shutdown
        current_task = asyncio.current_task()
        if current_task:
            self.transport.connection_tasks.add(current_task)

        # Start shutdown monitoring if not already shutting down
        if not self.transport.shutting_down:
            self.shutdown_monitor_task = asyncio.create_task(self._monitor_shutdown())

        logger.info(f"SSE connection {self.session_id} established")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the connection when exiting the context."""
        self.active = False

        # Clean up the connection
        if self.session_id in self.transport.active_connections:
            self.transport.active_connections[self.session_id] = False

        # Cancel the shutdown monitor task if it's still running
        if self.shutdown_monitor_task and not self.shutdown_monitor_task.done():
            try:
                self.shutdown_monitor_task.cancel()
                await asyncio.sleep(0)  # Yield control to allow cancellation to process
            except Exception as e:
                logger.error(f"Error cancelling shutdown monitor for {self.session_id}: {str(e)}")

        # Remove the current task from the transport's tracked tasks
        current_task = asyncio.current_task()
        if current_task and current_task in self.transport.connection_tasks:
            self.transport.connection_tasks.remove(current_task)

        logger.info(f"SSE connection {self.session_id} closed")

        # Don't suppress exceptions
        return False

    async def _monitor_shutdown(self):
        """Monitor for server shutdown and handle it gracefully."""
        try:
            while not self.transport.shutting_down and self.active:
                await asyncio.sleep(0.5)

            if self.transport.shutting_down and self.active:
                logger.warning(f"Server is shutting down - connection {self.session_id} will be terminated")
                self.active = False

        except asyncio.CancelledError:
            logger.debug(f"Shutdown monitor for {self.session_id} cancelled")
        except Exception as e:
            logger.error(f"Error in shutdown monitor for {self.session_id}: {str(e)}")

    def is_active(self):
        """Check if the connection is still active."""
        return self.active and not self.transport.shutting_down
