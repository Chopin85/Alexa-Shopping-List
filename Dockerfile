# Use a slim Python base image
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
# Add the root app directory to PYTHONPATH so src.* imports work
ENV PYTHONPATH="/app"

# Install tini for proper signal handling
RUN apt-get update && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only the API requirements file first to leverage Docker cache
COPY src/api/requirements.txt ./

# Install API Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire src directory which contains api, mcp, auth
# The API needs access to shared modules like config if they exist at the src level
COPY ./src ./src

# Create the data directory for cookies using an absolute path
# This assumes the API server might write cookies here, adjust if needed
RUN mkdir -p /app/data

# Use tini as the entrypoint
ENTRYPOINT ["/usr/bin/tini", "--"]

# Command to run the application using uvicorn
# Points to the FastAPI app instance within the copied src structure
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8800"]

