"""
Public Prompts Router

This module provides functionality for accessing and executing public prompts.
"""
from typing import List
from fastapi import Depends, HTTPException, status
from mcpo_simple_server.auth.models.auth import UserInDB
from mcpo_simple_server.auth import dependencies
from mcpo_simple_server.services.prompt_manager import PromptManager
from mcpo_simple_server.services.prompt_manager.models.prompts import PromptInfo, PromptExecuteRequest, PromptExecuteResponse, PromptMessage
from mcpo_simple_server.routers.public import router, get_prompt_manager
from loguru import logger


@router.get("/prompts", response_model=List[PromptInfo])
async def list_public_prompts(
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> List[PromptInfo]:
    """
    List all public prompts.

    Returns:
        List of public prompt info objects
    """
    logger.debug("Listing public prompts")
    return await prompt_manager.get_public_prompts()


@router.post("/prompts/{name}", response_model=PromptExecuteResponse)
async def execute_public_prompt(
    name: str,
    request: PromptExecuteRequest,
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> PromptExecuteResponse:
    """
    Execute a public prompt with the given arguments.

    Args:
        name: The name of the prompt to execute
        request: The request containing arguments

    Returns:
        The processed messages with variables filled in
    """
    logger.debug(f"Admin '{admin_user.username}' executing public prompt: {name}")
    raw_messages = await prompt_manager.execute_prompt(
        prompt_name=name,
        arguments=request.arguments,
        username="public"  # Default username for public prompts
    )

    if not raw_messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{name}' not found or required arguments missing"
        )

    # Convert raw dictionaries to PromptMessage objects
    messages = [PromptMessage(**msg) for msg in raw_messages]

    return PromptExecuteResponse(messages=messages)


@router.get("/prompts/reload", status_code=status.HTTP_200_OK)
async def reload_public_prompts(
    admin_user: UserInDB = Depends(dependencies.get_current_admin_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> dict:
    """
    Reload only public prompts from the filesystem.
    This is useful when public prompts have been added, removed, or modified directly on the filesystem.

    Returns:
        A message indicating the reload was successful and count of loaded public prompts
    """
    logger.info(f"Admin '{admin_user.username}' reloading public prompts")

    # Reload only public prompts from the filesystem
    await prompt_manager.reload_public_prompts()

    # Return count of loaded public prompts
    return {
        "message": "Public prompts reloaded successfully",
        "count": len(prompt_manager.public_prompts)
    }
