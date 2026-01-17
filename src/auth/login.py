"""Script to force login/re-login, generate the Alexa cookie file, and send it to the API container."""

import logging
import sys
import asyncio
import os
from pathlib import Path
import requests  # Needed for POSTing cookies
from typing import List, Dict # For cookie formatting type hint
import nodriver as uc
import json # To save cookies locally
import datetime

try:
    # Import the local auth config
    from . import config as auth_config
except ImportError as e:
    print(f"Error importing local config: {e}", file=sys.stderr)
    print("Ensure you are running from the project root or have activated the correct environment.", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger("login_script")  # Renamed logger for clarity

# Constructing URL based on signIn.js structure but with our return_to target
direct_signin_url = "https://www.amazon.fr/"

async def post_cookies_to_api(cookies_for_requests: List[Dict]):
    """Posts the cookies (in requests format) to the API endpoint as JSON."""
    # Post to API
    logger.info(f"Attempting to send cookies as JSON to API endpoint: {auth_config.API_COOKIE_ENDPOINT}")
    try:
        # Send the list of cookie dictionaries as JSON
        response = requests.post(auth_config.API_COOKIE_ENDPOINT, json=cookies_for_requests, timeout=15)
        response.raise_for_status()
        logger.info(f"Successfully sent cookies to API. Status: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Could not connect to the API server at {auth_config.API_COOKIE_ENDPOINT}. Is it running?")
        logger.error(f"Error: {conn_err}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while sending cookie file to {auth_config.API_COOKIE_ENDPOINT}.")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error sending cookie file to API: {req_err}")
        if req_err.response is not None:
            logger.error(f"API Response Status: {req_err.response.status_code}")
            logger.error(f"API Response Body: {req_err.response.text}")
    except Exception as upload_err:
        logger.error(f"Unexpected error during cookie file upload: {upload_err}", exc_info=True)
    return False

async def main():
    """Opens browser to sign-in page, waits for manual login, then extracts cookies."""
    logging.basicConfig(
        level=auth_config.LOG_LEVEL_INT,
        format='%(asctime)s - %(name)s [%(levelname)s] %(message)s',
        stream=sys.stdout
    )

    logger.info("Starting Alexa authentication process with nodriver...")

    browser = None
    page = None

    # Flag for final outcome
    cookie_upload_success = False

    try:
        # --- Step 1: Open Browser to Sign-in Page --- #
        logger.info("Initializing nodriver browser...")
        browser = await uc.start() # Headless by default
        page = await browser.get(direct_signin_url)
        logger.info(f"Navigated directly to: {direct_signin_url}")

        # --- Step 2: Wait for Manual Login --- #
        print("-" * 60)
        print("*** MANUAL LOGIN REQUIRED ***")
        print("A browser window should have opened to the Amazon sign-in page.")
        print("Please log in manually within that browser window.")
        print("If you encounter 2FA or CAPTCHA, complete those steps in the browser.")
        input("--> Press Enter here AFTER you have successfully logged in... ")
        print("-" * 60)
        logger.info("User indicated manual login complete. Attempting to extract cookies.")

        # --- Step 5: Extract and Post Cookies ---
        # Always attempt cookie extraction after verification steps or manual intervention pause
        # The login_success flag now only indicates if the *automated* part seemed to succeed.
        # The login_and_upload_success flag tracks the actual cookie extraction/upload result.
        logger.info("Proceeding to Step 5: Extract and Post Cookies attempt...")

        # --- Start Cookie Extraction Logic --- #
        logger.info("Attempting to extract cookies...")
        # Use the documented way to get all cookies for the current context/page
        # Access cookies through the browser object, not the page/tab object
        raw_cookies = await browser.cookies.get_all(requests_cookie_format=True)

        if not raw_cookies:
            logger.error("Failed to extract cookies after manual login attempt.")
            # Add a re-check here based on greeting if possible (might be useful even after manual intervention)
            try:
                final_greeting = await page.evaluate('''() => {
                    const el = document.querySelector('#nav-link-accountList .nav-line-1');
                    return el ? el.innerText.trim() : null;
                }''')
                if not (final_greeting and "Hello," in final_greeting):
                    logger.error("Double-check: Still not logged in according to greeting element, despite manual confirmation.")
                # No need for specific log if cookies extraction failed BUT login_success was True and greeting was found
            except Exception:
                logger.warning("Could not perform final greeting check.")
            # login_and_upload_success remains False
        else:
            logger.info(f"Successfully extracted {len(raw_cookies)} raw cookie objects.")

            # Convert Cookie objects to JSON serializable list of dicts
            serializable_cookies = []
            for cookie in raw_cookies:
                # Extract common attributes, handle potential None values
                cookie_dict = {
                    "name": getattr(cookie, 'name', None),
                    "value": getattr(cookie, 'value', None),
                    "domain": getattr(cookie, 'domain', None),
                    "path": getattr(cookie, 'path', None),
                    "expires": getattr(cookie, 'expires', None), # May need conversion if not serializable
                    "secure": getattr(cookie, 'secure', False),
                    "httpOnly": getattr(cookie, 'httpOnly', False), # Try direct access
                    # Add other relevant fields if needed, e.g., sameSite
                }
                # Filter out None values if necessary, or handle expires conversion
                serializable_cookies.append({k: v for k, v in cookie_dict.items() if v is not None})

            logger.info(f"Formatted {len(serializable_cookies)} cookies for JSON.")
            # Send the *serializable* list to the API
            cookie_upload_success = await post_cookies_to_api(serializable_cookies)

            if cookie_upload_success:
                logger.info("Manual login confirmation received and cookies sent successfully.")
            else:
                logger.error("Cookie extraction may have succeeded, but upload to API failed. See previous logs.")
        # --- End Cookie Extraction Logic --- #

        if not cookie_upload_success:
             logger.error("Overall process failed (cookie extraction or upload failed). Exiting with error status.")
             sys.exit(1)
        else:
            logger.info("Process completed successfully.")

    except Exception as e:
        # Catch top-level errors in the main login flow
        logger.exception(f"An unexpected error occurred during the nodriver login process: {e}")
        if page:
            try:
                # Save final page state on uncaught exception - REMOVED
                pass
            except Exception as screenshot_err:
                logger.warning(f"Could not save error screenshot: {screenshot_err}")
        sys.exit(1)
    finally:
        if browser:
            logger.info("Closing nodriver browser...")
            try:
                browser.stop() # Use stop() to close nodriver browser (synchronous)
                logger.info("Browser closed.")
            except Exception as close_err:
                 logger.warning(f"Error closing browser: {close_err}")

if __name__ == "__main__":
    try:
        uc.loop().run_until_complete(main())
    except KeyboardInterrupt:
        logging.getLogger().info("Login process interrupted by user.")
        sys.exit(0)
    except Exception as main_err:
         # Catch errors happening outside the main async function itself
         logging.getLogger().exception(f"Critical error running main: {main_err}")
         sys.exit(1)
