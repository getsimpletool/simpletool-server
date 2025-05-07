"""
Prompt Template Loader Module

This module provides functionality for loading prompt templates from files.
"""
import json
import aiofiles
from typing import Optional
from loguru import logger

from mcpo_simple_server.services.prompt_manager.models.prompts import PromptTemplate


class PromptTemplateLoader:
    """
    Loader for prompt templates from various sources.
    """

    async def load_from_file(self, file_path: str) -> Optional[PromptTemplate]:
        """
        Load a prompt template from a file.

        Args:
            file_path: Path to the prompt file

        Returns:
            The loaded prompt template, or None if loading failed
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

                logger.debug(f"Loaded prompt data from {file_path}: {data.get('name', 'NO_NAME_FOUND')}")

                # Validate required fields
                if "name" not in data:
                    logger.error(f"Missing 'name' field in prompt file: {file_path}")
                    return None
                if "messages" not in data:
                    logger.error(f"Missing 'messages' field in prompt file: {file_path}")
                    return None

                # Convert to PromptTemplate
                prompt = PromptTemplate(**data)
                logger.debug(f"Successfully created PromptTemplate with name: {prompt.name}")
                return prompt
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in prompt file {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error loading prompt from {file_path}: {str(e)}")
            return None

    async def load_from_string(self, content: str) -> Optional[PromptTemplate]:
        """
        Load a prompt template from a string.

        Args:
            content: JSON string containing the prompt template

        Returns:
            The loaded prompt template, or None if loading failed
        """
        try:
            data = json.loads(content)

            # Validate required fields
            if "name" not in data:
                logger.error("Missing 'name' field in prompt data")
                return None
            if "messages" not in data:
                logger.error("Missing 'messages' field in prompt data")
                return None

            # Convert to PromptTemplate
            prompt = PromptTemplate(**data)
            return prompt
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in prompt data: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error loading prompt from string: {str(e)}")
            return None
