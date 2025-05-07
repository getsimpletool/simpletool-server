"""
Global configuration module for the server.

This module provides central configuration variables used throughout the application.
"""
import os
import pathlib

# Import version from central location
from mcpo_simple_server._version import __version__

# Define application paths
APP_PATH = pathlib.Path(os.getcwd())
APP_VERSION = os.getenv("APP_VERSION", __version__)
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
