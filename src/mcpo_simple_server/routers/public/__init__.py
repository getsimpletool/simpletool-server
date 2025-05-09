"""
Public Router Package

This package contains all the public-facing router functionality.
"""
from typing import Optional
from fastapi import APIRouter, Request
from mcpo_simple_server.services.mcpserver import McpServerService
from mcpo_simple_server.services.prompt_manager import PromptManager
from mcpo_simple_server.config import CONFIG_MAIN_FILE_PATH

router = APIRouter(
    prefix="/public",
    tags=["Public MCP Server and Prompts"],
)

# Global prompt manager instance
PROMPT_MANAGER: Optional[PromptManager] = None


def get_mcpserver_service(request: Request) -> McpServerService:
    return request.app.state.mcpserver_service


async def get_prompt_manager() -> PromptManager:
    """
    Get the prompt manager instance.

    Returns:
        The prompt manager instance
    """
    global PROMPT_MANAGER
    if PROMPT_MANAGER is None:
        PROMPT_MANAGER = PromptManager(CONFIG_MAIN_FILE_PATH)
        await PROMPT_MANAGER.load_all_prompts()
    return PROMPT_MANAGER

# Import modules to register routes
from . import mcpservers  # noqa: F401, E402
from . import prompts  # noqa: F401, E402
