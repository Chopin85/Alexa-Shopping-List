import sys
import os
import logging
from typing import List, Dict, Any, Optional, Union
import json # Added json for saving cookies

# --- Path Modification ---
# Add the project root directory to the Python path
# This allows importing modules from the 'src' directory (e.g., alexa_shopping_list)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)
# --- End Path Modification ---

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field  # For request body validation

# Import necessary components using relative imports
try:
    # Use the new local config
    from . import config as api_config # Alias to avoid name clashes
    from .alexa_api import ( # Relative import
        get_shopping_list_items,
        add_shopping_list_item,
        delete_shopping_list_item,
        mark_item_as_completed,
        unmark_item_as_completed,
        filter_incomplete_items,
        # No filter_completed_items, we'll do it inline
    )
except ImportError as e:
    print(f"FATAL ERROR: Could not import alexa_shopping_list modules: {e}", file=sys.stderr)
    print("Ensure the script is run from the project root or the src directory is in PYTHONPATH.", file=sys.stderr)
    sys.exit(1)

# --- Globals & Setup ---

# Configure basic logging
# Note: Uvicorn will likely handle more advanced logging config when run
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure logging based on local config
logging.basicConfig(level=api_config.LOG_LEVEL_INT, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy library logs based on loaded config
if api_config.LOG_LEVEL_INT > logging.DEBUG:
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING) # Likely not needed here, but safe
    logging.getLogger("webdriver_manager").setLevel(logging.WARNING) # Likely not needed here
    logger.debug("Suppressed noisy library logs.")

# --- FastAPI App Instance ---
app = FastAPI(
    title="Alexa Shopping List API",
    description="API to interact with an Alexa Shopping List using pre-generated cookies.",
    version="1.0.0"
)

# --- Helper Function ---
def find_item_by_name(items: List[Dict[str, Any]], name: str) -> Dict[str, Any] | None:
    """Finds the first item in a list matching the name (case-insensitive)."""
    if items is None:
        return None
    for item in items:
        if item.get("value", "").lower() == name.lower():
            return item
    return None

# --- Pydantic Models (for Request Bodies) ---
class ItemNameModel(BaseModel):
    item_name: str = Field(..., description="The name of the shopping list item.")

# Define a Pydantic model for the expected cookie structure (adjust if needed)
class CookieModel(BaseModel):
    name: str
    value: str
    domain: Optional[str] = None
    path: Optional[str] = None
    # Add missing fields based on what login.py sends
    expires: Optional[Union[str, int, float]] = None # Allow various types for expiry
    secure: Optional[bool] = None
    httpOnly: Optional[bool] = None
    # sameSite: Optional[str] = None # Could add if needed

# --- API Endpoints ---

@app.get("/", tags=["Status"])
async def read_root():
    """Simple health check endpoint."""
    return {"status": "Alexa Shopping List API is running"}

@app.get("/items/all", tags=["Items"], response_model=List[Dict[str, Any]])
async def get_all_list_items():
    """Retrieves all items (completed and incomplete) from the shopping list."""
    logger.info("Endpoint GET /items/all called.")
    items = get_shopping_list_items()
    if items is None:
        logger.error("Failed to retrieve items from Alexa API.")
        raise HTTPException(status_code=503, detail="Could not retrieve shopping list from Alexa.")
    return items

@app.get("/items/incomplete", tags=["Items"], response_model=List[Dict[str, Any]])
async def get_incomplete_list_items():
    """Retrieves only the incomplete items from the shopping list."""
    logger.info("Endpoint GET /items/incomplete called.")
    all_items = get_shopping_list_items() # No longer needs config passed
    if all_items is None:
        logger.error("Failed to retrieve items from Alexa API.")
        raise HTTPException(status_code=503, detail="Could not retrieve shopping list from Alexa.")
    incomplete_items = filter_incomplete_items(all_items)
    return incomplete_items

@app.get("/items/completed", tags=["Items"], response_model=List[Dict[str, Any]])
async def get_completed_list_items():
    """Retrieves only the completed items from the shopping list."""
    logger.info("Endpoint GET /items/completed called.")
    all_items = get_shopping_list_items() # No longer needs config passed
    if all_items is None:
        logger.error("Failed to retrieve items from Alexa API.")
        raise HTTPException(status_code=503, detail="Could not retrieve shopping list from Alexa.")
    # Filter completed items directly
    completed_items = [item for item in all_items if item.get('completed', False)]
    return completed_items

@app.post("/items", tags=["Items"], status_code=201)  # 201 Created
async def add_new_item(item_data: ItemNameModel):
    """Adds a new item to the shopping list."""
    item_name = item_data.item_name
    logger.info(f"Endpoint POST /items called to add: '{item_name}'")
    success = add_shopping_list_item(item_name) # No longer needs config passed
    if not success:
        logger.error(f"Failed to add item '{item_name}' via Alexa API.")
        raise HTTPException(status_code=500, detail=f"Failed to add item '{item_name}'.")
    return {"message": f"Item '{item_name}' added successfully."}

@app.delete("/items", tags=["Items"])
async def remove_item(item_data: ItemNameModel):
    """Deletes an item from the shopping list by name (case-insensitive)."""
    item_name = item_data.item_name
    logger.info(f"Endpoint DELETE /items called for: '{item_name}'")
    all_items = get_shopping_list_items() # No longer needs config passed
    item_to_delete = find_item_by_name(all_items or [], item_name)

    if not item_to_delete:
        logger.warning(f"Item '{item_name}' not found for deletion.")
        raise HTTPException(status_code=404, detail=f"Item '{item_name}' not found.")

    success = delete_shopping_list_item(item_to_delete) # No longer needs config passed
    if not success:
        logger.error(f"Failed to delete item '{item_name}' via Alexa API.")
        raise HTTPException(status_code=500, detail=f"Failed to delete item '{item_name}'.")
    return {"message": f"Item '{item_name}' deleted successfully."}

@app.put("/items/mark_completed", tags=["Items"])
async def mark_item_complete(item_data: ItemNameModel):
    """Marks an item as completed by name (case-insensitive)."""
    item_name = item_data.item_name
    logger.info(f"Endpoint PUT /items/mark_completed called for: '{item_name}'")
    all_items = get_shopping_list_items() # No longer needs config passed
    # Find an *incomplete* item matching the name
    item_to_mark = find_item_by_name(filter_incomplete_items(all_items or []), item_name)

    if not item_to_mark:
        logger.warning(f"Incomplete item '{item_name}' not found to mark complete.")
        raise HTTPException(status_code=404, detail=f"Incomplete item '{item_name}' not found.")

    success = mark_item_as_completed(item_to_mark) # No longer needs config passed
    if not success:
        logger.error(f"Failed to mark item '{item_name}' completed via Alexa API.")
        raise HTTPException(status_code=500, detail=f"Failed to mark item '{item_name}' as completed.")
    return {"message": f"Item '{item_name}' marked as completed."}

@app.put("/items/mark_incomplete", tags=["Items"])
async def mark_item_incomplete_endpoint(item_data: ItemNameModel):
    """Marks an item as incomplete by name (case-insensitive)."""
    item_name = item_data.item_name
    logger.info(f"Endpoint PUT /items/mark_incomplete called for: '{item_name}'")
    all_items = get_shopping_list_items() # No longer needs config passed
    # Find a *complete* item matching the name
    completed_items = [item for item in (all_items or []) if item.get('completed', False)]
    item_to_mark = find_item_by_name(completed_items, item_name)

    if not item_to_mark:
        logger.warning(f"Completed item '{item_name}' not found to mark incomplete.")
        raise HTTPException(status_code=404, detail=f"Completed item '{item_name}' not found.")

    success = unmark_item_as_completed(item_to_mark)  # No longer needs config passed
    if not success:
        logger.error(f"Failed to mark item '{item_name}' incomplete via Alexa API.")
        raise HTTPException(status_code=500, detail=f"Failed to mark item '{item_name}' as incomplete.")
    return {"message": f"Item '{item_name}' marked as incomplete."}

# --- Authentication Endpoint ---
@app.post("/auth/cookies", tags=["Authentication"], status_code=200)
async def receive_cookies(cookies_data: List[CookieModel]): # Expect a list of CookieModel
    """Accepts cookies as JSON and saves them to the persistent data volume."""
    # Use the COOKIE_PATH directly from the local API config
    cookie_path = api_config.COOKIE_PATH
    data_dir_container = os.path.dirname(cookie_path) # Get directory from the path

    logger.info(f"Received {len(cookies_data)} cookies. Attempting to save as JSON to: {cookie_path}")

    # Create directory if it doesn't exist
    try:
        os.makedirs(data_dir_container, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create data directory '{data_dir_container}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: Could not create data directory.")

    try:
        # Convert Pydantic models back to dicts for JSON serialization
        cookies_list_of_dicts = [cookie.model_dump(exclude_unset=True) for cookie in cookies_data]

        # Save the received cookie list as a JSON file
        with open(cookie_path, "w", encoding="utf-8") as f:
            json.dump(cookies_list_of_dicts, f, indent=2)

        logger.info(f"Successfully saved cookie data as JSON to {cookie_path}")
        return {"message": "Cookie data received and saved successfully."}

    except Exception as e:
        logger.error(f"Failed to save cookie data as JSON to {cookie_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save cookie data: {e}")

# --- Optional: Add main block to run with uvicorn for direct execution ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server directly for development...")
    # Note: Host '0.0.0.0' makes it accessible on your network
    # Use '127.0.0.1' for local access only
    # Reload=True is for development, disable for production
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
