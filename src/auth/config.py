# Configuration for the Auth (Login) Script
import logging

# Amazon URL for your locale (e.g., amazon.com, amazon.co.uk)
AMAZON_URL = "https://www.amazon.fr"

# Path where the login script temporarily saves the cookie file locally
# before sending it to the API container.
LOCAL_TEMP_COOKIE_PATH = "./alexa_cookie.pickle"

# Logging level for the login script
LOG_LEVEL = "INFO"

# Host and Port of the running API container to send cookies to
# Assumes API container is accessible on localhost from where login script runs
API_HOST = "localhost"
API_PORT = 8800

# --- Derived --- #
LOG_LEVEL_INT = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
API_COOKIE_ENDPOINT = f"http://{API_HOST}:{API_PORT}/auth/cookies"
