"""Functions for interacting with the Alexa API (shopping list)."""

import json
import logging
import requests
from http.cookies import SimpleCookie
from collections import defaultdict
from typing import Optional, List, Dict, Any

# Import the local config module itself
from . import config as api_config

logger = logging.getLogger(__name__)

# Define headers for requests (Consider making configurable or dynamic)
DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5_1 like Mac OS X)"
                   " AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
                   " PitanguiBridge/2.2.345247.0-[HARDWARE=iPhone10_4][SOFTWARE=13.5.1]"),
    "Accept": "*/*",
    "Accept-Language": "*",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1"
}

# --- Cookie Handling ---

# Hardcoded path for cookie loading *within the container*
# Adjusted for JSON format
CONTAINER_COOKIE_PATH = "/app/data/cookies.json"

def load_cookies_from_json_file(cookie_file_path: str) -> Optional[List[Dict[str, Any]]]:
    """Loads cookies from a JSON file (expected list of dicts)."""
    try:
        with open(cookie_file_path, 'r', encoding='utf-8') as f:
            cookies_list = json.load(f) # Load list of cookie dicts

        if not isinstance(cookies_list, list):
            logger.error(f"Expected a list in {cookie_file_path}, got {type(cookies_list)}.")
            return None

        # Return the full list of dictionaries for detailed processing
        logger.debug(f"Successfully loaded {len(cookies_list)} cookie dicts from JSON: {cookie_file_path}")
        return cookies_list

    except FileNotFoundError:
        logger.error(f"Cookie file not found: {cookie_file_path}")
        return None
    except json.JSONDecodeError as json_err:
        logger.error(f"Failed to decode JSON from {cookie_file_path}: {json_err}")
        return None
    except Exception as err:
        logger.error(f"Failed to load or parse cookies from JSON file {cookie_file_path}: {err}", exc_info=True)
        return None

# --- API Request Function ---
def make_authenticated_request(
    url: str,
    # cookie_file_path: str, # No longer needed as parameter
    method: str = 'GET',
    payload: Optional[Dict[str, Any]] = None
) -> Optional[requests.Response]:
    """Makes an authenticated request using cookies from the fixed container path."""
    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        # Always load from the container path
        cookie_list_of_dicts = load_cookies_from_json_file(CONTAINER_COOKIE_PATH)

        if not cookie_list_of_dicts:
            logger.error(f"No cookies loaded from {CONTAINER_COOKIE_PATH} for authenticated request.")
            return None

        # Set cookies individually using requests' set method
        for cookie_dict in cookie_list_of_dicts:
            name = cookie_dict.get('name')
            value = cookie_dict.get('value')
            domain = cookie_dict.get('domain')
            path = cookie_dict.get('path')

            if name and value:
                logger.debug(f"Setting cookie: name={name}, domain={domain}, path={path}")
                session.cookies.set(
                    name=name,
                    value=value,
                    domain=domain,
                    path=path
                    # requests automatically handles secure/expires/httpOnly for its context
                    # We mainly need name, value, domain, path for session management
                )
            else:
                logger.warning(f"Skipping cookie dict with missing name/value: {cookie_dict}")

        logger.debug(f"Making {method} request to {url}")
        if method.upper() == 'GET':
            response = session.get(url)
        elif method.upper() == 'PUT':
            logger.debug(f"PUT payload: {payload}")
            response = session.put(url, json=payload)
        elif method.upper() == 'POST':
            logger.debug(f"POST payload: {payload}")
            response = session.post(url, json=payload)
        elif method.upper() == 'DELETE':
            logger.debug(f"DELETE request to {url}")
            # Allow DELETE with an optional payload (needed for Alexa API)
            response = session.delete(url, json=payload)
        else:
            logger.error(f"Unsupported method specified: {method}")
            return None

        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logger.debug(f"Request successful ({response.status_code})")
        return response

    except requests.exceptions.RequestException as err:
        logger.error(f"HTTP request failed: {err}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error during authenticated request: {e}")
        return None

# --- Shopping List Specific Functions ---
def extract_list_items(response_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Extracts list items from the API response."""
    # Adapt based on actual API response structure if needed
    for key in response_data.keys():
        if isinstance(response_data[key], dict) and 'listItems' in response_data[key]:
            return response_data[key]['listItems']
    logger.warning("Could not find 'listItems' in response data structure.")
    logger.debug(f"Full response keys: {list(response_data.keys())}")
    return None

def filter_incomplete_items(list_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters a list of items to include only those not marked completed."""
    return [item for item in list_items if not item.get('completed', False)]

def get_shopping_list_items() -> Optional[List[Dict[str, Any]]]:
    """Gets all items from the Alexa shopping list."""
    list_items_url = f"{api_config.AMAZON_URL}/alexashoppinglists/api/getlistitems"
    # Pass the config but the function now ignores the cookie_path within it
    response = make_authenticated_request(list_items_url, method='GET')
    if response:
        try:
            response_data = response.json()
            logger.debug("Successfully retrieved shopping list data.")
            return extract_list_items(response_data)
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from shopping list API: {e}")
            logger.debug(f"Response text: {response.text[:500]}") # Log first 500 chars
            return None
    else:
        logger.error("Failed to retrieve shopping list data.")
        return None

def add_shopping_list_item(item_value: str) -> bool:
    """Adds a new item to the Alexa shopping list."""
    logger.info(f"Adding item to shopping list: {item_value}")
    # Use the correct endpoint from documentation
    add_item_path = "/alexashoppinglists/api/addlistitem/YW16bjEuYWNjb3VudC5BSERXNEkyVE00U1I0UVQ2VUpINzNWUVpaQU5BLVNIT1BQSU5HX0lURU0="
    url = f"{api_config.AMAZON_URL}{add_item_path}"
    payload = {
        "value": item_value,
        "type": "TASK" # Assuming 'TASK' type, common for shopping/todo lists
    }

    response = make_authenticated_request(
        url,
        # config.cookie_path, # Removed
        method='POST', # Assuming POST for creation
        payload=payload
    )

    if response and response.status_code == 200: # Assuming 200 OK for success
        logger.info(f"Successfully added item: {item_value}")
        return True
    else:
        status = response.status_code if response else 'No Response'
        logger.error(f"Failed to add item: {item_value} (Status: {status})")
        # Log response text for debugging if available and failed
        if response is not None:
             logger.debug(f"Add item response text: {response.text[:500]}")
        return False

def mark_item_as_completed(list_item: Dict[str, Any]) -> bool:
    """Marks a specific shopping list item as completed via the API."""
    return _update_item_completion_status(list_item, completed_status=True)

def delete_shopping_list_item(list_item: Dict[str, Any]) -> bool:
    """Deletes a specific shopping list item via the API."""
    item_value = list_item.get('value', 'unknown')
    item_id = list_item.get('id')

    if not item_id:
        logger.error(f"Cannot delete item '{item_value}' without an ID.")
        return False

    logger.info(f"Deleting item: {item_value} (ID: {item_id})")
    # Use the correct base endpoint from documentation
    delete_item_path = "/alexashoppinglists/api/deletelistitem"
    url = f"{api_config.AMAZON_URL}{delete_item_path}"

    # Send the item dict (containing ID) as payload
    response = make_authenticated_request(
        url,
        # config.cookie_path, # Removed
        method='DELETE',
        payload=list_item # Send the whole item dict
    )

    # Check for successful deletion (often 200 OK or 204 No Content)
    if response and (response.status_code == 200 or response.status_code == 204):
        logger.info(f"Successfully deleted item: {item_value}")
        return True
    else:
        status = response.status_code if response else 'No Response'
        logger.error(f"Failed to delete item: {item_value} (Status: {status})")
        # Log response text for debugging if available and failed
        if response is not None:
            logger.debug(f"Delete item response text: {response.text[:500]}")
        return False

def unmark_item_as_completed(list_item: Dict[str, Any]) -> bool:
    """Unmarks a specific shopping list item as completed via the API."""
    return _update_item_completion_status(list_item, completed_status=False)

def _update_item_completion_status(list_item: Dict[str, Any], completed_status: bool) -> bool:
    """Internal helper to update the completed status of an item."""
    item_value = list_item.get('value', 'unknown')
    action = "Marking" if completed_status else "Unmarking"
    action_past = "marked" if completed_status else "unmarked"

    logger.info(f"{action} item as completed: {item_value}")
    url = f"{api_config.AMAZON_URL}/alexashoppinglists/api/updatelistitem"
    list_item_copy = list_item.copy()
    list_item_copy['completed'] = completed_status

    response = make_authenticated_request(
        url,
        # config.cookie_path, # Removed
        method='PUT',
        payload=list_item_copy
    )

    if response and response.status_code == 200:
        logger.info(f"Successfully {action_past} item as completed: {item_value}")
        return True
    else:
        status = response.status_code if response else 'No Response'
        logger.error(f"Failed to {action.lower()} item as completed: {item_value} (Status: {status})")
        if response is not None:
            logger.debug(f"{action} item response text: {response.text[:500]}")
        return False
