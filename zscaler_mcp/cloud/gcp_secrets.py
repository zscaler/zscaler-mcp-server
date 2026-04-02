"""
GCP Secret Manager credential loader for Zscaler MCP Server.

When the server runs on GCP (Cloud Run, GKE, Compute Engine), this module
can fetch Zscaler API credentials from GCP Secret Manager at startup and
inject them as environment variables before the server initializes its
SDK clients.

Activation:
    Set ``ZSCALER_MCP_GCP_SECRET_MANAGER=true`` to enable.

Required environment:
    ZSCALER_MCP_GCP_SECRET_MANAGER  — "true" to enable (default: "false")
    GCP_PROJECT_ID                  — GCP project containing the secrets

Naming convention:
    Environment variable names are converted to Secret Manager IDs by
    lowercasing and replacing underscores with hyphens::

        ZSCALER_CLIENT_ID      →  zscaler-client-id
        ZSCALER_CLIENT_SECRET  →  zscaler-client-secret

    Secrets that don't exist in Secret Manager are silently skipped
    (the env var retains whatever value it already has).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

CREDENTIAL_KEYS = (
    "ZSCALER_CLIENT_ID",
    "ZSCALER_CLIENT_SECRET",
    "ZSCALER_VANITY_DOMAIN",
    "ZSCALER_CUSTOMER_ID",
    "ZSCALER_CLOUD",
    "ZSCALER_MCP_WRITE_ENABLED",
    "ZSCALER_MCP_WRITE_TOOLS",
)

_REQUIRED_KEYS = ("ZSCALER_CLIENT_ID", "ZSCALER_CLIENT_SECRET")


def _env_key_to_secret_id(key: str) -> str:
    return key.lower().replace("_", "-")


def is_enabled() -> bool:
    return os.getenv("ZSCALER_MCP_GCP_SECRET_MANAGER", "").strip().lower() in (
        "true",
        "1",
        "yes",
    )


def load_secrets() -> None:
    """Fetch credentials from GCP Secret Manager and set as env vars.

    No-op when ``ZSCALER_MCP_GCP_SECRET_MANAGER`` is not ``true``.
    Raises ``SystemExit`` on fatal errors so the server stops cleanly.
    """
    if not is_enabled():
        return

    project_id = os.getenv("GCP_PROJECT_ID", "").strip()
    if not project_id:
        raise SystemExit(
            "GCP Secret Manager is enabled (ZSCALER_MCP_GCP_SECRET_MANAGER=true) "
            "but GCP_PROJECT_ID is not set."
        )

    try:
        from google.cloud import secretmanager  # type: ignore[import-untyped]
        from google.api_core import exceptions as gcp_exceptions  # type: ignore[import-untyped]
    except ImportError:
        raise SystemExit(
            "GCP Secret Manager is enabled but google-cloud-secret-manager is not installed.\n"
            "Install with:  pip install google-cloud-secret-manager\n"
            "Or use the 'gcp' extras:  pip install zscaler-mcp[gcp]"
        )

    logger.info("Loading credentials from GCP Secret Manager (project: %s)", project_id)

    client = secretmanager.SecretManagerServiceClient()
    loaded: list[str] = []

    for env_key in CREDENTIAL_KEYS:
        secret_id = _env_key_to_secret_id(env_key)
        resource = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

        try:
            response = client.access_secret_version(request={"name": resource})
            value = response.payload.data.decode("UTF-8")
            os.environ[env_key] = value
            loaded.append(env_key)

            if "SECRET" in env_key or "PASSWORD" in env_key:
                logger.info("  %s = ********", env_key)
            else:
                logger.info("  %s = %s", env_key, value[:20] + "..." if len(value) > 20 else value)

        except gcp_exceptions.NotFound:
            logger.debug("  %s: secret '%s' not found — skipping", env_key, secret_id)
        except gcp_exceptions.PermissionDenied:
            if env_key in _REQUIRED_KEYS:
                logger.error(
                    "  %s: permission denied for secret '%s'. "
                    "Grant roles/secretmanager.secretAccessor to the service account.",
                    env_key,
                    secret_id,
                )
                raise SystemExit(f"Permission denied accessing secret: {secret_id}")
            logger.debug(
                "  %s: secret '%s' not found or no access — skipping (optional)",
                env_key,
                secret_id,
            )

    missing = [k for k in _REQUIRED_KEYS if k not in loaded and not os.getenv(k)]
    if missing:
        raise SystemExit(
            f"Required credentials not found in Secret Manager or environment: "
            f"{', '.join(missing)}\n"
            f"Create the secrets in project '{project_id}' or pass them as env vars."
        )

    logger.info("Loaded %d credential(s) from GCP Secret Manager", len(loaded))
