# Use uv for fast dependency resolution
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.11-alpine AS uv

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# Clean up cache
RUN find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + && \
    find /app/.venv -name '*.pyc' -delete && \
    find /app/.venv -name '*.pyo' -delete && \
    echo "Cleaned up .venv"

# Final stage
FROM --platform=linux/arm64 python:3.11-alpine

# Create a non-root user 'app'
RUN adduser -D -h /home/app -s /bin/sh app

# Set working directory
WORKDIR /app

# Copy virtual environment from uv stage
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Copy source code
COPY --from=uv --chown=app:app /app/zscaler_mcp /app/zscaler_mcp

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER app

# Expose port 8000 for HTTP transport
EXPOSE 8000

# Set the entrypoint to run the FastAPI web server
CMD ["uvicorn", "zscaler_mcp.web_server:app", "--host", "0.0.0.0", "--port", "8000"]
