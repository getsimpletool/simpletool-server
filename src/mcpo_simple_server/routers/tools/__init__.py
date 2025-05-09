"""
Dynamic Tools Router Module

This module provides a dynamic router that generates individual endpoints for each tool
available in the server. Each tool gets its own dedicated endpoint, making it easier to
document and use specific tools.
"""

from typing import Dict, List, Any, Type, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import create_model, Field
from loguru import logger
from mcpo_simple_server.services.mcpserver import McpServerService
from mcpo_simple_server.routers.admin import get_mcpserver_service
from mcpo_simple_server.auth import dependencies


class ToolsRouter:
    """
    Dynamic router that creates endpoints for each available tool.

    This class creates a FastAPI router with dynamically generated endpoints
    for each tool available in the server. Each tool gets its own dedicated
    endpoint with proper documentation based on the tool's metadata.
    """

    def __init__(self):
        """Initialize the tools router."""
        self.router = APIRouter(
            prefix="/tool",
            tags=["Tools"],
            responses={404: {"description": "Tool not found"}},
        )
        self.tools_metadata = {}
        self.initialized = False
        self._dynamic_route_names = set()  # Track dynamic endpoint names

    async def initialize(self, server_manager: McpServerService):
        """
        Initialize the router by fetching tools and creating endpoints.

        Args:
            server_manager: The server manager instance to fetch tools from
        """
        # Remove previously added dynamic tool endpoints
        if self._dynamic_route_names:
            new_routes = []
            for route in self.router.routes:
                if getattr(route, 'name', None) not in self._dynamic_route_names:
                    new_routes.append(route)
            self.router.routes = new_routes
            self._dynamic_route_names.clear()
        self.initialized = False

        # Fetch all available tools
        tools = await server_manager.list_tools()

        # Store tools metadata for later use
        self.tools_metadata = {tool["name"]: tool for tool in tools}

        # Group tools by server
        tools_by_server = {}
        for tool in tools:
            server_name = tool.get("server", "unknown")
            if server_name not in tools_by_server:
                tools_by_server[server_name] = []
            tools_by_server[server_name].append(tool)

        # Create an endpoint for each tool
        for server_name, server_tools in tools_by_server.items():
            for tool in server_tools:
                self._create_tool_endpoint(tool, server_name)

        self.initialized = True
        logger.info(f"Initialized tools router with {len(tools)} dynamic endpoints across {len(tools_by_server)} servers")

        # Return the router to allow chaining
        return self.router

    def _create_tool_endpoint(self, tool: Dict[str, Any], server_name: str):
        """
        Create a dedicated endpoint for a specific tool.

        Args:
            tool: Tool metadata dictionary
            server_name: Name of the server containing this tool
        """
        tool_name = tool["name"]
        tool_description = tool.get("description", f"Tool: {tool_name}")
        input_schema = tool.get("inputSchema", {})

        # Create a dynamic Pydantic model for the tool's input parameters
        # based on the tool's input schema
        param_fields = {}
        properties = input_schema.get("properties", {})
        required_props = input_schema.get("required", [])

        for prop_name, prop_schema in properties.items():
            field_type = self._get_field_type(prop_schema.get("type", "string"))
            is_required = prop_name in required_props

            # Create field with proper type and description
            field_info = Field(
                default=... if is_required else None,
                description=prop_schema.get("description", f"Parameter: {prop_name}")
            )

            param_fields[prop_name] = (field_type, field_info)

        # Create the dynamic model
        param_model = create_model(
            f"{tool_name.capitalize()}Params",
            **param_fields
        )

        # Create the endpoint function
        async def tool_endpoint(
            params: param_model = Body(..., description=f"Parameters for {tool_name}"),     # type: ignore
            username: Optional[str] = Depends(dependencies.get_username),  # only API key allowed or guest
            server_manager: McpServerService = Depends(get_mcpserver_service)
        ):
            """Invoke the tool with the provided parameters."""
            # Convert Pydantic model to dict if needed
            if hasattr(params, "dict"):
                params_dict = params.dict(exclude_none=True)
            else:
                # If it's already a dict, filter out None values
                params_dict = {k: v for k, v in params.items() if v is not None}

            result = await server_manager.invoke_tool(tool_name, params_dict, username)

            if "status" in result and result["status"] == "error":
                raise HTTPException(status_code=404, detail=result["message"])

            return result

        # Set function name and docstring for better OpenAPI docs
        tool_endpoint.__name__ = f"invoke_{tool_name}"
        tool_endpoint.__doc__ = f"""
        {tool_description}

        This endpoint invokes the '{tool_name}' tool with the provided parameters.
        """

        # Add the endpoint to the router
        self.router.add_api_route(
            f"/{server_name}/{tool_name}",
            tool_endpoint,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary=f"Invoke {tool_name} from {server_name}",
            description=tool_description,
            name=f"invoke_{server_name}_{tool_name}"
        )
        self._dynamic_route_names.add(f"invoke_{server_name}_{tool_name}")

        logger.debug(f"Created endpoint for tool: {server_name}/{tool_name}")

    def _get_field_type(self, type_str: str) -> Type:
        """
        Convert JSON Schema type to Python type.

        Args:
            type_str: JSON Schema type string

        Returns:
            Corresponding Python type
        """
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": List[Any],
            "object": Dict[str, Any]
        }

        return type_mapping.get(type_str, Any)

    def get_openapi_schema(self, app) -> Dict[str, Any]:
        """
        Generate a filtered OpenAPI schema containing only the tools endpoints.

        Args:
            app: The FastAPI application instance

        Returns:
            OpenAPI schema dictionary with only tools endpoints
        """
        # Get the full OpenAPI schema
        full_schema = app.openapi()

        # Create a new schema with only the tools endpoints
        tools_schema = {
            "openapi": full_schema["openapi"],
            "info": {
                "title": "MCP Tools API",
                "description": "API for invoking MCP tools",
                "version": full_schema["info"]["version"]
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }

        # Filter paths to include only those with the 'tools' tag
        for path, path_item in full_schema["paths"].items():
            if path.startswith("/tool/"):
                tools_schema["paths"][path] = path_item

        # Include all components/schemas from the full OpenAPI spec
        # This ensures all referenced schemas are available
        if "components" in full_schema and "schemas" in full_schema["components"]:
            tools_schema["components"]["schemas"] = full_schema["components"]["schemas"]

        return tools_schema


# Create a singleton instance
tools_router = ToolsRouter()


# Dependency to get the initialized tools router
async def get_tools_router(server_manager: McpServerService = Depends(get_mcpserver_service)) -> ToolsRouter:
    """
    Get the initialized tools router.

    Args:
        server_manager: The server manager instance

    Returns:
        Initialized tools router
    """
    if not tools_router.initialized:
        await tools_router.initialize(server_manager)
    return tools_router


# Export the router for inclusion in the main app
router = tools_router.router
