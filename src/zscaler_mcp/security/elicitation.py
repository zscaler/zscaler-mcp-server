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
    5. Server recomputes the HMAC; mismatch (tampered args), expiry, or a token
       that was already redeemed → reject.

Tokens expire after ``ZSCALER_MCP_CONFIRMATION_TTL`` seconds (default 300) and
are **single-use**: a redeemed signature is recorded until it expires, so the
same approval cannot authorize a second execution.

Signing key
-----------
By default the key is ephemeral — generated at process start, never stored. That
is the right posture for stdio and single-instance HTTP, but it means a token
minted by one process cannot be validated by another. Operators running
**multiple replicas** behind a load balancer (Cloud Run, AKS, ECS, Container
Apps) must set ``ZSCALER_MCP_CONFIRMATION_SECRET`` to a shared value, otherwise
a confirmation retry that lands on a different replica is rejected as a
parameter mismatch.

Known limits (deliberate, documented in ``docs/guides/mcp-protocol.md``):

* The single-use ledger is **per process**. With a shared secret across replicas,
  replay is prevented per replica, not globally. A shared ledger would require the
  session store this server deliberately does not have.
* Tokens are **not bound to the calling principal**. Any authenticated caller
  holding a token can redeem it.

Both limits are resolved by migrating to the MCP SDK's ``RequestStateSecurity``
(AEAD + principal/audience binding + key-rotation ring) once the server moves to
``mcp`` 2.x; see the migration section of ``docs/guides/mcp-protocol.md``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

#: Env var holding a shared signing key. Required for multi-replica deployments.
SECRET_ENV_VAR = "ZSCALER_MCP_CONFIRMATION_SECRET"

#: Fallback key for the single-process case. Random per process, never stored.
_EPHEMERAL_SECRET: bytes = secrets.token_bytes(32)

CONFIRMATION_TOKEN_TTL_SECONDS = int(os.environ.get("ZSCALER_MCP_CONFIRMATION_TTL", "300"))

# Redeemed token signatures -> their expiry, so a valid approval can only be
# spent once. Bounded by (delete rate x TTL): entries are swept on every write,
# and every entry is removed no later than its own expiry.
_consumed_lock = threading.Lock()
_consumed_signatures: Dict[str, float] = {}


def _configured_secret() -> str:
    """The operator-supplied shared signing key, or an empty string."""
    return os.environ.get(SECRET_ENV_VAR, "").strip()


def uses_shared_secret() -> bool:
    """Whether confirmation tokens are signed with an operator-supplied key.

    ``False`` means the ephemeral per-process key is in use, which is safe for
    stdio / single-instance but breaks across replicas and restarts.
    """
    return bool(_configured_secret())


def _server_secret() -> bytes:
    """Resolve the HMAC key for this call.

    Read from the environment each time (rather than cached at import) so a
    lifecycle reload picks up a rotated key without a restart, and so tests can
    set it with ``monkeypatch.setenv``. ``os.environ`` lookup is a dict hit; the
    SHA-256 derivation lets the operator supply a key of any length or encoding.
    """
    configured = _configured_secret()
    if configured:
        return hashlib.sha256(configured.encode("utf-8")).digest()
    return _EPHEMERAL_SECRET


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
    """Create a short-lived, single-use HMAC token bound to tool_name + params.

    The nonce is what makes each issued token distinct. Without it the token is a
    pure function of (tool, params, expiry-second), so two tokens minted in the
    same second for the same operation would be byte-identical — and once
    single-use tracking exists, the second one would be born already spent. That
    breaks two real flows: re-approving after a failed execution, and performing
    the same operation twice inside one TTL window.
    """
    expiry = int(time.time()) + CONFIRMATION_TOKEN_TTL_SECONDS
    nonce = secrets.token_hex(8)
    payload = _canonical_payload(tool_name, params) + f":{expiry}:{nonce}"
    sig = hmac.new(_server_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{expiry}:{nonce}:{sig}"


def _consume_signature(sig: str, expiry: float) -> bool:
    """Record a verified signature as spent. ``False`` if it was already spent.

    Called only AFTER the HMAC verifies, so an attacker cannot burn a victim's
    token by submitting guesses — an unverified signature never reaches the
    ledger. Expired entries are swept on each write, which keeps the ledger
    bounded without a background task.
    """
    now = time.time()
    with _consumed_lock:
        for spent, spent_expiry in list(_consumed_signatures.items()):
            if spent_expiry <= now:
                del _consumed_signatures[spent]
        if sig in _consumed_signatures:
            return False
        _consumed_signatures[sig] = expiry
        return True


def _reset_consumed_for_testing() -> None:
    """Clear the single-use ledger. Test-support only."""
    with _consumed_lock:
        _consumed_signatures.clear()


def _validate_token(
    token: str, tool_name: str, params: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """Validate an HMAC confirmation token against the current args."""
    parts = token.split(":", 2)
    if len(parts) != 3:
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

    nonce, sig = parts[1], parts[2]
    payload = _canonical_payload(tool_name, params) + f":{expiry}:{nonce}"
    expected = hmac.new(_server_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig, expected):
        return False, (
            "Confirmation token does not match the submitted parameters. "
            "The operation parameters may have been modified after approval. "
            "Please retry the operation from the beginning."
        )

    # Single-use: an approval authorizes exactly one execution. Spending happens
    # here — the last gate before the caller proceeds to mutate — so a token is
    # never marked spent for a call that was rejected for some other reason.
    if not _consume_signature(sig, expiry):
        return False, (
            "Confirmation token has already been used. "
            "Each approval authorizes a single operation. "
            "Please retry the operation to get a new confirmation token."
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


def log_confirmation_posture(transport: str) -> None:
    """Log the destructive-confirmation posture once at startup.

    Only meaningful when write tools are enabled, so the caller gates on that.
    The ephemeral-key warning is limited to HTTP transports: stdio is a single
    process by construction, so there is no cross-replica retry to break.
    """
    if should_skip_confirmations():
        logger.warning(
            "Destructive-operation confirmation is DISABLED "
            "(ZSCALER_MCP_SKIP_CONFIRMATIONS=true). Delete tools will execute "
            "without a confirmation step."
        )
        return

    if transport != "stdio" and not uses_shared_secret():
        logger.warning(
            "Confirmation tokens are signed with an EPHEMERAL per-process key. "
            "If this server runs as more than one replica, a confirmation retry "
            "that lands on a different replica will be rejected. Set %s to a "
            "shared value across replicas to fix this.",
            SECRET_ENV_VAR,
        )
    else:
        logger.info(
            "Destructive-operation confirmation active (single-use, TTL %ds, %s key).",
            CONFIRMATION_TOKEN_TTL_SECONDS,
            "shared" if uses_shared_secret() else "ephemeral",
        )


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
