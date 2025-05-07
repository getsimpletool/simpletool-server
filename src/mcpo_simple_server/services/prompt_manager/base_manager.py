"""
Base Prompt Manager Module

This module provides the base PromptManager class for managing prompt templates.
"""
import os
from typing import Dict, List, Any, Optional
from loguru import logger
import json
import time

from mcpo_simple_server.services.prompt_manager.models.prompts import PromptTemplate, PromptInfo, PromptSource
from mcpo_simple_server.services.prompt_manager.template_loader import PromptTemplateLoader
from mcpo_simple_server.services.prompt_manager.template_executor import PromptTemplateExecutor
from mcpo_simple_server.config import CONFIG_MAIN_FILE_PATH


class PromptManager:
    """
    Manager for prompt templates.
    Handles loading, saving, and executing prompts.
    """

    def __init__(self, config_path: str = CONFIG_MAIN_FILE_PATH):
        """
        Initialize the prompt manager.

        Args:
            config_path: Path to the configuration directory (defaults to global CONFIG_MAIN_FILE_PATH)
        """
        self.config_path = config_path
        # Primary prompts directory in config path
        self.prompts_dir = os.path.join(config_path, "prompts")
        # Additional prompts directory directly in data path
        self.data_prompts_dir = os.path.join(os.path.dirname(config_path), "prompts")

        # Initialize template collections
        self.public_prompts: Dict[str, PromptTemplate] = {}
        self.private_prompts: Dict[str, Dict[str, PromptTemplate]] = {}  # username -> name -> prompt
        self.shared_prompts: Dict[str, PromptTemplate] = {}  # uuid -> prompt

        # Create prompts directories if they don't exist
        os.makedirs(self.prompts_dir, exist_ok=True)
        os.makedirs(self.data_prompts_dir, exist_ok=True)

        # Initialize helper components
        self.template_loader = PromptTemplateLoader()
        self.template_executor = PromptTemplateExecutor()

    async def load_all_prompts(self) -> None:
        """
        Load all prompts from the filesystem.
        This includes public, private, and shared prompts.
        """
        logger.info("Loading all prompts")

        # Clear existing prompts
        self.public_prompts.clear()
        self.private_prompts.clear()
        self.shared_prompts.clear()

        # Load public prompts
        await self._load_public_prompts()

        # Load shared prompts
        await self._load_shared_prompts()

        # Load private prompts for all users
        await self._load_all_private_prompts()

        logger.info(f"Loaded {len(self.public_prompts)} public prompts, "
                    f"{len(self.shared_prompts)} shared prompts, and "
                    f"private prompts for {len(self.private_prompts)} users")

    async def reload_public_prompts(self) -> None:
        """
        Reload only public prompts from the filesystem.
        Private and shared prompts are not affected.
        """
        logger.info("Reloading public prompts")

        # Clear existing public prompts
        self.public_prompts.clear()

        # Load public prompts
        await self._load_public_prompts()

        logger.info(f"Reloaded {len(self.public_prompts)} public prompts")

    async def _load_public_prompts(self) -> None:
        """Load all public prompts from the prompts directories."""
        for prompts_dir in [self.prompts_dir, self.data_prompts_dir]:
            if not os.path.exists(prompts_dir):
                logger.warning(f"Prompts directory does not exist: {prompts_dir}")
                continue

            logger.info(f"Loading public prompts from directory: {prompts_dir}")
            all_files = os.listdir(prompts_dir)
            logger.info(f"Found {len(all_files)} files in prompts directory: {all_files}")

            for filename in all_files:
                # Skip directories and files starting with underscore
                if os.path.isdir(os.path.join(prompts_dir, filename)) or filename.startswith('_'):
                    logger.debug(f"Skipping file/directory: {filename} (directory or starts with underscore)")
                    continue

                if filename.endswith('.json'):
                    try:
                        file_path = os.path.join(prompts_dir, filename)
                        logger.debug(f"Loading prompt from file: {file_path}")
                        prompt = await self.template_loader.load_from_file(file_path)
                        if prompt:
                            self.public_prompts[prompt.name] = prompt
                            logger.debug(f"Loaded public prompt: {prompt.name}")
                        else:
                            logger.warning(f"Failed to load prompt from file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error loading public prompt {filename}: {str(e)}")

    async def _load_shared_prompts(self) -> None:
        """Load all shared prompts from the prompts directories."""
        for prompts_dir in [self.prompts_dir, self.data_prompts_dir]:
            if not os.path.exists(prompts_dir):
                continue

            for filename in os.listdir(prompts_dir):
                # Only process files starting with _share-
                if not filename.startswith('_share-') or not filename.endswith('.json'):
                    continue

                try:
                    file_path = os.path.join(prompts_dir, filename)
                    prompt = await self.template_loader.load_from_file(file_path)
                    if prompt and prompt.id:
                        self.shared_prompts[prompt.id] = prompt
                        logger.debug(f"Loaded shared prompt: {prompt.name} (ID: {prompt.id})")
                except Exception as e:
                    logger.error(f"Error loading shared prompt {filename}: {str(e)}")

    async def _load_all_private_prompts(self) -> None:
        """Load private prompts for all users."""
        users_dir = os.path.join(self.prompts_dir, "users")
        if not os.path.exists(users_dir):
            os.makedirs(users_dir, exist_ok=True)
            return

        for username in os.listdir(users_dir):
            user_dir = os.path.join(users_dir, username)
            if not os.path.isdir(user_dir):
                continue

            await self._load_private_prompts_for_user(username)

    async def _load_private_prompts_for_user(self, username: str) -> None:
        """
        Load private prompts for a specific user.

        Args:
            username: The username to load prompts for
        """
        user_dir = os.path.join(self.prompts_dir, "users", username)
        if not os.path.exists(user_dir):
            return

        # Initialize user's prompts dictionary
        if username not in self.private_prompts:
            self.private_prompts[username] = {}

        for filename in os.listdir(user_dir):
            # Only process files with the .json extension
            if not filename.endswith('.json'):
                continue

            # Extract prompt name from filename (ignoring timestamp prefix)
            prompt_name = filename.split('_', 1)[-1].split('.')[0]

            try:
                file_path = os.path.join(user_dir, filename)
                prompt = await self.template_loader.load_from_file(file_path)
                if prompt:
                    self.private_prompts[username][prompt_name] = prompt
                    logger.debug(f"Loaded private prompt for {username}: {prompt_name}")
            except Exception as e:
                logger.error(f"Error loading private prompt {filename} for {username}: {str(e)}")

    async def get_public_prompts(self) -> List[PromptInfo]:
        """
        Get a list of all public prompts.

        Returns:
            List of prompt info objects
        """
        return [
            PromptInfo(
                name=prompt.name,
                description=prompt.description,
                arguments=prompt.arguments,
                source=PromptSource(type="public", path=f"prompts/{prompt.name}.json")
            )
            for prompt in self.public_prompts.values()
        ]

    async def get_user_prompts(self, username: str) -> List[PromptInfo]:
        """
        Get a list of all prompts accessible to a user.
        This includes the user's private prompts and shared prompts they have access to.
        Public prompts are not included as they are accessible through a separate endpoint.

        Args:
            username: The username to get prompts for

        Returns:
            List of prompt info objects
        """
        result = []

        # Add private prompts
        if username in self.private_prompts:
            for prompt in self.private_prompts[username].values():
                # Find the actual filename with timestamp
                prompt_files = []
                user_dir = os.path.join(self.prompts_dir, "users", username)
                if os.path.exists(user_dir):
                    for filename in os.listdir(user_dir):
                        if filename.endswith(f"_{prompt.name}.json") or filename == f"{prompt.name}.json":
                            prompt_files.append(filename)

                # Use the most recent file if multiple exist
                actual_filename = prompt.name + ".json"
                if prompt_files:
                    # Sort by timestamp (descending)
                    prompt_files.sort(reverse=True)
                    actual_filename = prompt_files[0]

                # Get the path relative to CONFIG_MAIN_FILE_PATH
                path_from_config = os.path.join("prompts", "users", username, actual_filename)

                result.append(PromptInfo(
                    name=prompt.name,
                    description=prompt.description,
                    arguments=prompt.arguments,
                    source=PromptSource(type="private", path=path_from_config)
                ))

        # Add shared prompts the user has access to
        user_shared_prompts = await self._get_user_shared_prompts(username)
        for prompt in user_shared_prompts:
            result.append(PromptInfo(
                name=prompt.name,
                description=prompt.description,
                arguments=prompt.arguments,
                source=PromptSource(type="shared", path=f"prompts/_share-{prompt.id}.json"),
                id=prompt.id,
                owner=prompt.owner
            ))

        return result

    async def _get_user_shared_prompts(self, username: str) -> List[PromptTemplate]:
        """
        Get a list of shared prompts a user has access to.

        Args:
            username: The username to get shared prompts for

        Returns:
            List of prompt templates
        """
        # Implementation for getting shared prompts would go here
        # This would typically involve checking a user's permissions
        return []

    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any], username: str, prompt_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Execute a prompt with the given arguments.

        Args:
            prompt_name: The name of the prompt to execute
            arguments: The arguments to fill in the prompt
            username: The username executing the prompt
            prompt_id: Optional ID for shared prompts

        Returns:
            The processed messages with variables filled in
        """
        # Find the prompt template
        prompt = None

        # If prompt_id is provided, look for a shared prompt
        if prompt_id:
            prompt = self.shared_prompts.get(prompt_id)
        # Otherwise look for a public or private prompt by name
        elif prompt_name:
            # Check public prompts first
            prompt = self.public_prompts.get(prompt_name)

            # If not found, check private prompts
            if not prompt and username in self.private_prompts:
                prompt = self.private_prompts[username].get(prompt_name)

        if not prompt:
            return []

        # Execute the prompt with the provided arguments
        return await self.template_executor.execute(prompt, arguments)

    async def create_private_prompt(self, username: str, prompt_data: Dict[str, Any]) -> Optional[PromptTemplate]:
        """
        Create a private prompt for a user.

        Args:
            username: The username to create the prompt for
            prompt_data: The prompt data

        Returns:
            The created prompt, or None if creation failed
        """
        try:
            # Create user directory if it doesn't exist
            user_dir = os.path.join(self.prompts_dir, "users", username)
            os.makedirs(user_dir, exist_ok=True)

            # Set the owner field to the username
            prompt_data["owner"] = username

            # Create a PromptTemplate object from the data
            prompt = PromptTemplate(**prompt_data)

            # Get current Unix timestamp
            timestamp = int(time.time())

            # Save the prompt to a file with timestamp prefix
            file_path = os.path.join(user_dir, f"{timestamp}_{prompt.name}.json")

            # Convert to dict for saving
            prompt_dict = prompt.dict()

            # Write to file
            with open(file_path, "w") as f:
                json.dump(prompt_dict, f, indent=4)

            # Initialize user's prompts dictionary if it doesn't exist
            if username not in self.private_prompts:
                self.private_prompts[username] = {}

            # Add to in-memory collection
            self.private_prompts[username][prompt.name] = prompt

            logger.info(f"Created/updated private prompt '{prompt.name}' for user '{username}' at {file_path}")

            return prompt
        except Exception as e:
            logger.error(f"Error creating private prompt for {username}: {str(e)}")
            return None

    async def create_shared_prompt(self, username: str, prompt_data: Dict[str, Any]) -> Optional[PromptTemplate]:
        """
        Create a shared prompt.

        Args:
            username: The username creating the prompt
            prompt_data: The prompt data

        Returns:
            The created prompt, or None if creation failed
        """
        # Implementation for creating shared prompts would go here
        return None

    async def share_prompt_with_user(self, target_username: str, prompt_id: str) -> bool:
        """
        Share a prompt with another user by adding the prompt ID to their config's 'prompts' list.
        """
        from mcpo_simple_server.auth.dependencies import config_manager

        if not config_manager:
            logger.error("Config manager not set in auth dependencies")
            return False

        user_data = config_manager.users.get_user(target_username)
        if not user_data:
            logger.error(f"User '{target_username}' not found when sharing prompt.")
            return False

        # Add the prompt ID to the user's prompts list
        prompts = user_data.get("prompts", [])
        entry = f"_share-{prompt_id}"
        if entry not in prompts:
            prompts.append(entry)
            user_data["prompts"] = prompts
            success = await config_manager.users.add_user(target_username, user_data)
            if not success:
                logger.error(f"Failed to update prompts for user '{target_username}' in config.")
            return success
        else:
            logger.info(f"User '{target_username}' already has access to prompt '{prompt_id}'.")
            return True

    async def delete_private_prompt(self, username: str, prompt_name: str) -> bool:
        """
        Delete a private prompt.

        Args:
            username: The username that owns the prompt
            prompt_name: The name of the prompt to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        user_dir = os.path.join(self.prompts_dir, "users", username)
        if not os.path.exists(user_dir):
            return False
        deleted = False
        for filename in os.listdir(user_dir):
            if filename.endswith(f"_{prompt_name}.json") or filename == f"{prompt_name}.json":
                file_path = os.path.join(user_dir, filename)
                try:
                    os.remove(file_path)
                    deleted = True
                except OSError as e:
                    logger.error(f"Failed to delete private prompt file {file_path}: {str(e)}")
        # Remove from in-memory prompts
        if username in self.private_prompts and prompt_name in self.private_prompts[username]:
            del self.private_prompts[username][prompt_name]
        return deleted

    async def delete_shared_prompt(self, username: str, prompt_id: str) -> bool:
        """
        Delete a shared prompt.

        Args:
            username: The username that owns the prompt
            prompt_id: The ID of the prompt to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        filename = f"_share-{prompt_id}.json"
        deleted = False
        # Remove prompt file from prompt directories
        for prompts_dir in [self.prompts_dir, self.data_prompts_dir]:
            file_path = os.path.join(prompts_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted = True
                except OSError as e:
                    logger.error(f"Failed to delete shared prompt file {file_path}: {str(e)}")
        # Remove from in-memory collection
        if prompt_id in self.shared_prompts:
            del self.shared_prompts[prompt_id]
        # Remove entries from all user configs
        from mcpo_simple_server.auth.dependencies import config_manager
        user_data = config_manager.users.get_all_users()
        for user, data in user_data.items():
            prompts_list = data.get("prompts", [])
            entry = f"_share-{prompt_id}"
            if entry in prompts_list:
                prompts_list.remove(entry)
                data["prompts"] = prompts_list
                success = await config_manager.users.add_user(user, data)
                if not success:
                    logger.error(f"Failed to remove shared prompt entry for user '{user}' in config.")
        return deleted
