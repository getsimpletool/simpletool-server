import sys
import os
from loguru import logger
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Configure loguru
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
# Remove default handler
logger.remove()
# Customize level colors
logger.level("INFO", color="<green>")

# Define format strings for different log levels


# Add console handlers with different formats per level
INFO_FORMAT = "<level>{level.name}</level>:     {message}"
logger.add(sys.stderr, format=INFO_FORMAT, level="INFO", filter=lambda record: record["level"].name == "INFO", colorize=True)
DEBUG_FORMAT = "<level>{level.name}</level>:    {message}"
logger.add(sys.stderr, format=DEBUG_FORMAT, level="DEBUG", filter=lambda record: record["level"].name == "DEBUG", colorize=True)
ERROR_FORMAT = "<level>{level.name}</level>:    [<level>!!</level>] {message}"
logger.add(sys.stderr, format=ERROR_FORMAT, level="ERROR", filter=lambda record: record["level"].name == "ERROR", colorize=True)
CRITICAL_FORMAT = "<level>{level.name}</level>: [<level>!!!</level>] {message}"
logger.add(sys.stderr, format=CRITICAL_FORMAT, level="CRITICAL", filter=lambda record: record["level"].name == "CRITICAL", colorize=True)
WARNING_FORMAT = "<level>{level.name}</level>:  [<level>!</level>] {message}"
logger.add(sys.stderr, format=WARNING_FORMAT, level="WARNING", filter=lambda record: record["level"].name == "WARNING", colorize=True)
DEFAULT_FORMAT = "<level>{level.name}</level>: {message}"
logger.add(sys.stderr, format=DEFAULT_FORMAT, level=log_level, filter=lambda record: record["level"].name not in ("INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"), colorize=True)
