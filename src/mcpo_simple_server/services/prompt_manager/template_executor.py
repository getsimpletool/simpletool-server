"""
Prompt Template Executor Module

This module provides functionality for executing prompt templates with variables.
"""
import copy
from typing import Dict, List, Any
from loguru import logger
from jinja2 import Template

from mcpo_simple_server.services.prompt_manager.models.prompts import PromptTemplate, PromptMessage, TextContent

class PromptTemplateExecutor:
    """
    Executor for prompt templates with variable substitution.
    """

    async def execute(self, prompt: PromptTemplate, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a prompt with the given arguments.

        Args:
            prompt: The prompt template to execute
            arguments: The arguments to fill in the prompt

        Returns:
            The processed messages with variables filled in
        """
        try:
            # Create a deep copy of the messages to avoid modifying the original
            messages = copy.deepcopy(prompt.messages)
            # Process each message
            processed_messages = []
            for message in messages:
                processed_message = await self._process_message(message, arguments)
                processed_messages.append(processed_message)
            return processed_messages
        except Exception as e:
            logger.error(f"Error executing prompt {prompt.name}: {str(e)}")
            return []

    async def _process_message(self, message: PromptMessage, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single message with the given arguments.

        Args:
            message: The message to process
            arguments: The arguments to fill in the message

        Returns:
            The processed message with variables filled in
        """
        # Convert the message to a dictionary
        message_dict = message.dict()
        # Process the content if it's a text content
        if isinstance(message.content, TextContent):
            # Fill in variables using Jinja2
            template = Template(message.content.text)
            filled_text = template.render(**arguments)
            # Update the message content
            message_dict["content"]["text"] = filled_text
        elif isinstance(message.content, dict) and "text" in message.content:
            # Fill in variables using Jinja2
            template = Template(message.content["text"])
            filled_text = template.render(**arguments)
            # Update the message content
            message_dict["content"]["text"] = filled_text
        return message_dict
