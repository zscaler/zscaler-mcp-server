"""Native MCP 2026-07-28 elicitation — InputRequiredResult prototype.

Implements **SEP-2322 (Multi Round-Trip Requests)** from the
``2026-07-28`` Model Context Protocol release candidate. This module is
the spec-compliant successor to :mod:`zscaler_mcp.common.elicitation`'s
HMAC-token-in-prose flow.

**Status: prototype.** Native dispatch is opt-in via
``ZSCALER_MCP_NATIVE_ELICITATION=true``. After the ``mcp`` / ``fastmcp``
SDK ships ``2026-07-28`` support (P1 in the impact analysis), the opt-in
will be replaced by per-client capability negotiation through
``server/discover``. Until then this module exists alongside the legacy
flow and is wired in via :func:`zscaler_mcp.common.elicitation.check_confirmation`
so every destructive tool in the repo gets the new shape for free.

Wire shape (returned in native mode in place of the legacy prose
message)::

    {
        "resultType": "inputRequired",
        "inputRequests": [
            {
                "name": "confirm",
                "schema": {
                    "type": "boolean",
                    "description": "DESTRUCTIVE: delete segment group 12345?"
                },
                "required": true
            }
        ],
        "requestState": "<opaque base64url-encoded HMAC blob>",
        "_legacy_message": "DESTRUCTIVE: delete segment group 12345?"
    }

The agent collects the user's answers, then re-calls the tool with the
spec-shaped ``inputResponses`` + ``requestState`` echoed back in the
``kwargs`` parameter (the transport surface FastMCP exposes today)::

    kwargs = '{"inputResponses": {"confirm": true}, "requestState": "<echoed>"}'

After the SDK upgrade lands, ``inputResponses`` and ``requestState``
will travel as native JSON-RPC fields on ``params``; the ``kwargs``
wrapping disappears and tool signatures get cleaner.

requestState binding & multi-instance verification
--------------------------------------------------

``requestState`` is HMAC-SHA256-signed over ``tool_name | canonical_args
| expiry``. Same binding the legacy token had, just in the spec-defined
opaque shape so clients never have to parse it.

By default the HMAC key is a per-process random secret (``secrets.token_bytes(32)``)
— fine for single-instance dev. For multi-replica deployments
(AgentCore Gateway, Cloud Run min-instances >= 2, AKS multi-pod) set the
same ``ZSCALER_MCP_ELICITATION_SECRET`` value on every replica and a
``requestState`` issued by replica A can be verified by replica B. This
is the ``test_request_state_stateless_any_instance`` invariant from the
impact analysis.

Never hardcode the secret in source or commit it to a repo. Inject it
through your normal secret-management path (GCP Secret Manager, AWS
Secrets Manager, Azure Key Vault, K8s Secret).
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple

from zscaler_mcp.common.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration & secrets
# ---------------------------------------------------------------------------

REQUEST_STATE_VERSION = "v1"

CONFIRMATION_TTL_SECONDS = int(os.environ.get("ZSCALER_MCP_CONFIRMATION_TTL", "300"))

_SHARED_SECRET_ENV = os.environ.get("ZSCALER_MCP_ELICITATION_SECRET", "")

# Shared secret: same value on every replica → cross-instance requestState
# verification. Falls back to a per-process random key for single-instance.
_SERVER_SECRET: bytes = (
    _SHARED_SECRET_ENV.encode("utf-8") if _SHARED_SECRET_ENV else secrets.token_bytes(32)
)

if _SHARED_SECRET_ENV:
    logger.info(
        "Native elicitation: ZSCALER_MCP_ELICITATION_SECRET configured "
        "(cross-instance requestState verification enabled)."
    )


def is_native_elicitation_enabled() -> bool:
    """Whether the server should respond with ``InputRequiredResult`` dicts.

    Opt-in via ``ZSCALER_MCP_NATIVE_ELICITATION=true`` for the prototype.
    Will be replaced by per-client capability detection (negotiated via
    ``server/discover`` per SEP-2575) once the ``mcp`` / ``fastmcp`` SDK
    upgrade (P1) lands.
    """
    return os.environ.get("ZSCALER_MCP_NATIVE_ELICITATION", "").lower() == "true"


# ---------------------------------------------------------------------------
# requestState — opaque HMAC-signed blob
# ---------------------------------------------------------------------------

# Excluded keys mirror the set in elicitation.py::_canonical_payload so both
# flows use exactly the same binding contract. Changing this set in one
# place without the other would create a flow where the legacy HMAC and
# the native requestState bind different surfaces of the call.
_EXCLUDED_KEYS = frozenset({"confirmed", "confirmation_token", "service", "kwargs"})


def _canonical_args(tool_name: str, params: Dict[str, Any]) -> str:
    """Deterministic JSON-stable string of tool + args for HMAC input.

    Identical normalization to ``elicitation.py::_canonical_payload`` so
    the native and legacy paths use the same canonicalization. Tests
    cross-check this in ``test_elicitation_native.py``.
    """
    clean = {
        k: v
        for k, v in params.items()
        if k not in _EXCLUDED_KEYS and not k.startswith("_")
    }
    return tool_name + ":" + json.dumps(clean, sort_keys=True, separators=(",", ":"))


def _b64url_encode(payload: bytes) -> str:
    """URL-safe base64 with stripped padding (RFC 4648 §5)."""
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _b64url_decode(payload: str) -> bytes:
    """URL-safe base64 with re-added padding."""
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def _build_request_state(tool_name: str, params: Dict[str, Any]) -> str:
    """Build an opaque, HMAC-signed requestState blob.

    Decoded format: ``<version>.<expiry>.<hex-sig>``

    The blob is base64url-encoded so it survives any transport without
    escaping. The version prefix lets future revisions migrate without
    silently mis-verifying old blobs.
    """
    expiry = int(time.time()) + CONFIRMATION_TTL_SECONDS
    payload = _canonical_args(tool_name, params) + f":{expiry}"
    sig = hmac.new(_SERVER_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    blob = f"{REQUEST_STATE_VERSION}.{expiry}.{sig}".encode("utf-8")
    return _b64url_encode(blob)


def _verify_request_state(
    state: str, tool_name: str, params: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Verify an opaque requestState against the resubmitted tool + args.

    Returns ``(valid, error_message)``. ``error_message`` is ``None`` on
    success. All failure modes return a human-readable explanation the
    server can pass straight back to the agent.
    """
    if not isinstance(state, str) or not state:
        return False, "Missing or empty requestState."

    try:
        decoded = _b64url_decode(state).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False, "Malformed requestState (invalid base64)."

    parts = decoded.split(".", 2)
    if len(parts) != 3:
        return False, "Malformed requestState (wrong field count)."

    version, expiry_str, sig = parts

    if version != REQUEST_STATE_VERSION:
        return False, f"Unsupported requestState version: {version!r}."

    try:
        expiry = int(expiry_str)
    except ValueError:
        return False, "Malformed requestState (invalid expiry)."

    if time.time() > expiry:
        return False, (
            "requestState has expired. Re-call the tool to obtain a fresh "
            "InputRequiredResult."
        )

    payload = _canonical_args(tool_name, params) + f":{expiry}"
    expected = hmac.new(_SERVER_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False, (
            "requestState does not match the submitted parameters. The "
            "arguments may have changed after the inputRequired prompt was "
            "issued. Re-call the tool to obtain a fresh InputRequiredResult."
        )

    return True, None


# ---------------------------------------------------------------------------
# InputRequiredResult builder
# ---------------------------------------------------------------------------


def _default_prompt(tool_name: str, params: Dict[str, Any]) -> str:
    """Build the single-sentence prompt used inside the ``confirm`` input's
    schema description.

    Shorter than the legacy multi-line prose: the spec puts the prompt
    inside ``inputRequests[].schema.description`` and clients render it
    natively (checkbox / button / boolean toggle), so multi-line
    DOOM-style banners are out of place.
    """
    display_params = {
        k: v for k, v in params.items() if k not in _EXCLUDED_KEYS and not k.startswith("_")
    }

    if "delete_" in tool_name or "bulk_delete_" in tool_name:
        resource = tool_name.split("delete_", 1)[-1].replace("_", " ")
        ident = (
            display_params.get("id")
            or display_params.get("group_id")
            or display_params.get("connector_id")
            or display_params.get("rule_id")
            or display_params.get("name")
            or "?"
        )
        return f"DESTRUCTIVE: delete {resource} {ident!s}? This cannot be undone."

    if "create_" in tool_name:
        resource = tool_name.split("create_", 1)[-1].replace("_", " ")
        name = display_params.get("name", "")
        suffix = f" '{name}'" if name else ""
        return f"Confirm: create {resource}{suffix}?"

    if "update_" in tool_name:
        resource = tool_name.split("update_", 1)[-1].replace("_", " ")
        ident = (
            display_params.get("id") or display_params.get("name") or "resource"
        )
        return f"Confirm: update {resource} {ident!s}?"

    return f"Confirm: execute {tool_name}?"


def build_input_required_result(
    tool_name: str,
    params: Dict[str, Any],
    *,
    prompt: Optional[str] = None,
    prompt_prefix: str = "",
) -> Dict[str, Any]:
    """Build an InputRequiredResult dict (SEP-2322 shape).

    Args:
        tool_name: Fully-qualified tool name (e.g. ``"zpa_delete_segment_group"``).
        params: The actual tool arguments at the call site. These get
            canonicalized and HMAC-bound into ``requestState``.
        prompt: Override the auto-generated prompt. Use sparingly — the
            default is consistent across the codebase.
        prompt_prefix: Prepended to the prompt. Used when re-issuing
            the result after a rejected retry to surface the error
            (e.g. ``"Previous request rejected: expired. "``).

    Returns:
        A dict matching the spec shape, plus a ``_legacy_message`` field
        so HMAC-aware clients can still render the prompt as plain text.
        Spec-aware clients ignore the underscore-prefixed field and use
        ``inputRequests`` instead.
    """
    base_prompt = prompt if prompt is not None else _default_prompt(tool_name, params)
    full_prompt = (prompt_prefix + base_prompt) if prompt_prefix else base_prompt

    request_state = _build_request_state(tool_name, params)

    return {
        "resultType": "inputRequired",
        "inputRequests": [
            {
                "name": "confirm",
                "schema": {
                    "type": "boolean",
                    "description": full_prompt,
                },
                "required": True,
            }
        ],
        "requestState": request_state,
        "_legacy_message": full_prompt,
    }


# ---------------------------------------------------------------------------
# Retry validation
# ---------------------------------------------------------------------------


def check_input_response(
    tool_name: str,
    params: Dict[str, Any],
    input_responses: Optional[Dict[str, Any]],
    request_state: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Validate a retry carrying ``inputResponses`` + ``requestState``.

    Returns ``(ok_to_proceed, error_message)``:

    - ``(True, None)`` — server may execute the operation.
    - ``(False, str)`` — server should re-issue an InputRequiredResult
      with ``prompt_prefix=f"Previous request rejected: {error}. "``.
    """
    if request_state is None:
        return False, (
            "Missing requestState. The agent must echo the exact value "
            "returned in the InputRequiredResult."
        )
    if input_responses is None:
        return False, (
            "Missing inputResponses. The agent must include the user's "
            "answers from the InputRequiredResult prompt."
        )
    if not isinstance(input_responses, dict):
        return False, "inputResponses must be an object."

    confirm = input_responses.get("confirm")
    if confirm is not True:
        return False, (
            "User did not confirm the destructive operation "
            "(inputResponses.confirm is not True)."
        )

    return _verify_request_state(request_state, tool_name, params)


# ---------------------------------------------------------------------------
# kwargs-shape parsing — the temporary transport vehicle until P1 lands
# ---------------------------------------------------------------------------


def extract_native_inputs_from_kwargs(
    kwargs_value: Any,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse ``inputResponses`` + ``requestState`` out of the ``kwargs`` parameter.

    Until the SDK upgrade (P1) makes these first-class JSON-RPC fields,
    spec-aware agents send them through the existing ``kwargs`` string
    parameter that destructive tools already accept::

        kwargs = '{"inputResponses": {"confirm": true}, "requestState": "<echoed>"}'

    Returns ``(input_responses, request_state)``. Either field may be
    ``None`` if absent. An entirely unrecognized ``kwargs`` shape
    returns ``(None, None)``.
    """
    data = kwargs_value
    if isinstance(data, str):
        if not data or data == "{}":
            return None, None
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return None, None

    if not isinstance(data, dict):
        return None, None

    input_responses = data.get("inputResponses")
    request_state = data.get("requestState")

    if input_responses is not None and not isinstance(input_responses, dict):
        # Malformed payload — treat as absent so the dispatcher re-issues
        # a fresh InputRequiredResult instead of crashing.
        input_responses = None
    if request_state is not None and not isinstance(request_state, str):
        request_state = None

    return input_responses, request_state


__all__ = [
    "REQUEST_STATE_VERSION",
    "CONFIRMATION_TTL_SECONDS",
    "is_native_elicitation_enabled",
    "build_input_required_result",
    "check_input_response",
    "extract_native_inputs_from_kwargs",
    # Exposed for tamper / TTL / cross-instance tests.
    "_build_request_state",
    "_verify_request_state",
    "_canonical_args",
]
