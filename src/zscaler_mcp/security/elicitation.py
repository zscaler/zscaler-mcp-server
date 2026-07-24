"""Cryptographic confirmation for destructive operations.

Ported from v1 (``zscaler_mcp/common/elicitation.py``). Matching v1, only
DESTRUCTIVE operations (delete / bulk-delete) require confirmation before
execution; create/update are gated solely by the ``--write-tools`` allowlist
(read-only by default). The confirmation is cryptographically bound to the exact
tool name and parameters via HMAC-SHA256, so a compromised or hallucinating
agent cannot swap parameters between the user's approval and the actual
execution.

This module itself stays policy-agnostic — :func:`check_confirmation` and
:func:`generate_confirmation_message` can confirm any tool name (the create_/
update_ branches are retained for that reason). The decision of *which* actions
are confirmation-gated lives in the bridge (:mod:`zscaler_mcp.registry.fastmcp_bridge`),
which only invokes confirmation for ``action == delete``.

Flow:
    1. Agent calls a write tool without a ``confirmation_token``.
    2. Server returns an HMAC token bound to (tool_name + canonical args + expiry).
    3. Agent shows the operation to the user for approval.
    4. On approval, the agent retries with the same args + the token.
    5. Server recomputes the HMAC; mismatch (tampered args) or expiry → reject.

The server secret is generated once at process startup (ephemeral, never
stored). Tokens expire after ``ZSCALER_MCP_CONFIRMATION_TTL`` seconds (default
300).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

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
    """Validate an HMAC confirmation token against the current args."""
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
    """Extract a confirmation_token (or the deprecated-bool sentinel) from kwargs."""
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
    """Whether confirmations should be skipped (automation / CI)."""
    return os.environ.get("ZSCALER_MCP_SKIP_CONFIRMATIONS", "").lower() == "true"


def _resource_identifier(params: Dict[str, Any]) -> str:
    """Best-effort human-readable identifier for the resource being acted on.

    Delete tools across services use different primary-key parameter names —
    ``id``, ``connector_id``, ``group_id``, ``segment_id``, ``rule_id`` … — so a
    fixed lookup of ``id``/``connector_id``/``name`` prints ``unknown`` for most
    of them, defeating the whole point of the human-facing confirmation prompt.
    Prefer an explicit ``id``/``name``, then fall back to the first ``*_id``
    parameter present (deterministic ordering), then ``unknown``.
    """
    if params.get("id"):
        return str(params["id"])
    if params.get("name"):
        return str(params["name"])
    for key in sorted(params):
        if key.endswith("_id") and params[key]:
            return f"{params[key]} ({key})"
    return "unknown"


def generate_confirmation_message(tool_name: str, params: Dict[str, Any], token: str) -> str:
    """Build a human-readable confirmation message carrying the token."""
    display_params = {
        k: v
        for k, v in params.items()
        if k not in ("confirmed", "confirmation_token", "service") and not k.startswith("_")
    }

    retry_instruction = (
        f'To proceed, retry this tool call with: kwargs=\'{{"confirmation_token": "{token}"}}\''
    )

    if "delete_" in tool_name or "bulk_delete_" in tool_name:
        resource_type = tool_name.split("delete_", 1)[-1].replace("_", " ").title()
        resource_id = _resource_identifier(params)
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
    """Check a write op for valid confirmation.

    Returns a confirmation message (str) if the caller must stop and ask the
    user, or ``None`` if the operation may proceed.
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
