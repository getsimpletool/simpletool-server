"""
Router package.

This package contains all the FastAPI routers for the server.
"""

# Define what should be exported from this package
__all__ = ['admin_router', 'tools_router', 'public_router', 'mcp_sse_router']

# Import the router modules directly
from .admin import router as admin_router
from .tools import router as tools_router
from .public import router as public_router
from .mcp_sse import router as mcp_sse_router
