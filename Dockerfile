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

# Then, add the rest of the project source code and install it.
# Both cloud extras ship in the one image: the deployment target is selected at
# runtime by environment variable (ZSCALER_SECRET_NAME / GCP_PROJECT_ID), not by
# choosing a build, so the same image serves Docker Hub, Cloud Run and Bedrock
# AgentCore. Neither loader imports its SDK unless enabled.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-editable --extra gcp --extra aws

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
# - libcrypto3/libssl3 ≥3.5.7-r0 fixes CVE-2026-28390 (openssl NULL ptr deref)
#   and CVE-2026-34182 (CMS AuthEnvelopedData accepts forged messages). Do not
#   relax this floor to 3.5.6 — that release predates the CMS fix.
# - zlib ≥1.3.2-r0 fixes CVE-2026-22184 (buffer overflow in untgz)
# - xz-libs ≥5.8.3-r0 fixes CVE-2026-34743 (heap overflow in lzma_index_append
#   after decoding an Index with no Records)
# - musl ≥1.2.5-r23, libuuid ≥2.41.4-r0 (upstream security patches)
RUN apk update && \
    apk upgrade --no-cache \
        libcrypto3 \
        libssl3 \
        musl \
        musl-utils \
        libuuid \
        xz-libs \
        zlib \
        apk-tools \
        alpine-baselayout \
        alpine-baselayout-data && \
    rm -rf /var/cache/apk/*

# Security: remove the Python installer tooling from the runtime image.
# The application runs entirely out of /app/.venv, which uv builds without pip,
# setuptools or wheel, so nothing here needs an installer at runtime (this is
# the same assumption lifecycle.py already encodes when `update --apply`
# refuses on the container channel).
#
# Upgrading pip in place does NOT clear scanner findings: ensurepip keeps its
# own private copy of the pip wheel under ensurepip/_bundled/ that
# `pip install --upgrade pip` never rewrites, and that stale copy is what gets
# reported (CVE-2026-3219, CVE-2026-6357, CVE-2026-8643 were all raised against
# it while the installed pip was already patched). Deleting the tooling retires
# the whole class instead of chasing each release.
RUN PY_LIB="$(/usr/local/bin/python -c 'import sysconfig; print(sysconfig.get_path("stdlib"))')" && \
    /usr/local/bin/python -m pip uninstall -y setuptools wheel && \
    /usr/local/bin/python -m pip uninstall -y pip && \
    rm -rf "${PY_LIB}/ensurepip" \
           "${PY_LIB}/site-packages/pip" "${PY_LIB}/site-packages/pip-"* \
           "${PY_LIB}/site-packages/setuptools" "${PY_LIB}/site-packages/setuptools-"* \
           "${PY_LIB}/site-packages/wheel" "${PY_LIB}/site-packages/wheel-"* \
           "${PY_LIB}/site-packages/pkg_resources" && \
    if find /usr/local -name 'pip-*' -o -name 'ensurepip' | grep -q .; then \
        echo "ERROR: pip artifacts survived removal" >&2; exit 1; \
    fi

# Create a non-root user 'app'
RUN adduser -D -h /home/app -s /bin/sh app
WORKDIR /app
USER app

COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Declares the HTTP transports' default port. Bedrock AgentCore requires the
# container to listen on 8000; stdio ignores it.
EXPOSE 8000

LABEL io.modelcontextprotocol.server.name="io.github.zscaler/zscaler-mcp-server"

# No HEALTHCHECK on purpose: AgentCore manages container health at the runtime
# layer, and a Docker-level probe against the streamable-http transport would
# fail (there is no unauthenticated GET on /mcp).
ENTRYPOINT ["zscaler-mcp"]