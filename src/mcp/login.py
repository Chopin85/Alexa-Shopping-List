"""Script to force login/re-login and generate the Alexa cookie file."""

import logging
import sys
import asyncio
import os
from pathlib import Path

# Add src directory to path if running directly
# This helps Python find the alexa_shopping_list package
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Go up one level from src/mcp
if os.path.isdir(src_dir) and src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from alexa_shopping_list.config import load_config
    from alexa_shopping_list.auth import ensure_authentication
except ImportError as e:
    print(f"Error importing application modules: {e}", file=sys.stderr)
    print("Ensure you are running from the project root directory or have installed the package.", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)

async def main():
    """Main function to handle the login process."""
    try:
        config = load_config()
    except EnvironmentError as e:
        logging.basicConfig(level=logging.INFO) # Basic logging for error message
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)

    # Setup logging based on config
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    if log_level > logging.DEBUG:
        # Suppress noisy library logs unless debugging
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("selenium").setLevel(logging.INFO)
        logging.getLogger("webdriver_manager").setLevel(logging.INFO)

    logger.info("Starting Alexa authentication process...")

    cookie_file = Path(config.cookie_path)

    # Check if cookie file exists and delete it to force re-auth
    if cookie_file.is_file():
        logger.info(f"Existing cookie file found at '{config.cookie_path}'. Deleting to force re-authentication.")
        try:
            cookie_file.unlink()
        except OSError as e:
            logger.error(f"Error deleting existing cookie file '{config.cookie_path}': {e}")
            # Decide if we should proceed or exit? For now, let's try to proceed.
            logger.warning("Proceeding with authentication attempt despite cookie deletion error.")

    # Call the authentication function (will trigger browser login)
    try:
        success = await ensure_authentication(config)

        if success:
            logger.info("Authentication successful. Cookie file should be saved.")
        else:
            logger.error("Authentication process failed. See previous logs for details.")
            sys.exit(1) # Exit with error if auth failed

    except Exception as e:
        logger.exception(f"An unexpected error occurred during authentication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Use basic logger if setup failed earlier
        logging.getLogger().info("Login process interrupted by user.")
        sys.exit(0)
