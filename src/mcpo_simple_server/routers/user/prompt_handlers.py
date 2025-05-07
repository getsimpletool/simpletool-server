"""
User Router for private and shared prompts.

This module provides API endpoints for managing private and shared prompts.
"""
from fastapi import Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from uuid import UUID
from mcpo_simple_server.services.prompt_manager import PromptManager
from mcpo_simple_server.config import CONFIG_MAIN_FILE_PATH
from mcpo_simple_server.auth.dependencies import get_current_access_user
from mcpo_simple_server.auth.models.auth import UserInDB
from mcpo_simple_server.services.prompt_manager.models.prompts import (
    PromptInfo,
    PromptExecuteRequest,
    PromptExecuteResponse,
    PromptCreateRequest,
    PromptSource,
    PromptMessage
)
from . import router
from loguru import logger

# Global prompt manager instance
PROMPT_MANAGER: Optional[PromptManager] = None


async def get_prompt_manager() -> PromptManager:
    """
    Get or create the prompt manager instance.

    Returns:
        The prompt manager instance
    """
    global PROMPT_MANAGER
    if PROMPT_MANAGER is None:
        PROMPT_MANAGER = PromptManager(CONFIG_MAIN_FILE_PATH)
        await PROMPT_MANAGER.load_all_prompts()
    return PROMPT_MANAGER


@router.get("/prompts", response_model=List[PromptInfo])
async def list_user_prompts(
    current_user: UserInDB = Depends(get_current_access_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> List[PromptInfo]:
    """
    List all prompts accessible to the current user.
    This includes public prompts, the user's private prompts, and shared prompts they have access to.

    Returns:
        List of prompt info objects
    """
    logger.debug(f"Listing prompts for user: {current_user}")
    return await prompt_manager.get_user_prompts(current_user.username)


@router.post("/prompts/{prompt_id_or_name}", response_model=PromptExecuteResponse)
async def execute_user_prompt(
    prompt_id_or_name: str,
    request: PromptExecuteRequest,
    current_user: UserInDB = Depends(get_current_access_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> PromptExecuteResponse:
    """
    Execute a prompt with the given arguments.
    The prompt can be a public prompt, a private prompt, or a shared prompt.

    Args:
        prompt_id_or_name: The name or ID of the prompt to execute
        request: The request containing arguments

    Returns:
        The processed messages with variables filled in
    """
    logger.debug(f"Executing prompt for user {current_user}: {prompt_id_or_name}")

    # Check if prompt_id_or_name is a UUID (for shared prompts)
    try:
        UUID(prompt_id_or_name)
        is_uuid = True
    except ValueError:
        is_uuid = False

    messages = []
    if is_uuid:
        # Execute shared prompt
        messages = await prompt_manager.execute_prompt(
            prompt_name="",
            arguments=request.arguments,
            username=current_user.username,
            prompt_id=prompt_id_or_name
        )
    else:
        # Try to execute private prompt first, then fall back to public
        messages = await prompt_manager.execute_prompt(
            prompt_name=prompt_id_or_name,
            arguments=request.arguments,
            username=current_user.username
        )

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_id_or_name}' not found or required arguments missing"
        )

    message_objs = [PromptMessage(**m) for m in messages]
    return PromptExecuteResponse(messages=message_objs)


@router.put("/prompts", response_model=PromptInfo)
async def create_or_update_prompt(
    request: PromptCreateRequest,
    current_user: UserInDB = Depends(get_current_access_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> PromptInfo:
    """
    Create or update a private prompt.

    Args:
        request: The prompt data

    Returns:
        The created or updated prompt info
    """
    logger.debug(f"Creating/updating prompt for user {current_user}: {request.name}")

    # Convert to dict for easier handling
    prompt_data = request.dict()

    # Create private prompt
    prompt = await prompt_manager.create_private_prompt(current_user.username, prompt_data)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create or update prompt '{request.name}'"
        )

    return PromptInfo(
        name=prompt.name,
        description=prompt.description,
        arguments=prompt.arguments,
        source=PromptSource(type="private", path=f"prompts/{current_user.username}/{prompt.name}.json")
    )


@router.put("/prompts/share", response_model=PromptInfo)
async def create_shared_prompt(
    request: PromptCreateRequest,
    current_user: UserInDB = Depends(get_current_access_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> PromptInfo:
    """
    Create a shared prompt.

    Args:
        request: The prompt data

    Returns:
        The created shared prompt info
    """
    logger.debug(f"Creating shared prompt for user {current_user}: {request.name}")

    # Convert to dict for easier handling
    prompt_data = request.dict()

    # Create shared prompt
    prompt = await prompt_manager.create_shared_prompt(current_user.username, prompt_data)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create shared prompt '{request.name}'"
        )

    return PromptInfo(
        name=prompt.name,
        description=prompt.description,
        arguments=prompt.arguments,
        source=PromptSource(type="shared", path=f"prompts/_share-{prompt.id}.json"),
        id=prompt.id,
        owner=prompt.owner
    )


@router.post("/prompts/share/{prompt_id}/{target_username}")
async def share_prompt_with_user(
    prompt_id: str,
    target_username: str,
    current_user: UserInDB = Depends(get_current_access_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> Dict[str, Any]:
    """
    Share a prompt with another user.

    Args:
        prompt_id: The ID of the shared prompt
        target_username: The username to share the prompt with

    Returns:
        Success message
    """
    logger.debug(f"User {current_user} sharing prompt {prompt_id} with {target_username}")

    # Check if prompt exists and user is the owner
    if prompt_id not in prompt_manager.shared_prompts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shared prompt '{prompt_id}' not found"
        )

    prompt = prompt_manager.shared_prompts[prompt_id]
    if prompt.owner != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this prompt"
        )

    # Share prompt with user
    success = await prompt_manager.share_prompt_with_user(target_username, prompt_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to share prompt with user '{target_username}'"
        )

    return {"message": f"Prompt shared with user '{target_username}'"}


@router.delete("/prompts/{prompt_id_or_name}")
async def delete_prompt(
    prompt_id_or_name: str,
    current_user: UserInDB = Depends(get_current_access_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> Dict[str, Any]:
    """
    Delete a private or shared prompt.

    Args:
        prompt_id_or_name: The name or ID of the prompt to delete

    Returns:
        Success message
    """
    logger.debug(f"Deleting prompt for user {current_user}: {prompt_id_or_name}")

    # Check if prompt_id_or_name is a UUID (for shared prompts)
    try:
        UUID(prompt_id_or_name)
        is_uuid = True
    except ValueError:
        is_uuid = False

    success = False
    if is_uuid:
        # Delete shared prompt
        success = await prompt_manager.delete_shared_prompt(current_user.username, prompt_id_or_name)
    else:
        # Delete private prompt
        success = await prompt_manager.delete_private_prompt(current_user.username, prompt_id_or_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_id_or_name}' not found or you don't have permission to delete it"
        )

    return {"message": f"Prompt '{prompt_id_or_name}' deleted successfully"}


@router.get("/prompts/reload", status_code=status.HTTP_200_OK)
async def reload_all_prompts(
    current_user: UserInDB = Depends(get_current_access_user),
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> Dict[str, Any]:
    """
    Reload all prompts from the filesystem.
    This includes public, private, and shared prompts.
    This is useful when prompts have been added, removed, or modified directly on the filesystem.

    Returns:
        A message indicating the reload was successful and counts of loaded prompts
    """
    logger.info(f"Reloading all prompts (requested by user: {current_user.username})")

    # Reload all prompts from the filesystem
    await prompt_manager.load_all_prompts()

    # Return counts of loaded prompts
    return {
        "message": "All prompts reloaded successfully",
        "counts": {
            "public_prompts": len(prompt_manager.public_prompts),
            "shared_prompts": len(prompt_manager.shared_prompts),
            "users_with_private_prompts": len(prompt_manager.private_prompts)
        }
    }
