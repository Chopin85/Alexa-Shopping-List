"""Configuration management using environment variables."""

import os
import logging
from dataclasses import dataclass
from typing import Optional
import sys

logger = logging.getLogger(__name__)

# Configuration for the API Server (inside Docker)
COOKIE_PATH = "/app/data/cookies.json"

# Amazon URL for your locale (e.g., amazon.com, amazon.co.uk)
# Needs to match the one used for login to construct API paths correctly.
AMAZON_URL = "https://www.amazon.com"

# Logging level for the API server
LOG_LEVEL = "INFO"

# Port the API server listens on inside the container
API_PORT = 8000

# --- Derived --- #
LOG_LEVEL_INT = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

#-def load_config(project_root: Optional[str] = None) -> AppConfig:
#-    """Loads configuration from .env file and environment variables."""
#-    # Construct the path to the .env file
#-    if project_root is None:
#-        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#-    dotenv_path = os.path.join(project_root, '.env')
#-
#-    logger.debug(f"Attempting to load .env file from: {dotenv_path}")
#-
#-    # Use find_dotenv to locate the .env file reliably
#-    dotenv_path_found = find_dotenv(filename='.env', raise_error_if_not_found=False)
#-
#-    if dotenv_path_found:
#-        logger.info(f"Loading environment variables from: {dotenv_path_found}")
#-        load_dotenv(dotenv_path=dotenv_path_found)
#-    else:
#-        logger.warning(".env file not found. Relying on environment variables or defaults.")
#-
#-    # Load values, providing defaults
#-    amazon_url = os.getenv("AMAZON_URL")
#-    cookie_path = os.getenv("COOKIE_PATH", "./alexa_cookie.pickle") # Default local path
#-    log_level = os.getenv("LOG_LEVEL", "INFO")
#-    api_port_str = os.getenv("API_PORT", "8000")
#-
#-    # Basic validation
#-    if not amazon_url:
#-        raise EnvironmentError("AMAZON_URL environment variable is not set.")
#-    if not cookie_path:
#-        logger.warning("COOKIE_PATH not set, using default '{cookie_path}'.")
#-    if log_level.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
#-        logger.warning(f"Invalid LOG_LEVEL '{log_level}', using default 'INFO'.")
#-        log_level = "INFO"
#-
#-    try:
#-        api_port = int(api_port_str)
#-        if not (1024 <= api_port <= 65535):
#-             logger.warning(f"Invalid API_PORT '{api_port_str}', using default 8000.")
#-             api_port = 8000
#-    except ValueError:
#-        logger.warning(f"Invalid API_PORT '{api_port_str}', using default 8000.")
#-        api_port = 8000
#-
#-    return AppConfig(
#-        amazon_url=amazon_url,
#-        cookie_path=cookie_path,
#-        log_level=log_level,
#-        api_port=api_port
#-    )
