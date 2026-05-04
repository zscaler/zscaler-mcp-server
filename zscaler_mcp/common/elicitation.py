"""Cryptographic confirmation for write operations.

Write operations (create, update, delete) require confirmation before execution.
The confirmation is cryptographically bound to the exact tool name and parameters
using HMAC-SHA256, preventing a compromised or hallucinating AI agent from
swapping parameters between the user's approval and the actual execution.

Flow:
    1. Agent calls a write tool without a confirmation_token.
    2. Server generates an HMAC token bound to (tool_name + canonical args + expiry)
       and returns it in the confirmation message.
    3. Agent presents the operation details to the user for approval.
    4. If the user approves, the agent retries with the same args + the token.
    5. Server recomputes the HMAC from the submitted args. If it matches and
       hasn't expired, the operation proceeds. If the args were changed, the
       HMAC won't match and the request is rejected.

The server secret is generated once at process startup (ephemeral, never stored).
Tokens expire after CONFIRMATION_TOKEN_TTL_SECONDS (default: 5 minutes).
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional

from zscaler_mcp.common.logging import get_logger

logger = get_logger(__name__)

_SERVER_SECRET: bytes = secrets.token_bytes(32)

CONFIRMATION_TOKEN_TTL_SECONDS = int(os.environ.get("ZSCALER_MCP_CONFIRMATION_TTL", "300"))


def _canonical_payload(tool_name: str, params: Dict[str, Any]) -> str:
    """Deterministic string representation of tool + params for HMAC input."""
    clean = {
        k: v
        for k, v in params.items()
        if k not in ("confirmed", "confirmation_token", "service", "kwargs")
        and not k.startswith("_")
    }
    return tool_name + ":" + json.dumps(clean, sort_keys=True, separators=(",", ":"))


def _generate_token(tool_name: str, params: Dict[str, Any]) -> str:
    """Create a short-lived HMAC token bound to tool_name + params."""
    expiry = int(time.time()) + CONFIRMATION_TOKEN_TTL_SECONDS
    payload = _canonical_payload(tool_name, params) + f":{expiry}"
    sig = hmac.new(_SERVER_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{expiry}:{sig}"


def _validate_token(
    token: str, tool_name: str, params: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """Validate an HMAC confirmation token against the current args.

    Returns (valid, error_message). error_message is None on success.
    """
    parts = token.split(":", 1)
    if len(parts) != 2:
        return False, "Malformed confirmation token"

    try:
        expiry = int(parts[0])
    except ValueError:
        return False, "Malformed confirmation token (invalid expiry)"

    if time.time() > expiry:
        return False, (
            "Confirmation token has expired. "
            "Please retry the operation to get a new confirmation token."
        )

    sig = parts[1]
    payload = _canonical_payload(tool_name, params) + f":{expiry}"
    expected = hmac.new(_SERVER_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig, expected):
        return False, (
            "Confirmation token does not match the submitted parameters. "
            "The operation parameters may have been modified after approval. "
            "Please retry the operation from the beginning."
        )

    return True, None


def extract_confirmed_from_kwargs(kwargs_value: Any) -> Optional[str]:
    """Extract confirmation_token from the kwargs parameter.

    In MCP/FastMCP context, kwargs is a literal parameter that may receive:
    - A dict: {"confirmation_token": "12345:abc..."} or {"confirmed": True}
    - A JSON string: '{"confirmation_token": "12345:abc..."}'
    - An empty string/dict: "" or {}

    Returns:
        The confirmation_token string if present, None otherwise.
    """
    data = kwargs_value
    if isinstance(data, str):
        if not data or data == "{}":
            return None
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return None

    if isinstance(data, dict):
        token = data.get("confirmation_token")
        if token:
            return str(token)
        if data.get("confirmed") or data.get("confirm"):
            return "__deprecated_bool_confirmed__"

    return None


def should_skip_confirmations() -> bool:
    """Check if confirmations should be skipped (for automation/CI/CD)."""
    return os.environ.get("ZSCALER_MCP_SKIP_CONFIRMATIONS", "").lower() == "true"


def generate_confirmation_message(tool_name: str, params: Dict[str, Any], token: str) -> str:
    """Generate a confirmation message with a cryptographic token.

    The AI agent should present the operation details to the user and,
    if approved, retry with the provided confirmation_token.
    """
    display_params = {
        k: v
        for k, v in params.items()
        if k not in ("confirmed", "confirmation_token", "service")
        and not k.startswith("_")
    }

    retry_instruction = (
        f'To proceed, retry this tool call with: kwargs=\'{{"confirmation_token": "{token}"}}\''
    )

    if "delete_" in tool_name or "bulk_delete_" in tool_name:
        resource_type = tool_name.split("delete_", 1)[-1].replace("_", " ").title()
        resource_id = (
            params.get("id") or params.get("connector_id") or params.get("name") or "unknown"
        )

        return (
            f"DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: DELETE {resource_type}\n"
            f"Resource ID/Name: {resource_id}\n\n"
            f"WARNING: This action CANNOT be undone!\n\n"
            f"To proceed, please confirm that you want to delete this resource.\n"
            f"{retry_instruction}"
        )

    if "create_" in tool_name:
        resource_type = tool_name.split("create_", 1)[-1].replace("_", " ").title()
        name = params.get("name") or "new resource"

        msg = (
            f"CREATE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: CREATE {resource_type}\n"
            f"Resource Name: {name}\n"
        )

        if len(display_params) > 1:
            msg += "\nConfiguration:\n"
            for key, value in list(display_params.items())[:8]:
                if key != "name":
                    value_str = str(value)[:80] + ("..." if len(str(value)) > 80 else "")
                    msg += f"  - {key}: {value_str}\n"

        msg += f"\nPlease confirm that you want to create this resource.\n{retry_instruction}"
        return msg

    if "update_" in tool_name:
        resource_type = tool_name.split("update_", 1)[-1].replace("_", " ").title()
        resource_id = params.get("id") or params.get("name") or "resource"

        msg = (
            f"UPDATE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: UPDATE {resource_type}\n"
            f"Resource ID/Name: {resource_id}\n"
        )

        if len(display_params) > 1:
            msg += "\nChanges to be applied:\n"
            for key, value in list(display_params.items())[:8]:
                if key not in ("id",):
                    value_str = str(value)[:80] + ("..." if len(str(value)) > 80 else "")
                    msg += f"  - {key}: {value_str}\n"

        msg += f"\nPlease confirm that you want to update this resource.\n{retry_instruction}"
        return msg

    return (
        f"WRITE OPERATION - CONFIRMATION REQUIRED\n\n"
        f"Operation: {tool_name}\n\n"
        f"Parameters:\n{json.dumps(display_params, indent=2)}\n\n"
        f"Please confirm that you want to proceed with this operation.\n"
        f"{retry_instruction}"
    )


def check_confirmation(tool_name: str, confirmed: Any, params: Dict[str, Any]) -> Optional[str]:
    """Check if a write operation has a valid cryptographic confirmation.

    Called at the start of every write tool. The ``confirmed`` argument is
    the value returned by ``extract_confirmed_from_kwargs`` — either a
    confirmation_token string, the deprecated-bool sentinel
    ``"__deprecated_bool_confirmed__"``, or None (no confirmation yet).

    Returns a confirmation message (str) if the caller should stop and ask
    the user, or None if the operation may proceed.
    """
    if should_skip_confirmations():
        logger.debug(
            "Skipping confirmation for %s (ZSCALER_MCP_SKIP_CONFIRMATIONS=true)", tool_name
        )
        return None

    if confirmed is None or confirmed is False:
        token = _generate_token(tool_name, params)
        logger.info("Confirmation required for %s", tool_name)
        return generate_confirmation_message(tool_name, params, token)

    if confirmed == "__deprecated_bool_confirmed__":
        token = _generate_token(tool_name, params)
        logger.warning(
            "Deprecated confirmed=true received for %s. "
            "Please use confirmation_token instead. Generating new token.",
            tool_name,
        )
        return generate_confirmation_message(tool_name, params, token)

    token_str = str(confirmed)
    valid, error = _validate_token(token_str, tool_name, params)
    if not valid:
        logger.warning("Confirmation token rejected for %s: %s", tool_name, error)
        new_token = _generate_token(tool_name, params)
        return f"Confirmation rejected: {error}\n\n" + generate_confirmation_message(
            tool_name, params, new_token
        )

    logger.info("Confirmed (token valid): %s", tool_name)
    return None
