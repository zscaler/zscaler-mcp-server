# Use a Python image with uv pre-installed
# ghcr.io/astral-sh/uv:python3.13-alpine (multi-arch: amd64, arm64)
FROM ghcr.io/astral-sh/uv@sha256:3ce89663b5309e77087de25ca805c49988f2716cdb2c6469b1dec2764f58b141 AS uv

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Generate proper TOML lockfile first
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv lock

# Install the project's dependencies using the lockfile
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-editable

# Remove unnecessary files from the virtual environment before copying
RUN find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + && \
    find /app/.venv -name '*.pyc' -delete && \
    find /app/.venv -name '*.pyo' -delete && \
    echo "Cleaned up .venv"

# Final stage
# python:3.13-alpine (multi-arch: amd64, arm64)
# Using latest tag to get security patches - pin after security review
FROM python:3.13-alpine

# Security: Update Alpine packages to latest versions to fix:
# - CVE-2024-58251, CVE-2025-46394 (busybox)
# - CVE-2025-9230, CVE-2025-9231, CVE-2025-9232 (openssl/libcrypto3/libssl3)
RUN apk update && apk upgrade --no-cache && \
    rm -rf /var/cache/apk/*

# Security: Upgrade pip and setuptools to fix:
# - CVE-2025-8869 (pip)
# - CVE-2024-6345, CVE-2025-47273 (setuptools)
RUN pip install --no-cache-dir --upgrade pip>=25.3 setuptools>=78.1.1

# Create a non-root user 'app'
RUN adduser -D -h /home/app -s /bin/sh app
WORKDIR /app
USER app

COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["zscaler-mcp"]