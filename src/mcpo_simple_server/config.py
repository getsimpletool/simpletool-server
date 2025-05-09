"""
Global configuration module for the server.

This module provides central configuration variables used throughout the application.
"""
import os
import pathlib
from mcpo_simple_server.logger import logger
from mcpo_simple_server._version import __version__

# Define application paths
APP_PATH = pathlib.Path(os.getcwd())
APP_VERSION = str(__version__)
APP_NAME = "MCPoSimpleServer"
CONFIG_STORAGE_TYPE = os.getenv("CONFIG_STORAGE_TYPE", "files")
CONFIG_STORAGE_PATH = os.getenv("CONFIG_STORAGE_PATH", str(APP_PATH / "data" / "config"))


# If the path points to a file (config.json), extract the directory path
if CONFIG_STORAGE_PATH.endswith(".json"):
    CONFIG_MAIN_FILE_PATH = CONFIG_STORAGE_PATH
    CONFIG_STORAGE_PATH = os.path.dirname(CONFIG_STORAGE_PATH)
else:
    # If it's already a directory, append config.json for the file path
    CONFIG_MAIN_FILE_PATH = os.path.join(CONFIG_STORAGE_PATH, "config.json")


# Create the config directory if it doesn't exist
try:
    if not os.path.exists(CONFIG_STORAGE_PATH):
        os.makedirs(CONFIG_STORAGE_PATH)
        logger.info(f"📁 Config directory created: {CONFIG_STORAGE_PATH}")
except Exception as e:
    logger.error(f"Failed to create config directory at {CONFIG_STORAGE_PATH}: {str(e)}")
