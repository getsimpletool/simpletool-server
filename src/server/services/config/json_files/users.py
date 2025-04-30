"""
File-Based Users Config Service Module

This module provides the UsersConfigFileService class for managing user configurations
where each user is stored in a separate JSON file.
"""

import json
import os
from typing import Dict, Any, Optional
from loguru import logger
from server.config import CONFIG_STORAGE_PATH
from server.services.config import ConfigService
from server.services.config.models.memory import MemoryDBModel, UserConfigModel


class UsersConfigFileService:
    """
    Manages users configurations where each user is stored in a separate JSON file.
    Each user is stored in a separate JSON file named <username>.json in the users directory.
    """

    def __init__(self, parent: ConfigService):
        """
        Initialize the UsersConfigFileService.

        Args:
            parent: Parent ConfigService instance
        """
        self.parent = parent
        self.memory: MemoryDBModel = self.parent.memory
        self.users_dir = os.path.join(CONFIG_STORAGE_PATH, "users")

        # Create the users directory if it doesn't exist
        try:
            if not os.path.exists(self.users_dir):
                os.makedirs(self.users_dir)
                logger.info(f"📁 Users directory created: {self.users_dir}")
        except Exception as e:
            logger.error(f"Failed to create users directory at {self.users_dir}: {str(e)}")

        # Init Clean Cache of user data to avoid reading from disk for every request
        self.memory.users = {}

    async def refresh_users_cache(self, username: Optional[str] = None):
        """Refresh the users cache. If username is provided, refresh only that user; otherwise, refresh all."""
        async with self.parent.cache_lock_users:
            if username:
                # Remove from cache if exists
                self.memory.users.pop(username, None)
                user_path = os.path.join(self.users_dir, f"{username}.json")
                if os.path.exists(user_path):
                    try:
                        with open(user_path, 'r', encoding='utf-8') as f:
                            user_data_dict = json.load(f)
                            from server.services.config.models.memory import UserConfigModel
                            user_config = UserConfigModel(**user_data_dict)
                            self.memory.users[username] = user_config
                    except Exception as e:
                        logger.error(f"Error refreshing user cache for {username}: {str(e)}")
            else:
                self.memory.users.clear()
                # Scan the users directory for JSON files
                if os.path.exists(self.users_dir):
                    for filename in os.listdir(self.users_dir):
                        if filename.endswith('.json'):
                            user_file_path = os.path.join(self.users_dir, filename)
                            try:
                                with open(user_file_path, 'r', encoding='utf-8') as f:
                                    user_data_dict = json.load(f)
                                    username = filename[:-5]  # Remove .json extension
                                    from server.services.config.models.memory import UserConfigModel
                                    user_config = UserConfigModel(**user_data_dict)
                                    self.memory.users[username] = user_config
                            except Exception as e:
                                logger.error(f"Error refreshing user cache for {filename}: {str(e)}")

    def get_all_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all user configurations.

        Returns:
            Dictionary of user configurations
        """
        if self.memory.users is None:
            return {}
        else:
            return {item[0]: item[1].model_dump() for item in self.memory.users.items()}

    async def load_users_configs(self) -> Dict[str, Any]:
        """
        Scan the users directory for user files.

        Returns:
            The loaded configuration dictionary
        """
        # Scan the users directory and load all user files
        await self.refresh_users_cache()

        logger.info(f"Loaded user configurations for {len(self.get_all_users())} users")
        return self.get_all_users()

    async def save_user_configfile(self, username: str, user_data: Dict[str, Any]) -> bool:
        """
        Save a user's data to their individual JSON file.

        Args:
            username: The username
            user_data: The user data to save

        Returns:
            True if successful, False otherwise
        """
        # Ensure the users directory exists
        try:
            os.makedirs(self.users_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create users directory at {self.users_dir}: {str(e)}")
            return False

        user_path = os.path.join(self.users_dir, f"{username}.json")

        try:
            with open(user_path, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=4)
            logger.info(f"Successfully saved user data to {user_path}")
            # Always refresh cache for this user after saving
            await self.refresh_users_cache(username)
            return True
        except IOError as e:
            logger.error(f"Error saving user file for {username}: {str(e)}")
            return False

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration for a specific user.

        Args:
            username: The username to look up

        Returns:
            The user configuration dictionary or None if not found
        """
        # Special logic for admin account recovery

        admin_env_pw = os.getenv("ADMIN_DEFAULT_PASSWORD")
        user_path = os.path.join(self.users_dir, f"{username}.json")

        # If user is admin and admin.json does not exist
        if username == "admin" and not os.path.exists(user_path):
            from server.services.config.models.memory import UserConfigModel
            from server.auth.security import get_password_hash
            if admin_env_pw:
                # Create minimal admin user with password from env
                user_data = {
                    "username": "admin",
                    "hashed_password": get_password_hash(admin_env_pw),
                    "admin": True,
                    "disabled": False,
                    "api_keys": [],
                    "env": {},
                    "mcpServers": {}
                }
                # Save to file for persistence
                await self.save_user_configfile("admin", user_data)
                self.memory.users["admin"] = UserConfigModel(**user_data)
                return user_data
            else:
                # Default fallback: password is 'admin'
                from server.auth.security import get_password_hash
                user_data = {
                    "username": "admin",
                    "hashed_password": get_password_hash("admin"),
                    "admin": True,
                    "disabled": False,
                    "api_keys": [],
                    "env": {},
                    "mcpServers": {}
                }
                await self.save_user_configfile("admin", user_data)
                self.memory.users["admin"] = UserConfigModel(**user_data)
                return user_data

        # First check the cache
        if self.memory.users is not None and username in self.memory.users:
            return self.memory.users[username].model_dump()

        # If not in cache, try to load from file
        if os.path.exists(user_path):
            try:
                with open(user_path, 'r', encoding='utf-8') as f:
                    user_data_dict = json.load(f)
                    # --- ADMIN PASSWORD OVERRIDE LOGIC ---
                    if username == "admin" and admin_env_pw:
                        from server.auth.security import get_password_hash  # pylint: disable=C0415
                        # Replace hashed_password with hash from env
                        user_data_dict["hashed_password"] = get_password_hash(admin_env_pw)
                    # Validate and cache user configuration
                    try:
                        from server.services.config.models.memory import UserConfigModel  # pylint: disable=C0415, W0404
                        user_config = UserConfigModel(**user_data_dict)
                        self.memory.users[username] = user_config
                        return user_config.model_dump()
                    except Exception as e:
                        logger.error(f"Error validating user data for {username} in get_user: {str(e)}")
                        return None
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading user file for {username}: {str(e)}")

        return None

    async def add_user(self, username: str, user_data: Dict[str, Any]) -> bool:
        """
        Add or update a user configuration.

        Args:
            username: The username
            user_data: User data including hashed_password, admin status, etc.

        Returns:
            True if the operation was successful, False otherwise
        """
        # Validate user data using model validation
        try:
            UserConfigModel(**user_data)
        except Exception as e:
            logger.error(f"Invalid user data for user '{username}': {str(e)}")
            return False

        # Save to individual file
        success = await self.save_user_configfile(username, user_data)

        if success:
            # Update the cache
            async with self.parent.cache_lock_users:
                if self.memory.users is not None:
                    self.memory.users[username] = UserConfigModel(**user_data)
            logger.info(f"User '{username}' configuration saved successfully")

        return success

    async def remove_user(self, username: str) -> bool:
        """
        Remove a user configuration.

        Args:
            username: The username to remove

        Returns:
            True if the user was removed, False if it didn't exist or there was an error
        """
        user_path = os.path.join(self.users_dir, f"{username}.json")

        if not os.path.exists(user_path) and (self.memory.users is None or username not in self.memory.users):
            logger.warning(f"User '{username}' not found, cannot remove")
            return False

        # Remove from cache
        async with self.parent.cache_lock_users:
            if self.memory.users is not None and username in self.memory.users:
                del self.memory.users[username]

        # Remove the file
        try:
            if os.path.exists(user_path):
                os.remove(user_path)
        except IOError as e:
            logger.error(f"Error removing user file for {username}: {str(e)}")
            return False

        logger.info(f"User '{username}' removed successfully")
        return True

    async def update_user_field(self, username: str, field: str, value: Any) -> bool:
        """
        Update a specific field for a user.

        Args:
            username: The username
            field: The field to update
            value: The new value

        Returns:
            True if the operation was successful, False otherwise
        """
        user = await self.get_user(username)
        if not user:
            logger.warning(f"User '{username}' not found, cannot update field '{field}'")
            return False

        # Update the field
        user[field] = value

        # Save the updated user data
        return await self.add_user(username, user)

    async def add_api_key(self, username: str, hashed_key: str) -> bool:
        """
        Add a hashed API key to a user's configuration.

        Args:
            username: The username
            hashed_key: The hashed API key to add

        Returns:
            True if the operation was successful, False otherwise
        """
        user = await self.get_user(username)
        if not user:
            logger.warning(f"User '{username}' not found, cannot add API key")
            return False

        # Initialize api_keys list if it doesn't exist
        if "api_keys" not in user:
            user["api_keys"] = []

        # Add the hashed key
        user["api_keys"].append(hashed_key)

        # Save the updated user data
        return await self.add_user(username, user)

    async def remove_api_key(self, username: str, hashed_key: str) -> bool:
        """
        Remove a hashed API key from a user's configuration.

        Args:
            username: The username
            hashed_key: The hashed API key to remove

        Returns:
            True if the operation was successful, False otherwise
        """
        user = await self.get_user(username)
        if not user:
            logger.warning(f"User '{username}' not found, cannot remove API key")
            return False

        # Check if the user has API keys
        if "api_keys" not in user or not user["api_keys"]:
            logger.warning(f"User '{username}' has no API keys, cannot remove")
            return False

        # Check if the hashed key exists
        if hashed_key not in user["api_keys"]:
            logger.warning(f"API key not found for user '{username}', cannot remove")
            return False

        # Remove the hashed key
        user["api_keys"].remove(hashed_key)

        # Save the updated user data
        return await self.add_user(username, user)
