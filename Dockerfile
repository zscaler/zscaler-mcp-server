# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pip and uv
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies using uv with --system flag
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Explicitly install zscaler-sdk-python with any additional dependencies
RUN uv pip install --system --no-cache-dir zscaler-sdk-python

# Copy the rest of the application
COPY . .

# Make your main.py executable
RUN chmod +x src/zscaler_mcp/main.py

# Verify installations
RUN python -c "import zscaler; print(f'Zscaler SDK version: {zscaler.__version__}')" || echo "Zscaler SDK check failed"

# Entrypoint command
# ENTRYPOINT ["uv", "run", "python", "main.py"]
ENTRYPOINT ["python", "main.py"]

