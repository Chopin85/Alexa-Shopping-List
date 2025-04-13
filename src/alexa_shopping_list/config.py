"""Configuration management using environment variables."""

import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    amazon_url: str
    cookie_path: str
    log_level: str

def load_config() -> AppConfig:
    """Loads configuration from environment variables."""
    load_dotenv() # Load .env file

    amazon_url = os.getenv('AMAZON_URL')
    cookie_path = os.getenv('COOKIE_PATH')
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Validation
    if not amazon_url:
        logger.critical("Missing required environment variable: AMAZON_URL")
        raise EnvironmentError("Missing required environment variable: AMAZON_URL")
    if not cookie_path:
        logger.critical("Missing required environment variable: COOKIE_PATH")
        raise EnvironmentError("Missing required environment variable: COOKIE_PATH")

    # Validate log level
    if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        logger.warning(f"Invalid LOG_LEVEL '{log_level}', defaulting to INFO.")
        log_level = 'INFO'

    logger.info("Configuration loaded.")
    logger.debug(
        f"Config: URL={amazon_url}, CookiePath={cookie_path}, LogLevel={log_level}"
    )

    return AppConfig(
        amazon_url=amazon_url,
        cookie_path=cookie_path,
        log_level=log_level,
    )
