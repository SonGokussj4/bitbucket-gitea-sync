import os
import sys

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configure the logger
logger.remove()  # Remove the default logger configuration
logger.add(sys.stderr, level=LOG_LEVEL)  # Add new configuration with the specified log level
