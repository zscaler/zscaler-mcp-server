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

Scope of this module
--------------------
This is the **pre-2026-07-28 compatibility path**. The MCP protocol grew a native
answer to server-side confirmation in SEP-2322 (multi-round-trip requests), and
the SDK ships the matching state protection in ``mcp.server.request_state``. That
is the mechanism this server adopts; this module stays only for clients that do
not negotiate the newer revision.

Consequently the known limits below are NOT fixed here — fixing them locally would
mean hand-rolling weaker versions of primitives the protocol already defines:

* **Single-process scope.** The signing key and the single-use ledger are both
  per process, so a token minted by one replica is not valid on another (nor
  after a restart). SEP-2322's ``requestState``, sealed via the SDK's
  ``RequestStateSecurity`` key ring, is the native fix.
* **No principal binding.** Any authenticated caller holding a token can redeem
  it. The SDK's ``authenticated_principal`` binding is the native fix.

See ``docs/guides/mcp-protocol.md`` for the threat model and the adoption plan.
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
from typing import Any, Callable, Dict, Literal, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

#: Signing key for this process. Random, never stored. Deliberately NOT
#: configurable: sharing a key across replicas is what SEP-2322's `requestState`
#: (sealed by the SDK's `RequestStateSecurity` key ring) exists to do, and adding
#: a bespoke env var here would duplicate that with a weaker primitive.
_SERVER_SECRET: bytes = secrets.token_bytes(32)

CONFIRMATION_TOKEN_TTL_SECONDS = int(os.environ.get("ZSCALER_MCP_CONFIRMATION_TTL", "300"))

# Redeemed token signatures -> their expiry, so a valid approval can only be
# spent once. Bounded by (delete rate x TTL): entries are swept on every write,
# and every entry is removed no later than its own expiry.
_consumed_lock = threading.Lock()
_consumed_signatures: Dict[str, float] = {}


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
    sig = hmac.new(_SERVER_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
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
    expected = hmac.new(_SERVER_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()

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


def _identify(params: Dict[str, Any], resource_name: Optional[str] = None) -> str:
    """Render the resource for a human, preferring a server-fetched name.

    ``resource_name`` comes from the API, not from the caller's arguments — see
    :func:`zscaler_mcp.registry.fastmcp_bridge._resolve_resource_name`. An id
    alone (``999999991``) is not something a human can meaningfully approve, and
    two ids differing by one digit look identical at a glance. The id is still
    shown because it, not the name, is the durable audit key.
    """
    identifier = _resource_identifier(params)
    if not resource_name:
        return identifier
    # `_resource_identifier` annotates which parameter it used ("7205 (group_id)")
    # because without a name that is the only context available. With a name the
    # annotation is noise, and nesting it reads as "…" (7205 (group_id)) — so show
    # the bare value alongside the name.
    bare = identifier.split(" (", 1)[0]
    return f'"{resource_name}" ({bare})'


def describe_destructive_operation(
    tool_name: str, params: Dict[str, Any], resource_name: Optional[str] = None
) -> str:
    """One-line description of a destructive operation, with no token in it.

    Shared by both confirmation paths so the human sees the same wording whether
    the prompt is rendered by the client (native elicitation) or embedded in the
    tool result (the token fallback).
    """
    resource_type = tool_name.split("delete_", 1)[-1].replace("_", " ").title()
    return f"DELETE {resource_type} — {_identify(params, resource_name)}"


def generate_confirmation_message(
    tool_name: str,
    params: Dict[str, Any],
    token: str,
    resource_name: Optional[str] = None,
) -> str:
    """Build a human-readable confirmation message carrying the token."""
    display_params = {
        k: v
        for k, v in params.items()
        if k not in ("confirmed", "confirmation_token", "service") and not k.startswith("_")
    }

    def retry_instruction(noun: str, verb: str) -> str:
        """Tell the agent to obtain a human's answer, then how to submit it.

        Addressed to the agent, in the imperative, and ordered deliberately: the
        human comes first, the mechanism last. The v1 wording was a bare "To
        proceed, retry this tool call with: kwargs=…" — a next-step instruction an
        agent can satisfy on its own authority, and one did exactly that in a real
        session, re-issuing the call in the same turn on the grounds that the
        original request was authorization enough. Hence step 2, which denies that
        reading outright.

        This is advisory and cannot be otherwise. On a client that supports MCP
        elicitation the human is asked over the protocol and this text is never
        reached; this path serves clients that cannot be prompted at all, where the
        only channel available is an instruction the model chooses to follow. Do not
        describe it as enforcement.
        """
        return (
            "REQUIRED NEXT STEP — do not skip:\n"
            f"1. Show this warning to the user and ask them to confirm the {noun}.\n"
            f"2. Wait for the user's reply. An earlier request to {verb} is NOT "
            "confirmation, and you must not answer on their behalf.\n"
            "3. Only if the user explicitly agrees, retry this call with: "
            f'kwargs=\'{{"confirmation_token": "{token}"}}\'\n'
            "If the user declines or does not answer, report that and stop."
        )

    if "delete_" in tool_name or "bulk_delete_" in tool_name:
        resource_type = tool_name.split("delete_", 1)[-1].replace("_", " ").title()
        resource_id = _identify(params, resource_name)
        return (
            f"DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: DELETE {resource_type}\n"
            f"Resource ID/Name: {resource_id}\n\n"
            f"WARNING: This action CANNOT be undone!\n\n"
            f"{retry_instruction('deletion', 'delete')}"
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
        msg += f"\n{retry_instruction('creation', 'create this resource')}"
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
        msg += f"\n{retry_instruction('change', 'update this resource')}"
        return msg

    return (
        f"WRITE OPERATION - CONFIRMATION REQUIRED\n\n"
        f"Operation: {tool_name}\n\n"
        f"Parameters:\n{json.dumps(display_params, indent=2)}\n\n"
        f"{retry_instruction('operation', 'run this operation')}"
    )


def check_confirmation(
    tool_name: str,
    confirmed: Any,
    params: Dict[str, Any],
    name_lookup: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[str]:
    """Check a write op for valid confirmation.

    Returns a confirmation message (str) if the caller must stop and ask the
    user, or ``None`` if the operation may proceed.

    ``name_lookup`` is deliberately a callable rather than a resolved string: it
    costs an API round trip, and every ``return None`` path below must stay free
    of one. It is invoked only where a prompt is actually rendered.
    """

    def _name() -> Optional[str]:
        return name_lookup() if name_lookup is not None else None

    if confirmed is None or confirmed is False:
        token = _generate_token(tool_name, params)
        logger.info("Confirmation required for %s", tool_name)
        return generate_confirmation_message(tool_name, params, token, _name())

    if confirmed == "__deprecated_bool_confirmed__":
        token = _generate_token(tool_name, params)
        logger.warning(
            "Deprecated confirmed=true received for %s. "
            "Please use confirmation_token instead. Generating new token.",
            tool_name,
        )
        return generate_confirmation_message(tool_name, params, token, _name())

    token_str = str(confirmed)
    valid, error = _validate_token(token_str, tool_name, params)
    if not valid:
        logger.warning("Confirmation token rejected for %s: %s", tool_name, error)
        new_token = _generate_token(tool_name, params)
        return f"Confirmation rejected: {error}\n\n" + generate_confirmation_message(
            tool_name, params, new_token, _name()
        )

    logger.info("Confirmed (token valid): %s", tool_name)
    return None


# ---------------------------------------------------------------------------
# SEP-2322 — native elicitation (the preferred path)
# ---------------------------------------------------------------------------
#
# The token flow above has a structural ceiling: the agent both *asks for* and
# *submits* the approval, so a model that has been talked into calling a delete
# completes the handshake by itself. Cryptography cannot fix that, because the
# token is not the thing being forged — the intent is.
#
# MCP's elicitation moves the decision to the other side of the connection: the
# server asks, the *client* renders a prompt, and a human answers. The reply
# arrives as a protocol-level field, not as tool-call arguments the model authors,
# so there is no slot for a hijacked model to fill in on the human's behalf.
#
# HOW THE ASKING HAPPENS IS THE FRAMEWORK'S JOB, NOT OURS. A destructive tool
# declares a resolved parameter (`Annotated[..., Resolve(fn)]`) and the resolver
# below returns an `Elicit` marker; the framework then picks the transport that
# the negotiated revision allows:
#
#   * 2026-07-28 and later — the question is returned as an `InputRequiredResult`
#     and the call resumes when the client retries with `input_responses` plus the
#     sealed `request_state`. This is the ONLY option on that revision: its
#     stateless core has no back-channel for server-initiated requests during a
#     tool call, so a direct `ctx.elicit()` fails outright.
#   * 2025-11-25 and earlier — a standalone `elicitation/create` request is sent
#     mid-call, the way it always was.
#
# Declaring the question instead of sending it is what lets one code path serve
# both revisions.
#
# Not every caller can be asked — a client must advertise the `elicitation`
# capability — so the token flow stays as an automatic fallback. The resolver
# decides which of the two applies, per call.

#: Choice values presented to the human. Deliberately explicit rather than a
#: bare yes/no: the human should have to pick the word "delete".
_APPROVE_CHOICE = "delete"
_CANCEL_CHOICE = "cancel"

#: Marker a resolver returns instead of a question when the caller cannot be
#: prompted. It travels back to the tool body as the resolved value, where
#: :func:`gate_destructive_operation` reads it as "use the token exchange".
#:
#: A sentinel is needed because a resolver has exactly two options — ask, or
#: produce a value — and "ask the other way" is not one of them.
TOKEN_FALLBACK = "__zscaler_mcp_token_fallback__"


# NOTE: this model's docstring is NOT a place for engineering rationale. Pydantic
# renders it into the JSON Schema `description`, and clients display that text to
# the human in the approval dialog — so anything written there is end-user copy,
# and reStructuredText markup shows up literally in a UI that cannot parse it.
# The design rationale therefore lives here, in a comment:
#
#   MCP restricts elicitation schemas to primitive types, so confirmation is a
#   single Literal field rather than a boolean. The human picks the word "delete",
#   which reads unambiguously in whatever UI the client draws; a bool would render
#   as a checkbox whose default state is a coin flip across clients.
class DeleteConfirmation(BaseModel):
    """Confirm a destructive operation."""

    choice: Literal["delete", "cancel"] = Field(
        description="Choose 'delete' to perform the deletion, or 'cancel' to abort."
    )


class CapabilityCheckFailed(RuntimeError):
    """The elicitation capability check failed for an unexpected reason.

    Raised instead of returning ``False`` so a defect in our own code cannot be
    mistaken for "this client cannot be prompted". The gate turns it into a
    refusal: on an internal error we decline the destructive operation rather
    than silently accepting the weaker token path.
    """


#: Resolved value meaning "the capability check itself broke" — distinct from
#: :data:`TOKEN_FALLBACK`, which means "this caller legitimately cannot be asked".
CAPABILITY_CHECK_FAILED = "__zscaler_mcp_capability_check_failed__"


def is_capability_check_failure(outcome: Any) -> bool:
    """Whether a resolved value is the "capability check broke" sentinel."""
    return getattr(outcome, "data", outcome) == CAPABILITY_CHECK_FAILED


def elicitation_available(ctx: Any) -> bool:
    """Whether this caller can be asked for confirmation over the protocol.

    False whenever anything is missing — no context, no negotiated capabilities
    (direct in-process calls and unit tests land here), or a client that did not
    advertise the ``elicitation`` capability. Every false answer routes to the
    token fallback, so a missing capability degrades rather than failing the call.

    **A false answer is a real cost, not a neutral default.** The token can be
    redeemed by the agent in the same turn, so falling back means no human
    necessarily approves the delete. Prefer being wrong towards asking.

    **Each branch logs its reason.** Without that, a defect in this function is
    indistinguishable from a client that legitimately cannot be prompted — both
    just quietly take the weaker path. Operators need to tell the two apart,
    because only one of them is a client limitation.
    """
    if ctx is None:
        logger.debug("Elicitation unavailable: no active request context")
        return False
    try:
        # `Context.client_capabilities` is what the SDK's own resolver checks, so
        # reading the same field keeps our fallback decision aligned with the
        # framework's rather than approximating it from the session object.
        capabilities = ctx.client_capabilities
        if capabilities is None:
            logger.debug("Elicitation unavailable: no negotiated client capabilities")
            return False
        if capabilities.elicitation is None:
            logger.info(
                "Client did not advertise the 'elicitation' capability — falling back to "
                "the HMAC confirmation token, which cannot enforce a human decision "
                "(see docs/guides/mcp-protocol.md)."
            )
            return False

        # Reachability needs no separate test, and adding one was a bug. Before
        # 2026-07-28 the prompt is a server-initiated request that has to be pushed
        # over the session's channel; from 2026-07-28 it rides the response itself
        # (``InputRequiredResult``) and needs no channel. The capability check above
        # already separates those cases, because of where capabilities come from:
        # a pre-2026-07-28 client declares them once during `initialize` and the
        # *session* holds them, while a 2026-07-28 client re-sends them on every
        # request in `_meta`. So on sessionless streamable-http there is nothing to
        # hold them and `client_capabilities` is None for exactly the population
        # that could not have been pushed a prompt anyway.
        #
        # An earlier version of this function tested
        # `ctx.connection.has_standalone_channel` here. `Context` has no
        # `.connection` in mcp 2.0.0, so that raised `AttributeError` on every
        # pre-2026-07-28 caller, the broad `except` below swallowed it, and **every
        # legacy client silently lost its human confirmation prompt** — including
        # ones on a session that could have been asked. The unit tests did not catch
        # it because they faked the attribute into existence. Any predicate added
        # here must be exercised against a real `Context`; see
        # `tests/test_protocol_2026_07_28.py::TestLegacyClientConfirmation`.
        return True
    except ValueError as exc:
        # The SDK raises exactly this ("Context is not available outside of a
        # request") when no request context is bound: direct in-process calls and
        # unit tests. A genuine "cannot be prompted" case, so degrade to the token.
        logger.debug(
            "Elicitation unavailable: no bound request context (%s) — using the "
            "HMAC confirmation token",
            exc,
        )
        return False
    except Exception as exc:
        # Anything else is a DEFECT on our side, and the comment above is only
        # honest if this branch acts on it. Returning False here would give the
        # same answer as "this client legitimately cannot elicit" — which is how a
        # previous version of this function shipped a silent downgrade: it read
        # `ctx.connection`, which does not exist in mcp 2.0.0, and the resulting
        # AttributeError was swallowed into the token path for every legacy client.
        # Note the discriminator is the exception TYPE: the expected case above is
        # a ValueError, that historical bug was an AttributeError.
        logger.error(
            "Elicitation capability check FAILED for an unexpected reason (%s: %s). "
            "Refusing the destructive operation rather than downgrading to the token "
            "path — this is a server defect, not a client limitation.",
            type(exc).__name__,
            exc,
        )
        raise CapabilityCheckFailed(str(exc)) from exc


def build_confirmation_request(
    tool_name: str, params: Dict[str, Any], resource_name: Optional[str] = None
) -> Any:
    """The question to put to the human, as an ``Elicit`` marker.

    Returned from a resolver rather than sent from here, so the framework can pick
    the transport the negotiated revision supports (``InputRequiredResult`` on
    2026-07-28, a mid-call request before it).
    """
    from mcp.server.mcpserver import Elicit

    summary = describe_destructive_operation(tool_name, params, resource_name)
    return Elicit(
        f"Confirm destructive operation: {summary}\n"
        f"This cannot be undone. Choose '{_APPROVE_CHOICE}' to proceed.",
        DeleteConfirmation,
    )


def is_token_fallback(outcome: Any) -> bool:
    """Whether a resolved value is the "cannot be prompted" sentinel.

    The framework wraps a resolver's plain return value in an accepted outcome, so
    the sentinel arrives as ``AcceptedElicitation(data=TOKEN_FALLBACK)``. It is
    distinguishable from a real approval because a real one carries a validated
    :class:`DeleteConfirmation`, never a bare string.
    """
    return getattr(outcome, "data", outcome) == TOKEN_FALLBACK


def interpret_confirmation(outcome: Any, tool_name: str, params: Dict[str, Any]) -> Optional[str]:
    """Turn an elicitation outcome into a decision. ``None`` means approved.

    Any non-approval returns caller-facing text, so a declined or cancelled prompt
    reads as a normal "did not happen" result rather than an error. Anything
    unrecognised is treated as a refusal: this function must never answer
    "approved" for an outcome it does not understand.
    """
    summary = describe_destructive_operation(tool_name, params)
    action = getattr(outcome, "action", None)

    if action == "accept":
        # `data` is a validated DeleteConfirmation. Read `choice` off it, but fall
        # back to the raw value so a client that answers with a bare string still
        # gets a correct — never accidentally approving — decision.
        data = getattr(outcome, "data", None)
        chosen = getattr(data, "choice", data)
        if chosen == _APPROVE_CHOICE:
            logger.info("Confirmed via elicitation: %s", tool_name)
            return None
        logger.info("Declined via elicitation (chose %r): %s", chosen, tool_name)
        return f"Cancelled by user. {summary} was NOT performed."

    if action == "decline":
        logger.info("Declined via elicitation: %s", tool_name)
        return f"Declined by user. {summary} was NOT performed."

    if action == "cancel":
        logger.info("Elicitation cancelled: %s", tool_name)
        return f"Confirmation dismissed. {summary} was NOT performed."

    # No recognisable outcome. Fail CLOSED — an unanswered confirmation must never
    # fall through to the mutation.
    logger.warning("Unusable confirmation outcome (%r) for %s", action, tool_name)
    return (
        f"Could not obtain confirmation for {summary}. "
        "The operation was NOT performed. Please retry."
    )


def gate_destructive_operation(
    outcome: Any,
    tool_name: str,
    params: Dict[str, Any],
    confirmation_token: Any = None,
    name_lookup: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[str]:
    """The single confirmation gate for destructive tools.

    Returns ``None`` when the operation may proceed, or the text to hand back to
    the caller when it must not.

    ``outcome`` is the value the framework resolved for the tool's confirmation
    parameter: either a human's answer to the elicited question, or
    :data:`TOKEN_FALLBACK` when the caller could not be prompted at all. The
    asking already happened before this runs, which is why nothing here is async.
    """
    if is_capability_check_failure(outcome):
        # A defect broke the capability check. We do not know whether this caller
        # could have been asked, so we refuse rather than mint a token the agent
        # could redeem unaided. No mutation happens.
        logger.error("Refusing %s: the confirmation capability check failed", tool_name)
        return (
            "DESTRUCTIVE OPERATION REFUSED\n\n"
            f"Operation: {describe_destructive_operation(tool_name, params)}\n\n"
            "The server could not determine whether this client is able to ask a human "
            "for confirmation, so the operation was NOT performed. This is a server-side "
            "fault, not a permissions problem — check the server logs for a "
            "'capability check FAILED' entry and report it.\n\n"
            "Retrying will not help until the fault is fixed."
        )

    if is_token_fallback(outcome):
        return check_confirmation(tool_name, confirmation_token, params, name_lookup)

    return interpret_confirmation(outcome, tool_name, params)
