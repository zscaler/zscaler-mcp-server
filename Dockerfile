# Use a Python image with uv pre-installed
# ghcr.io/astral-sh/uv:0.10.4-python3.14-alpine (multi-arch: amd64, arm64)
FROM ghcr.io/astral-sh/uv:0.10.4-python3.14-alpine@sha256:35e9528631d62049f00590f8f0e65124081764d079a98231ce49c7effb6b6ef5 AS uv

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
# Include [gcp] extras for GCP Secret Manager support
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-editable --extra gcp

# Remove unnecessary files from the virtual environment before copying
RUN find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + && \
    find /app/.venv -name '*.pyc' -delete && \
    find /app/.venv -name '*.pyo' -delete && \
    echo "Cleaned up .venv"

# Final stage
# python:3.14-alpine (multi-arch: amd64, arm64)
FROM python:3.14-alpine@sha256:6f873e340e6786787a632c919ecfb1d2301eb33ccfbe9f0d0add16cbc0892116

# Security: Upgrade Alpine packages to patched versions.
# Pins exact versions to satisfy security assessment requirements:
# - libcrypto3/libssl3 ≥3.5.6-r0 fixes CVE-2026-28390 (openssl NULL ptr deref)
# - zlib ≥1.3.2-r0 fixes CVE-2026-22184 (buffer overflow in untgz)
# - musl ≥1.2.5-r23, libuuid ≥2.41.4-r0 (upstream security patches)
RUN apk update && \
    apk upgrade --no-cache \
        libcrypto3 \
        libssl3 \
        musl \
        musl-utils \
        libuuid \
        apk-tools \
        alpine-baselayout \
        alpine-baselayout-data && \
    rm -rf /var/cache/apk/*

# Security: Upgrade pip and setuptools to fix:
# - CVE-2025-8869 (pip)
# - CVE-2024-6345, CVE-2025-47273 (setuptools)
RUN pip install --no-cache-dir --upgrade pip>=25.3 setuptools>=82.0.0 wheel>=0.46.2

# Create a non-root user 'app'
RUN adduser -D -h /home/app -s /bin/sh app
WORKDIR /app
USER app

COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

LABEL io.modelcontextprotocol.server.name="io.github.zscaler/zscaler-mcp-server"

ENTRYPOINT ["zscaler-mcp"]