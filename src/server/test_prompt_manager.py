"""
Test script for the refactored prompt_manager module.
"""
import asyncio
import logging

from server.services.prompt_manager import PromptManager
from server.config import CONFIG_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_prompt_manager():
    """Test the prompt manager functionality."""
    logger.info("Testing prompt manager...")
    # Create a prompt manager instance
    pm = PromptManager(CONFIG_PATH)
    # Load all prompts
    await pm.load_all_prompts()
    # Print loaded prompts
    logger.info(f"Loaded public prompts: {list(pm.public_prompts.keys())}")
    logger.info(f"Loaded shared prompts: {len(pm.shared_prompts)}")
    logger.info(f"Loaded private prompts for users: {list(pm.private_prompts.keys())}")
    return True

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_prompt_manager())
    logger.info("Test completed successfully!")
