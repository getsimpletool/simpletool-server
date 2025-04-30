import asyncio
import os
import signal
import sys
from typing import Any
from server.logger import logger
from config import CONFIG_MAIN_FILE_PATH, APP_VERSION, APP_NAME
import routers.prompts as prompts_module
import routers.admin as admin_module
import routers.mcp_sse as mcp_sse_module
import routers.tools as tools_module
import routers.user as user_module
from auth import dependencies as auth_dependencies
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, responses
from fastapi.openapi.utils import get_openapi
from middleware import setup_middleware
from pydantic import BaseModel
from services.config import ConfigService
from services.mcpserver import McpServerService

# Load environment variables from .env file
load_dotenv()

fastapi = FastAPI(
    title=APP_NAME,
    description="A simple FastAPI server template",
    version=str(APP_VERSION)
)

# Setup middleware
setup_middleware(fastapi)

# Initialize services
logger.info("Initializing Services")
config_service = ConfigService(storage_type="files", settings={"config_file_path": CONFIG_MAIN_FILE_PATH})
mcpserver_service = McpServerService(config_service=config_service)

# Set 'config_service' in auth dependencies module
auth_dependencies.set_config_service(config_service)

# Include routers
fastapi.include_router(user_module.router)
fastapi.include_router(mcp_sse_module.router)  # Include the SSE transport router
fastapi.include_router(prompts_module.router)
fastapi.include_router(admin_module.router)


def custom_openapi():
    """
    Custom OpenAPI generator that includes dynamic tool endpoints and patches /user/me.
    """
    if fastapi.openapi_schema:
        return fastapi.openapi_schema
    schema = get_openapi(
        title=fastapi.title,
        version=fastapi.version,
        routes=fastapi.routes,
    )
    fastapi.openapi_schema = schema
    return fastapi.openapi_schema


fastapi.openapi = custom_openapi


@fastapi.get("/", include_in_schema=False, response_class=responses.HTMLResponse)
async def root():
    return f"""
    <html>
        <body>
            <h3>Welcome to the {APP_NAME} API</h3>
            <p>Check <a href="/docs">docs</a> or <a href="/redoc">redoc</a> for API documentation</p>
            <p>Check <a href="/tools/openapi.json">tools</a> for tools documentation</p>
        </body>
    </html>
    """


class HealthResponse(BaseModel):
    status: str


@fastapi.get("/health", response_model=HealthResponse, include_in_schema=False)
async def handle_health():
    return {"status": "ok"}


class PingResponse(BaseModel):
    response: str


@fastapi.get("/ping", response_model=PingResponse, include_in_schema=False)
async def handle_ping():
    return {"response": "pong"}


@fastapi.get("/tools/openapi.json", include_in_schema=False)
async def get_tools_openapi(tools_router=Depends(tools_module.get_tools_router)):
    """
    Return a filtered OpenAPI schema containing only the tools endpoints.
    """
    return responses.JSONResponse(content=tools_router.get_openapi_schema(fastapi))


@fastapi.on_event("startup")
async def startup_event():
    # Load the configuration from disk
    await config_service.main_config.load_config()

    # Load user configurations
    await config_service.users.load_users_configs()

    # Initialize server manager on startup
    await mcpserver_service.initialize()

    # Store mcpserver_service on app.state
    fastapi.state.mcpserver_service = mcpserver_service

    # Initialize tools router with available tools and include it
    from routers.tools import tools_router  # pylint: disable=C0415
    # Initialize the router with actual endpoints
    await tools_router.initialize(mcpserver_service)
    # Include the router with the dynamically created endpoints
    fastapi.include_router(tools_router.router)

    # Start periodic cleanup task for idle private server instances
    asyncio.create_task(periodic_idle_server_cleanup())


async def periodic_idle_server_cleanup():
    """
    Periodically clean up idle private server instances.
    Runs every 5 minutes by default.
    """
    cleanup_interval = int(os.getenv("PRIVATE_SERVER_CLEANUP_INTERVAL", "300"))  # Default: 5 minutes
    logger.info(f"Starting periodic cleanup of idle private servers (interval: {cleanup_interval} seconds)")

    while True:
        try:
            # Wait for the specified interval
            await asyncio.sleep(cleanup_interval)

            # Clean up idle private servers
            result = await mcpserver_service.cleanup_idle_private_servers()

            if result["cleaned_servers"]:
                logger.info(
                    f"Cleaned up {len(result['cleaned_servers'])} idle private servers: "
                    f"{', '.join([srv['private_server_name'] for srv in result['cleaned_servers']])}"
                )
            else:
                logger.debug("No idle private servers to clean up")

        except asyncio.CancelledError:
            logger.info("Private server cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in private server cleanup task: {str(e)}")
            # Continue running despite errors
            await asyncio.sleep(60)  # Wait a bit before retrying after an error


@fastapi.on_event("shutdown")
async def shutdown_event():
    """Gracefully shut down all server processes when the application is terminated."""
    logger.info("Shutting down server processes...")

    try:
        # Get the current event loop for scheduling the force exit
        loop = asyncio.get_running_loop()

        # Schedule a force exit after a short delay (3 seconds)
        # This ensures we don't hang indefinitely even if the regular shutdown fails
        force_exit_handle = loop.call_later(3.0, lambda: os._exit(0))
        logger.warning("Scheduled force exit in 3 seconds if graceful shutdown fails")

        # First, close all SSE connections
        from routers.mcp_sse import sse_transport  # pylint: disable=C0415
        logger.info("Shutting down SSE transport...")
        await sse_transport.shutdown()
        logger.info("All SSE connections closed successfully")

        # Then shutdown all server processes (both public and private)
        logger.info("Shutting down server manager...")
        await mcpserver_service.stop_all_mcpservers()
        logger.info("All server processes terminated successfully")

        # If we got here successfully, we can cancel the force exit
        logger.info("Graceful shutdown succeeded, cancelling force exit")
        force_exit_handle.cancel()

        # But still exit immediately to avoid Uvicorn waiting for connections
        logger.info("Exiting immediately")
        os._exit(0)
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        # Force exit on error - don't wait for Uvicorn
        logger.critical("Forcing immediate exit due to shutdown error")
        os._exit(1)


# Register signal handlers
def signal_handler(sig: int, frame: Any) -> None:
    """
    Signal handler to properly shut down the server when SIGINT or SIGTERM is received.

    This ensures graceful shutdown of all server processes.
    """
    logger.debug(f"Received signal {sig} (frame {frame})")
    logger.info("Received termination signal, shutting down...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
