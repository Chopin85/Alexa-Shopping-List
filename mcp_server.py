"""FastMCP Server for interacting with Alexa Shopping List."""

import logging
import sys
from typing import List, Dict, Any, Optional, Union

# Add src directory to path if running directly
# This helps Python find the alexa_shopping_list package
import os
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if os.path.isdir(src_dir) and src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from fastmcp import FastMCP
    from alexa_shopping_list.config import load_config, AppConfig
    from alexa_shopping_list.alexa_api import (
        get_shopping_list_items,
        add_shopping_list_item,
        delete_shopping_list_item,
        mark_item_as_completed,
        unmark_item_as_completed,
        filter_incomplete_items
    )
except ImportError as e:
    print(f"Error importing necessary modules: {e}", file=sys.stderr)
    print("Ensure fastmcp is installed ('pip install fastmcp') and run from project root.", file=sys.stderr)
    sys.exit(1)

# --- Configuration and Initialization ---

# Load configuration globally - assumes .env is set up
# CRITICAL ASSUMPTION: Authentication cookie file is valid before starting server.
try:
    config = load_config()
except EnvironmentError as e:
    print(f"Configuration Error: {e}", file=sys.stderr)
    sys.exit(1)

# Initialize FastMCP Server
mcp = FastMCP("Alexa Shopping List Manager 🛒")
logger = logging.getLogger(__name__) # Use standard logging

# Setup basic logging for MCP server context (optional, FastMCP handles some)
logging.basicConfig(level=config.log_level.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Helper Function ---

def _find_item_by_value(value_to_find: str) -> Optional[Dict[str, Any]]:
    """Internal helper to find the first matching incomplete item dict by its value."""
    logger.debug(f"Searching for item with value: '{value_to_find}'")
    all_items = get_shopping_list_items(config)
    if not all_items:
        logger.debug("Shopping list is empty, cannot find item.")
        return None

    incomplete_items = filter_incomplete_items(all_items)
    for item in incomplete_items:
        if item.get('value', '').strip().lower() == value_to_find.strip().lower():
            logger.debug(f"Found item: {item}")
            return item

    logger.debug(f"Item with value '{value_to_find}' not found in incomplete items.")
    return None

# --- MCP Tools ---

@mcp.tool()
def get_list() -> List[str]:
    """Retrieves the current incomplete items from the Alexa shopping list."""
    logger.info("Tool 'get_list' called.")
    all_items = get_shopping_list_items(config)
    if all_items is None:
        return ["Error: Could not retrieve shopping list items."]

    incomplete_items = filter_incomplete_items(all_items)
    if not incomplete_items:
        return ["Shopping list is empty or has no incomplete items."]

    item_values = [item.get('value', '<Unknown Item>') for item in incomplete_items]
    return item_values

@mcp.tool()
def get_completed_list() -> List[str]:
    """Retrieves items currently marked as completed from the Alexa shopping list."""
    logger.info("Tool 'get_completed_list' called.")
    all_items = get_shopping_list_items(config)
    if all_items is None:
        return ["Error: Could not retrieve shopping list items."]

    # Filter for completed items
    completed_items = [item for item in all_items if item.get('completed', False)]

    if not completed_items:
        return ["No completed items found on the list."]

    item_values = [item.get('value', '<Unknown Item>') for item in completed_items]
    return item_values

@mcp.tool()
def add_item(item_values: Union[str, List[str]]) -> str:
    """Adds one or more items to the Alexa shopping list."""
    logger.info(f"Tool 'add_item' called with value(s): {item_values}")

    if isinstance(item_values, str):
        values_to_process = [item_values]
    else:
        values_to_process = item_values

    if not values_to_process or not any(v.strip() for v in values_to_process):
        return "Error: No valid item values provided to add."

    results = {
        "added": [],
        "failed": []
    }

    for value in values_to_process:
        val_strip = value.strip()
        if not val_strip:
            continue # Skip empty strings

        logger.debug(f"Attempting to add item '{val_strip}'")
        success = add_shopping_list_item(config, val_strip)
        if success:
            results["added"].append(val_strip)
        else:
            results["failed"].append(val_strip)

    # Format summary message
    summary = []
    if results["added"]: summary.append(f"Added: {', '.join(results['added'])}.")
    if results["failed"]: summary.append(f"Failed to add: {', '.join(results['failed'])}.")

    return " ".join(summary) if summary else "No actions performed or items provided."

@mcp.tool()
def delete_item(item_values: Union[str, List[str]]) -> str:
    """Deletes one or more items from the Alexa shopping list by their value(s)."""
    logger.info(f"Tool 'delete_item' called with value(s): {item_values}")

    if isinstance(item_values, str):
        values_to_process = [item_values] # Normalize to list
    else:
        values_to_process = item_values

    if not values_to_process or not any(v.strip() for v in values_to_process):
        return "Error: No valid item values provided for deletion."

    # Fetch list once to search within it
    all_items = get_shopping_list_items(config)
    incomplete_items = filter_incomplete_items(all_items) if all_items else []

    results = {
        "deleted": [],
        "not_found": [],
        "missing_id": [],
        "failed": []
    }

    for value in values_to_process:
        val_strip = value.strip()
        if not val_strip:
            continue # Skip empty strings

        item_to_delete = None
        for item in incomplete_items:
            if item.get('value', '').strip().lower() == val_strip.lower():
                item_to_delete = item
                break # Found the first match

        if not item_to_delete:
            results["not_found"].append(val_strip)
            continue

        item_id = item_to_delete.get('id')
        if not item_id:
            results["missing_id"].append(val_strip)
            continue

        logger.debug(f"Attempting to delete item '{val_strip}' with ID {item_id}")
        success = delete_shopping_list_item(config, item_to_delete)
        if success:
            results["deleted"].append(val_strip)
            # Remove from local list to prevent trying to delete same-named item again
            incomplete_items.remove(item_to_delete)
        else:
            results["failed"].append(val_strip)

    # Format summary message
    summary = []
    if results["deleted"]: summary.append(f"Deleted: {', '.join(results['deleted'])}.")
    if results["not_found"]: summary.append(f"Not found (incomplete): {', '.join(results['not_found'])}.")
    if results["missing_id"]: summary.append(f"Found but missing ID: {', '.join(results['missing_id'])}.")
    if results["failed"]: summary.append(f"Failed to delete: {', '.join(results['failed'])}.")

    return " ".join(summary) if summary else "No actions performed or items provided."

@mcp.tool()
def mark_complete(item_values: Union[str, List[str]]) -> str:
    """Marks one or more items on the Alexa shopping list as completed by their value(s)."""
    logger.info(f"Tool 'mark_complete' called with value(s): {item_values}")

    if isinstance(item_values, str):
        values_to_process = [item_values]
    else:
        values_to_process = item_values

    if not values_to_process or not any(v.strip() for v in values_to_process):
        return "Error: No valid item values provided to mark complete."

    # Fetch list once
    all_items = get_shopping_list_items(config)
    incomplete_items = filter_incomplete_items(all_items) if all_items else []

    results = {
        "marked": [],
        "not_found": [],
        "already_complete": [], # Checked via item state
        "failed": []
    }

    for value in values_to_process:
        val_strip = value.strip()
        if not val_strip:
            continue

        item_to_mark = None
        for item in incomplete_items:
             if item.get('value', '').strip().lower() == val_strip.lower():
                 item_to_mark = item
                 break

        if not item_to_mark:
            results["not_found"].append(val_strip)
            continue

        # Although we filter for incomplete, double-check just in case of race condition or oddity
        if item_to_mark.get('completed', False):
             results["already_complete"].append(val_strip)
             continue

        logger.debug(f"Attempting to mark '{val_strip}' complete.")
        success = mark_item_as_completed(config, item_to_mark)
        if success:
            results["marked"].append(val_strip)
            # Remove from local list to prevent trying to mark same-named item again
            incomplete_items.remove(item_to_mark)
        else:
            results["failed"].append(val_strip)

    # Format summary message
    summary = []
    if results["marked"]: summary.append(f"Marked complete: {', '.join(results['marked'])}.")
    if results["not_found"]: summary.append(f"Not found (incomplete): {', '.join(results['not_found'])}.")
    if results["already_complete"]: summary.append(f"Already complete: {', '.join(results['already_complete'])}.")
    if results["failed"]: summary.append(f"Failed to mark complete: {', '.join(results['failed'])}.")

    return " ".join(summary) if summary else "No actions performed or items provided."

@mcp.tool()
def mark_incomplete(item_values: Union[str, List[str]]) -> str:
    """Marks one or more items on the Alexa shopping list as incomplete (unmarks them) by their value(s)."""
    logger.info(f"Tool 'mark_incomplete' called with value(s): {item_values}")

    if isinstance(item_values, str):
        values_to_process = [item_values]
    else:
        values_to_process = item_values

    if not values_to_process or not any(v.strip() for v in values_to_process):
         return "Error: No valid item values provided to mark incomplete."

    # Need to search *all* items
    logger.debug("Fetching all items to search for completed ones.")
    all_items = get_shopping_list_items(config)
    if all_items is None:
        return "Error: Could not retrieve shopping list items to process request."

    results = {
        "unmarked": [],
        "not_found": [],
        "already_incomplete": [],
        "failed": []
    }

    # Create a mutable copy to track changes if needed
    searchable_items = list(all_items)

    for value in values_to_process:
        val_strip = value.strip()
        if not val_strip:
            continue

        item_to_unmark = None
        item_index = -1
        for i, item in enumerate(searchable_items):
            if item.get('value', '').strip().lower() == val_strip.lower():
                item_to_unmark = item
                item_index = i
                logger.debug(f"Found item to potentially unmark: {item}")
                break

        if not item_to_unmark:
            results["not_found"].append(val_strip)
            continue

        if not item_to_unmark.get('completed', False): # Check if it's already incomplete
             results["already_incomplete"].append(val_strip)
             continue

        logger.debug(f"Attempting to mark '{val_strip}' incomplete.")
        success = unmark_item_as_completed(config, item_to_unmark)
        if success:
            results["unmarked"].append(val_strip)
            # Mark locally as incomplete to prevent reprocessing if same name exists
            if item_index != -1:
                searchable_items[item_index]['completed'] = False
        else:
            results["failed"].append(val_strip)

    # Format summary message
    summary = []
    if results["unmarked"]: summary.append(f"Marked incomplete: {', '.join(results['unmarked'])}.")
    if results["not_found"]: summary.append(f"Not found: {', '.join(results['not_found'])}.")
    if results["already_incomplete"]: summary.append(f"Already incomplete: {', '.join(results['already_incomplete'])}.")
    if results["failed"]: summary.append(f"Failed to mark incomplete: {', '.join(results['failed'])}.")

    return " ".join(summary) if summary else "No actions performed or items provided."

@mcp.tool()
def clear_completed_items() -> str:
    """Iteratively deletes all items marked as completed from the Alexa shopping list."""
    logger.info("Tool 'clear_completed_items' called.")

    total_deleted_count = 0
    total_failed_items = []
    iteration = 0
    max_iterations = 10 # Safety break to prevent infinite loops

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Clear completed items: Iteration {iteration}")

        # 1. Get all items
        all_items = get_shopping_list_items(config)
        if all_items is None:
            error_msg = "Error: Could not retrieve shopping list items during clearing process."
            if total_deleted_count > 0 or total_failed_items:
                 error_msg += f" So far: Deleted {total_deleted_count}, Failures: {len(total_failed_items)}."
            return error_msg

        # 2. Filter for completed items in this batch
        completed_items_batch = [item for item in all_items if item.get('completed', False)]

        if not completed_items_batch:
            logger.info("No more completed items found. Clearing process finished.")
            break # Exit the loop if no completed items are left

        logger.info(f"Found {len(completed_items_batch)} completed items in this batch.")

        # 3. Attempt to delete items in this batch
        batch_failed = []
        for item in completed_items_batch:
            item_value = item.get('value', '<Unknown Item>')
            item_id = item.get('id')

            if not item_id:
                logger.warning(f"Skipping completed item '{item_value}' (iteration {iteration}) due to missing ID.")
                if f"{item_value} (Missing ID)" not in total_failed_items:
                     total_failed_items.append(f"{item_value} (Missing ID)")
                continue

            logger.debug(f"Attempting delete (iteration {iteration}): '{item_value}' (ID: {item_id})")
            success = delete_shopping_list_item(config, item)
            if success:
                total_deleted_count += 1
            else:
                logger.warning(f"Failed to delete completed item: '{item_value}' (iteration {iteration})")
                if item_value not in batch_failed and item_value not in total_failed_items:
                    batch_failed.append(item_value)

        total_failed_items.extend(batch_failed) # Add failures from this batch to total

        # Optional: Small delay between batches if needed
        # import time
        # time.sleep(1)

    else: # If loop finishes due to max_iterations
         logger.warning(f"Clear completed items stopped after reaching max iterations ({max_iterations}). There might still be completed items left.")

    # 4. Report final results
    summary = f"Clear completed process finished after {iteration} iteration(s). Total Deleted: {total_deleted_count}."
    if total_failed_items:
        summary += f" Failures encountered for: {', '.join(total_failed_items)}."

    logger.info(summary)
    return summary

# --- Run Server ---

if __name__ == "__main__":
    logger.info(f"Starting FastMCP server '{mcp.name}'...")
    # Add any specific transport or port needs here if not using default stdio
    mcp.run()
