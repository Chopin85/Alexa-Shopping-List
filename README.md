# Alexa Shopping List FastAPI + MCP Server

This project allows an LLM (like Claude) to interact with your Alexa shopping list via the Model Context Protocol (MCP). It uses a two-part architecture:

1.  **FastAPI Server (`src/api/main.py`):** Handles direct interaction with the Alexa API, including authentication using saved cookies.
2.  **MCP Server (`src/mcp/mcp_server.py`):** Acts as a proxy, exposing tools via MCP that forward requests to the running FastAPI server.

## Features

- Provides MCP tools to:
    - Get all items (`get_all_items`).
    - Get incomplete items (`get_incomplete_items`).
    - Get completed items (`get_completed_items`).
    - Add an item (`add_item`).
    - Delete an item by name (`delete_item`).
    - Mark an item as complete by name (`mark_item_completed`).
    - Mark an item as incomplete by name (`mark_item_incomplete`).
    - Check the status of the backend FastAPI server (`check_api_status`).
- Uses Selenium **in a separate script** (`src/mcp/login.py`) to handle the initial Amazon login (including 2FA) and save authentication cookies.
- The FastAPI server loads the saved cookies to make authenticated API calls to Alexa.
- The MCP server communicates with the FastAPI server via local HTTP requests.

## Prerequisites

- Python 3.x
- A virtual environment tool (like `venv`)
- `pip` (or `uv` for faster installs)
- **Google Chrome** (or another supported browser) installed on the host machine for the initial login step.
- An Amazon account with Alexa enabled.

## Setup

### 1. Clone the Repository

```bash
# git clone <repository_url>
cd alexa-mcp
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Install required packages into your activated virtual environment. Using `uv` is recommended for speed.

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
# pip install -r requirements.txt
```
This installs `fastapi`, `uvicorn`, `requests`, `python-dotenv`, `selenium`, `webdriver-manager`, and `fastmcp`.

### 4. Install Project in Editable Mode

This allows imports within the project (like the FastAPI server importing `alexa_shopping_list` modules) to work correctly.

```bash
pip install -e .
```

### 5. Environment Variables

Create a `.env` file in the project root. Populate it with:

```dotenv
# Your local Amazon domain (e.g., amazon.com, amazon.co.uk)
AMAZON_URL=https://www.amazon.com

# Path where the login script will SAVE and the FastAPI server will READ the cookie file.
# Ensure the directory exists if not using the current directory.
COOKIE_PATH=./alexa_cookie.pickle

# Logging level for the scripts (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Optional: Port for the FastAPI server
# API_PORT=8000
```

### 6. Authentication (Cookie Generation - Run Once or When Needed)

The system relies on a cookie file for authentication. You need to run the `login.py` script to handle the interactive browser login and generate this file.

1.  **Configure `.env`:** Ensure your `.env` file is correctly set up with `AMAZON_URL` and `COOKIE_PATH`.
2.  **Run the Login Script:** From your terminal (with the virtual environment activated) in the project root:
    ```bash
    python src/mcp/login.py
    ```
3.  **Browser Interaction:**
    *   Follow the console prompts.
    *   Selenium will open a browser window to your `AMAZON_URL`.
    *   **MANUALLY** log in to your Amazon account (including 2FA).
    *   Once logged in, return to the console and press `Enter`.
4.  **Cookie Saved:** The script saves cookies to `COOKIE_PATH`.

Run this whenever the cookie file is missing or expired (causing `401 Unauthorized` errors).

## Running the System

You need to run **two** components: the FastAPI server and the MCP server.

### 1. Start the FastAPI Server

In one terminal (with the virtual environment activated):

```bash
uvicorn src.api.main:app --reload --port 8000
```
Keep this terminal running. You should see logs indicating the server is running on `http://127.0.0.1:8000`.

### 2. Start the MCP Server

You have two main options:

**Option A: Direct Execution (for Testing/Development)**

In a *second* terminal (with the virtual environment activated):

```bash
python src/mcp/mcp_server.py
```
This runs the MCP server directly, typically using stdio for communication. It's useful for simple testing but won't integrate with Claude Desktop.

**Option B: Claude Desktop Integration**

Configure Claude Desktop to run the MCP server script using your virtual environment's Python interpreter.

1.  **Find `mcp.json`:** Locate the configuration file used by Claude Desktop (e.g., in `~/.config/claude/`, `~/Library/Application Support/Claude/`).
2.  **Add/Edit Server Entry:** Ensure you have an entry for your Alexa server configured like this:

    ```json
    {
      "servers": [
        {
          "name": "Alexa Shopping List", // Or your preferred name
          "type": "stdio",
          "command": "/path/to/your/project/alexa-mcp/.venv/bin/python", // <-- ABSOLUTE path to venv python
          "args": [
            "/path/to/your/project/alexa-mcp/src/mcp/mcp_server.py" // <-- ABSOLUTE path to the MCP script
          ],
          "workingDirectory": "/path/to/your/project/alexa-mcp" // <-- ABSOLUTE path to project root
          // Add other relevant config if needed
        }
        // ... other servers ...
      ]
    }
    ```
    **Important:** Replace `/path/to/your/project/alexa-mcp` with the actual, absolute path to your project directory. Set the `workingDirectory` so the script can find relative paths like the `.env` file and `COOKIE_PATH`.

3.  **Restart Claude Desktop:** If it was running, restart it to load the new configuration.
4.  **Activate Tool:** Use the "Alexa Shopping List" tool within Claude. It should now connect to the running MCP server process.

*(Note: The `fastmcp install` command was previously used but proved unreliable due to environment issues. Direct configuration in `mcp.json` is the recommended approach for Claude Desktop.)*

## Troubleshooting

- **MCP Server Fails to Start (Claude Desktop):**
    - **`spawn ... ENOENT` Error:** Double-check the absolute paths for `command` and `args` in `mcp.json`. Ensure the `.venv/bin/python` file actually exists. Verify the `workingDirectory` is correct.
    - **Immediate Disconnect:** Ensure the FastAPI server is running *before* activating the tool in Claude. Check the FastAPI server logs for errors during startup or when the MCP server tries the initial health check. Ensure the MCP server process launched by Claude has permissions to read files/make network connections.
- **Tools Return Empty Lists or Errors:**
    - **`401 Unauthorized` in FastAPI logs:** The cookie is invalid or expired. Re-run `python src/mcp/login.py`.
    - **Connection Error in MCP logs:** The FastAPI server is not running or not accessible at `http://127.0.0.1:8000`. Check the FastAPI terminal.
    - **Other FastAPI Errors:** Check the FastAPI server logs for specific Python exceptions or error messages from the `alexa_shopping_list` modules.
- **Login Script (`login.py`) Errors:**
    - **WebDriver Errors:** Ensure Google Chrome is installed/updated. `webdriver-manager` should handle drivers, but check its logs or try clearing its cache (`~/.wdm`).
    - **Cookie Extraction Failure:** Complete the login fully in the browser before pressing Enter in the console.
