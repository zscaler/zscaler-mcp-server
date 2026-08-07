"""AWS Secrets Manager credential loader for the Zscaler MCP server.

Consolidated from the AWS Bedrock AgentCore fork (``zscaler_mcp/config.py``),
which existed as a separate repository solely because this loader — and a
container ``CMD`` — had no home here. When the server runs on AWS (Bedrock
AgentCore Runtime, ECS Fargate, EKS), this fetches the Zscaler API credentials
from Secrets Manager at startup and publishes them as environment variables
before anything reads them. The SDK client is created lazily on the first tool
call, so landing them in ``os.environ`` here is early enough.

Activation:
    Set ``ZSCALER_SECRET_NAME`` to the secret's name or ARN. Presence of that
    variable IS the gate — there is no separate boolean, because the AgentCore
    CloudFormation in ``integrations/aws/`` has always set exactly this one
    variable to mean "fetch my credentials from Secrets Manager".

Environment:
    ZSCALER_SECRET_NAME  — secret name or ARN (required; also the gate)
    AWS_REGION           — region of the secret. Falls back to
                           ``AWS_DEFAULT_REGION``, then to boto3's own
                           resolution chain (instance metadata / config file),
                           which is what AgentCore and ECS populate.

Secret format:
    A ``SecretString`` holding a flat JSON object of environment-variable names
    to values::

        {
          "ZSCALER_CLIENT_ID":     "...",
          "ZSCALER_CLIENT_SECRET": "...",
          "ZSCALER_VANITY_DOMAIN": "acme",
          "ZSCALER_CUSTOMER_ID":   "123456"
        }

    Only the keys in :data:`CREDENTIAL_KEYS` are published to the environment.
    The fork injected every key it found, which turned a typo — or a hostile
    edit of the secret — into an arbitrary environment variable in the server
    process. Unrecognised keys are named in a warning so a misspelling is
    diagnosable rather than silent.

    Requires the optional ``aws`` extra: ``pip install 'zscaler-mcp[aws]'``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

#: Environment variables this loader is willing to set from a secret.
#: A superset of the GCP loader's list: AWS deployments routinely carry the MCP
#: client-auth credential and the request-state key ring in the same secret,
#: because on AgentCore there is nowhere else for them to live.
CREDENTIAL_KEYS = (
    # Zscaler OneAPI (what the SDK authenticates with)
    "ZSCALER_CLIENT_ID",
    "ZSCALER_CLIENT_SECRET",
    "ZSCALER_PRIVATE_KEY",
    "ZSCALER_VANITY_DOMAIN",
    "ZSCALER_CUSTOMER_ID",
    "ZSCALER_CLOUD",
    # MCP client authentication (who may connect to this server)
    "ZSCALER_MCP_AUTH_API_KEY",
    "ZSCALER_MCP_AUTH_JWKS_URI",
    "ZSCALER_MCP_AUTH_ISSUER",
    "ZSCALER_MCP_AUTH_AUDIENCE",
    # SEP-2322 request-state key ring. Belongs in a secret rather than a plain
    # environment variable, and is REQUIRED for a multi-replica AWS deployment
    # with write tools enabled — see `_warn_if_scaled_writes_on_ephemeral_key`.
    "ZSCALER_MCP_REQUEST_STATE_KEYS",
    # Write posture, for parity with the GCP loader.
    "ZSCALER_MCP_WRITE_ENABLED",
    "ZSCALER_MCP_WRITE_TOOLS",
)

_REQUIRED_KEYS = ("ZSCALER_CLIENT_ID", "ZSCALER_CLIENT_SECRET")

#: Secret keys that satisfy ZSCALER_CLIENT_SECRET's role. A tenant using
#: JWT-based OneAPI auth stores a private key instead of a client secret, and
#: has no ZSCALER_CLIENT_SECRET to offer.
_SECRET_EQUIVALENTS = {"ZSCALER_CLIENT_SECRET": ("ZSCALER_PRIVATE_KEY",)}


def is_enabled() -> bool:
    """True when ``ZSCALER_SECRET_NAME`` names a secret to load."""
    return bool(os.getenv("ZSCALER_SECRET_NAME", "").strip())


def _region() -> Optional[str]:
    """The region to build the Secrets Manager client in, or ``None``.

    ``None`` means "let boto3 resolve it" — correct on AgentCore, ECS and EC2,
    where the region arrives through the container credential chain. The fork
    hardcoded a ``us-east-1`` default, which silently queried the wrong region
    for every deployment outside it.
    """
    for var in ("AWS_REGION", "AWS_DEFAULT_REGION"):
        value = os.getenv(var, "").strip()
        if value:
            return value
    return None


def _fetch_secret_string(secret_id: str) -> str:
    """Return the secret's ``SecretString``, or raise ``SystemExit``.

    Every failure is fatal. Starting without credentials would defer the error
    to the first tool call, where it surfaces to the agent as an opaque Zscaler
    API error rather than as the deployment problem it is.
    """
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        raise SystemExit(
            "ZSCALER_SECRET_NAME is set but boto3 is not installed.\n"
            "Install with:  pip install boto3\n"
            "Or use the 'aws' extras:  pip install 'zscaler-mcp[aws]'"
        )

    region = _region()
    logger.info(
        "Loading credentials from AWS Secrets Manager (secret: %s, region: %s)",
        secret_id,
        region or "resolved by boto3",
    )

    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_id)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        hints = {
            "ResourceNotFoundException": (
                f"No secret named '{secret_id}' in this account/region. Check "
                "ZSCALER_SECRET_NAME and AWS_REGION."
            ),
            "AccessDeniedException": (
                f"Access denied reading '{secret_id}'. Grant the execution role "
                "secretsmanager:GetSecretValue on the secret's ARN."
            ),
            "DecryptionFailureException": (
                f"Secrets Manager could not decrypt '{secret_id}'. Grant the "
                "execution role kms:Decrypt on the secret's KMS key."
            ),
            "InvalidRequestException": (
                f"'{secret_id}' cannot be read in its current state (a secret "
                "scheduled for deletion reports this)."
            ),
        }
        raise SystemExit(hints.get(code) or f"Could not read secret '{secret_id}': {exc}")
    except BotoCoreError as exc:
        # No credentials, no region, or no route to the endpoint. On VPC network
        # mode this is usually a missing interface endpoint for Secrets Manager.
        raise SystemExit(
            f"Could not reach AWS Secrets Manager for '{secret_id}': {exc}\n"
            "Check the execution role's credentials and, on VPC network mode, "
            "that a com.amazonaws.<region>.secretsmanager endpoint (or NAT) exists."
        )

    secret_string = response.get("SecretString")
    if not secret_string:
        raise SystemExit(
            f"Secret '{secret_id}' holds binary data (SecretBinary). Store the "
            "credentials as a JSON SecretString instead."
        )
    return secret_string


def load_secrets() -> None:
    """Publish credentials from AWS Secrets Manager into ``os.environ``.

    No-op unless :func:`is_enabled`. Raises ``SystemExit`` on any fatal error so
    the server stops cleanly rather than starting without credentials.

    Values from the secret **override** anything already in the environment.
    That is the point of pointing the deployment at a secret: rotating the
    secret has to beat a stale value baked into the container definition.
    """
    if not is_enabled():
        return

    secret_id = os.environ["ZSCALER_SECRET_NAME"].strip()
    secret_string = _fetch_secret_string(secret_id)

    try:
        payload = json.loads(secret_string)
    except ValueError as exc:
        raise SystemExit(
            f"Secret '{secret_id}' is not valid JSON: {exc}\n"
            'Expected a flat object, e.g. {"ZSCALER_CLIENT_ID": "...", '
            '"ZSCALER_CLIENT_SECRET": "..."}'
        )

    if not isinstance(payload, dict):
        raise SystemExit(
            f"Secret '{secret_id}' is a JSON {type(payload).__name__}, not an object. "
            "Expected a flat object mapping environment-variable names to values."
        )

    loaded: list[str] = []
    ignored: list[str] = []

    for key, value in payload.items():
        if key not in CREDENTIAL_KEYS:
            ignored.append(str(key))
            continue
        if value is None:
            continue
        os.environ[key] = str(value)
        loaded.append(key)
        if "SECRET" in key or "KEY" in key or "PASSWORD" in key:
            logger.info("  %s = ********", key)
        else:
            logger.info(
                "  %s = %s", key, str(value)[:20] + "..." if len(str(value)) > 20 else value
            )

    if ignored:
        # Named, not silent: a misspelled key and an absent one are otherwise
        # indistinguishable from the outside, and the symptom is an
        # authentication failure several minutes later.
        logger.warning(
            "Ignoring %d unrecognised key(s) in secret '%s': %s. "
            "Only these are published to the environment: %s",
            len(ignored),
            secret_id,
            ", ".join(sorted(ignored)),
            ", ".join(CREDENTIAL_KEYS),
        )

    missing = [key for key in _REQUIRED_KEYS if not _satisfied(key)]
    if missing:
        raise SystemExit(
            f"Required credentials missing after loading '{secret_id}': "
            f"{', '.join(missing)}\n"
            "Add them to the secret, or pass them as environment variables."
        )

    logger.info("Loaded %d credential(s) from AWS Secrets Manager", len(loaded))


def _satisfied(key: str) -> bool:
    """True when ``key`` — or an accepted stand-in — has a value in the env."""
    candidates = (key,) + _SECRET_EQUIVALENTS.get(key, ())
    return any(os.getenv(candidate, "").strip() for candidate in candidates)
