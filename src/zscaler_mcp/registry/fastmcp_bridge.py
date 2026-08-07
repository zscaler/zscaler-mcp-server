"""Bridge a :class:`ToolSpec` onto an MCP ``Tool``.

This is the single adapter between v2's self-declared tool records and the MCP
framework (``mcp.server.mcpserver``). It is the one place that knows how to:

* flatten the tool's Pydantic ``input_model`` into a callable signature so the
  advertised ``inputSchema`` is flat (``search``, ``detail``, …) — the shape an
  agent expects — instead of a nested ``{"args": {...}}`` wrapper;
* declare the curated view as the callable's RETURN annotation, from which the
  framework derives the ``outputSchema`` (so the advertised output shape and the
  shaped result can never drift — DESIGN.md §5 Pillar B);
* wrap the tool body with the security layer in the right order:
  write-confirmation (deletes only) → sanitize + audit (every tool).

Every tool — read or write — flows through here, so the security guarantees are
uniform and declared once, not re-implemented per tool (DESIGN.md §6).
"""

from __future__ import annotations

import inspect
import logging
from typing import Annotated, Any, Optional

import pydantic_core
from mcp.server.mcpserver import Context, ElicitationResult, Resolve
from mcp.server.mcpserver.tools.base import Tool
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.common.token_metrics import is_token_reporting_enabled, token_usage_block
from zscaler_mcp.encoding import encode
from zscaler_mcp.registry.registry import REGISTRY
from zscaler_mcp.registry.spec import DELETE, ToolSpec
from zscaler_mcp.security import (
    CAPABILITY_CHECK_FAILED,
    TOKEN_FALLBACK,
    CapabilityCheckFailed,
    DeleteConfirmation,
    build_confirmation_request,
    elicitation_available,
    extract_confirmed_from_kwargs,
    gate_destructive_operation,
    is_tool_call_logging_enabled,
    wrap_tool,
)

# Reuse the dedicated audit logger so token usage shows up on the same channel as
# the [TOOL CALL] / [TOOL OK] lines (filterable independently of app logging).
_audit_logger = logging.getLogger("zscaler_mcp.audit")
logger = logging.getLogger(__name__)

# Sentinel for write tools' confirmation channel. Mirrors v1: the agent passes
# kwargs='{"confirmation_token": "..."}' to confirm a destructive op.
_KWARGS_PARAM = "kwargs"

# Caller-supplied JMESPath expression on list tools (v1 parity).
_QUERY_PARAM = "query"

# The resolver's Context parameter. A resolver may take the Context by declaring
# it, and resolver parameters are never part of the tool's advertised inputSchema.
_CONTEXT_PARAM = "ctx"

# The DELETE tool's resolved confirmation parameter. Filled by the framework from
# the resolver below, never from agent-supplied arguments — which is the whole
# point: there is no slot in the tool call for a model to approve its own delete.
_APPROVAL_PARAM = "approval"


def _return_annotation(spec: ToolSpec) -> Any:
    """The callable's return annotation, from which MCP derives the outputSchema.

    ``Any`` is the normal case, and it means *no schema is advertised*: a tool
    that returns a Zscaler API record does NOT advertise a schema, because the
    attribute set of a resource belongs to the API, not to this server. Declaring
    it here would be a snapshot that silently goes stale the moment engineering
    adds a field — the failure mode behind issue #88 — and the SDK itself
    documents reads the same way (query params are enumerated; the response is
    just ``record.as_dict()``).

    A schema IS advertised for the few tools whose result the server constructs
    itself (``OperationResult`` and friends), since that shape really is ours.
    The MCP spec requires an object-typed outputSchema, and the framework handles
    that for collections natively: a ``list[View]`` annotation is wrapped under a
    ``result`` key, which is exactly the envelope :func:`_to_tool_result` builds.
    Deriving it from the annotation replaces the hand-rolled wrapper schema this
    bridge used to pass to FastMCP, so there is one less place for the advertised
    shape and the emitted shape to disagree.

    DELETE tools always return ``Any``. They are POLYMORPHIC: an unconfirmed call
    returns the confirmation prompt (a plain-text envelope with no structured
    content) and only the confirmed call returns a result. No single schema
    describes both, and a declared schema with no structured content is an error.
    """
    if spec.output_view is None or spec.action == DELETE:
        return Any
    if spec.is_list:
        return list[spec.output_view]  # type: ignore[name-defined]
    return spec.output_view


def _to_tool_result(spec: ToolSpec, value: Any) -> CallToolResult:
    """Package a shaped tool return into an MCP ``CallToolResult``.

    This is the SINGLE wire-format decision point (DESIGN.md §5 Pillar D):

    * the TEXT content block is produced by the encoder (flat list -> CSV,
      object/nested -> JSON, or the tool's explicit override) — token-efficient;
    * the STRUCTURED content block is the JSON-able form of the same value,
      wrapped under ``result`` for list tools to match the advertised
      object-typed outputSchema.

    Both blocks come from the same shaped value, so the human-readable text and
    the machine-readable structured content can never disagree.

    Token accounting is split into two scopes by *who pays for it*:

    * **Server-side `[TOKENS]` audit line — ALWAYS on, no flag.** It measures the
      exact cost of the text the agent receives and logs it on the
      ``zscaler_mcp.audit`` channel. This is operator-facing telemetry; it costs
      nothing in the agent's context window, so there's no reason to hide it.
    * **Agent-facing footer + ``token_usage`` in structured content — opt-in via
      ``ZSCALER_MCP_REPORT_TOKENS``.** These DO consume response tokens the model
      reads, so they stay off by default and only turn on when an operator
      explicitly wants the metric echoed back into the agent's view.

    The measurement is computed once and reused for both scopes.
    """
    text = encode(value, fmt=spec.wire_format)
    structured = pydantic_core.to_jsonable_python(value)

    # Measure once. The server-side log line is free (operator-facing), so it is
    # unconditional; only the agent-facing echo is gated by the opt-in flag.
    row_count = len(value) if isinstance(value, list) else None
    usage = token_usage_block(text, row_count=row_count)
    approx = "" if usage["exact"] else "~"
    # `tokens_per_row` is omitted for empty results (no divide-by-zero), so guard
    # on it independently of `rows` — an empty list still logs "0 rows".
    if "rows" in usage:
        rows_suffix = f" | {usage['rows']} rows"
        if "tokens_per_row" in usage:
            rows_suffix += f" ({usage['tokens_per_row']} tok/row)"
    else:
        rows_suffix = ""
    _audit_logger.info(
        "[TOKENS]    %s | %s%d tokens | %d bytes | %s%s",
        spec.name,
        approx,
        usage["response_tokens"],
        usage["response_bytes"],
        usage["encoding"],
        rows_suffix,
    )

    echo_to_agent = is_token_reporting_enabled()
    if echo_to_agent:
        text = f"{text}\n# token_usage: {approx}{usage['response_tokens']} tokens ({usage['encoding']})"

    if spec.is_list:
        structured = {"result": structured}
    if echo_to_agent and isinstance(structured, dict):
        # structured_content is always a dict for list tools; for single-object
        # tools it's the object's dict — both can carry the metadata key.
        structured = {**structured, "token_usage": usage}

    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structuredContent=structured,
    )


def _tool_annotations(spec: ToolSpec) -> ToolAnnotations:
    """Build the MCP ``ToolAnnotations`` hints for a spec.

    These are behavioural HINTS the client uses to decide how to present a tool
    (e.g. whether to surface a confirmation prompt before running it) — they are
    advisory metadata, never a security control. The authoritative gate stays
    server-side: reads are always safe, and writes require the ``--write-tools``
    allowlist plus (for deletes) HMAC confirmation regardless of what any hint
    says (DESIGN.md §6).

    The values are DERIVED from the spec's single action verb via the domain
    properties on :class:`ToolSpec`, so they can never disagree with the tool's
    actual behaviour:

    * read  -> ``readOnlyHint=True``
    * create -> not read-only, not destructive, not idempotent
    * update -> not read-only, destructive (PUT-replace), idempotent
    * delete -> not read-only, destructive, idempotent

    ``openWorldHint`` is ``False`` for every tool: they all operate against a
    single, closed system (the configured Zscaler tenant), never an open-ended
    external world (contrast a web-search tool). Hint fields that the MCP spec
    treats as meaningful only for writes are left unset (``None``) on read-only
    tools rather than sent as ``False``.
    """
    if spec.read_only:
        return ToolAnnotations(read_only_hint=True, open_world_hint=False)
    return ToolAnnotations(
        read_only_hint=False,
        destructive_hint=spec.destructive,
        idempotent_hint=spec.idempotent,
        open_world_hint=False,
    )


def _build_signature(spec: ToolSpec) -> tuple[list[inspect.Parameter], dict[str, Any]]:
    """Flatten the input model's fields into callable parameters.

    Returns ``(parameters, annotations)``. Each input-model field becomes a
    keyword parameter with the same name, annotation, and default, so FastMCP's
    schema generation produces a flat inputSchema.

    Three channels are added here rather than in the tool modules, so no tool can
    forget them and new tools inherit them for free: list tools get the optional
    JMESPath ``query`` parameter, DELETE tools get the ``kwargs`` parameter
    carrying the HMAC confirmation token, and DELETE tools also get the MCP
    ``Context`` needed to prompt a human. The ``Context`` parameter is declared to
    the framework via ``context_kwarg``, which excludes it from the advertised
    inputSchema — so the agent never sees it and cannot supply it.
    """
    params: list[inspect.Parameter] = []
    annotations: dict[str, Any] = {}

    for field_name, field in spec.input_model.model_fields.items():
        annotations[field_name] = field.annotation
        default = field.default
        # Required fields (no default) must come first / have no default value.
        if field.is_required():
            params.append(
                inspect.Parameter(
                    field_name,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=field.annotation,
                )
            )
        else:
            params.append(
                inspect.Parameter(
                    field_name,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=field.annotation,
                    default=default,
                )
            )

    # Collection-returning tools accept a JMESPath expression so the CALLER can
    # filter and project the rows it asked for. This is the opt-in counterpart to
    # the verbatim-record contract: the server never guesses which attributes
    # matter, but the agent can say exactly what it wants back. See
    # ``ToolSpec.supports_query`` for which tools qualify and why.
    if spec.supports_query:
        query_annotation = Annotated[
            Optional[str],
            Field(
                default=None,
                description=(
                    "Optional JMESPath expression applied to the results after the API "
                    "call, for client-side filtering and projection. Examples: "
                    '"[?enabled==`true`]", "[*].{name: name, id: id}", "length(@)". '
                    "Omit to get the full records. IMPORTANT: field names are the keys "
                    "of the returned records, which are usually snake_case (`custom_category`) "
                    "even where the Zscaler API documents camelCase (`customCategory`) — "
                    "guessing the spelling yields an empty list that looks like a real "
                    "answer. If you have not already seen a record from this tool, call it "
                    "once without `query` and read the keys off the response."
                ),
            ),
        ]
        annotations[_QUERY_PARAM] = query_annotation
        params.append(
            inspect.Parameter(
                _QUERY_PARAM,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=query_annotation,
                default=None,
            )
        )

    # Only DELETE carries the HMAC confirmation channel (v1 parity: confirmation
    # is reserved for destructive operations). create/update execute directly
    # once the operator has enabled them via --write-tools, so they get no
    # `kwargs` confirmation parameter.
    if spec.action == DELETE:
        annotations[_KWARGS_PARAM] = Any
        params.append(
            inspect.Parameter(
                _KWARGS_PARAM,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Any,
                default=None,
            )
        )
        approval_annotation = Annotated[
            ElicitationResult[DeleteConfirmation],
            Resolve(_build_confirmation_resolver(spec)),
        ]
        annotations[_APPROVAL_PARAM] = approval_annotation
        params.append(
            inspect.Parameter(
                _APPROVAL_PARAM,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=approval_annotation,
                default=None,
            )
        )

    return params, annotations


def _resolve_resource_name(spec: ToolSpec, params: dict[str, Any]) -> Optional[str]:
    """Fetch the display name of the resource a DELETE is about to remove.

    A human asked to approve ``DELETE Segment Group — 999999991`` cannot verify
    that is the right group, and two ids differing by one digit look identical at
    a glance — the failure this exists to prevent. The name has to come from the
    API: Zscaler deletes answer ``204 No Content``, so it is unavailable after the
    fact, and taking it from the agent's own narration is exactly the unreliable
    path that motivated this.

    Resolution is by naming convention — ``*_delete_*`` -> ``*_get_*`` — which
    covers 42 of the 50 delete tools. The rest (bulk deletes, the URL-list
    deletes, ZTW's list-only resources) have no single-resource read and simply
    keep the id-only prompt.

    STRICTLY BEST-EFFORT. Every failure — no counterpart tool, a 404, missing
    permissions, a timeout, an unexpected shape — returns ``None`` so the prompt
    degrades to the id. It must never block or auto-approve a delete: the name is
    cosmetic, the gate is not. ``BaseException`` is deliberately not caught, so a
    cancellation still aborts the call rather than being swallowed here.
    """
    get_name = spec.name.replace("_delete_", "_get_", 1)
    if get_name == spec.name:
        return None
    get_spec = REGISTRY.get(get_name)
    if get_spec is None:
        return None
    try:
        fields = get_spec.input_model.model_fields
        args = {k: v for k, v in params.items() if k in fields and v is not None}
        record = get_spec.fn(get_spec.input_model.model_validate(args))
        if not isinstance(record, dict):
            return None
        for key in ("name", "displayName", "display_name"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
    except Exception as exc:  # noqa: BLE001 - cosmetic lookup, never fatal
        logger.debug(
            "Could not resolve a display name for %s via %s (%s: %s) — "
            "the confirmation prompt will show the id only",
            spec.name,
            get_name,
            type(exc).__name__,
            exc,
        )
        return None


def _build_confirmation_resolver(spec: ToolSpec) -> Any:
    """The resolver that obtains a human decision for one DELETE tool.

    Returns either an ``Elicit`` marker (ask the human) or
    :data:`~zscaler_mcp.security.elicitation.TOKEN_FALLBACK` (this caller cannot be
    asked, so fall back to the token exchange). It never decides the operation
    itself — :func:`gate_destructive_operation` interprets the result.

    The signature is SYNTHESIZED from the spec's input model because a resolver
    receives tool arguments *by name*, and the names differ per tool
    (``group_id``, ``rule_id``, …). Those arguments are what let the prompt name
    the resource being deleted instead of asking the human to approve an
    anonymous "delete". Every field is optional here: the resolver runs before the
    input model is validated, so it must tolerate a partial call rather than raise
    a second, confusing error.
    """
    field_names = list(spec.input_model.model_fields)

    def resolve_confirmation(**call_kwargs: Any) -> Any:
        ctx = call_kwargs.pop(_CONTEXT_PARAM, None)
        try:
            can_elicit = elicitation_available(ctx)
        except CapabilityCheckFailed:
            # An internal defect, not a client limitation. Surfaced as its own
            # sentinel so the gate refuses instead of quietly minting a token.
            return CAPABILITY_CHECK_FAILED
        if not can_elicit:
            return TOKEN_FALLBACK
        params = {k: v for k, v in call_kwargs.items() if v is not None}
        return build_confirmation_request(
            spec.name, params, resource_name=_resolve_resource_name(spec, params)
        )

    resolver_params = [
        inspect.Parameter(
            name, inspect.Parameter.KEYWORD_ONLY, annotation=Optional[Any], default=None
        )
        for name in field_names
    ]
    resolver_params.append(
        inspect.Parameter(
            _CONTEXT_PARAM, inspect.Parameter.KEYWORD_ONLY, annotation=Context, default=None
        )
    )
    resolve_confirmation.__name__ = f"confirm_{spec.name}"
    resolve_confirmation.__signature__ = inspect.Signature(resolver_params)
    resolve_confirmation.__annotations__ = {
        **{name: Optional[Any] for name in field_names},
        _CONTEXT_PARAM: Context,
    }
    return resolve_confirmation


def build_function_tool(spec: ToolSpec) -> Tool:
    """Construct the MCP ``Tool`` for a spec, with the full security wrap."""
    secured_fn = wrap_tool(spec.fn, spec.name)
    params, annotations = _build_signature(spec)

    def run_body(model: Any, query: Any) -> CallToolResult:
        result = secured_fn(model)
        # Caller-side filtering/projection runs AFTER the tool returns, so the
        # encoder and the token accounting below both measure what the agent
        # actually receives.
        if spec.supports_query:
            before = len(result) if isinstance(result, list) else None
            result = apply_jmespath(result, query)
            if query and is_tool_call_logging_enabled():
                # `query` is a bridge-owned channel: it is popped before the
                # input model is built and never reaches the tool function, so
                # the wrapper's [TOOL CALL] line cannot see it. Log it here, with
                # the row count on both sides — an expression that silently
                # matches nothing is indistinguishable from an empty tenant, and
                # that ambiguity has already cost a debugging session.
                after = len(result) if isinstance(result, list) else None
                _audit_logger.info(
                    "[QUERY]     %s | %r | %s -> %s rows", spec.name, query, before, after
                )
        return _to_tool_result(spec, result)

    if spec.action == DELETE:

        def impl(**call_kwargs: Any) -> Any:
            # Separate the three bridge-owned channels from the real tool inputs,
            # so none of them reaches the input model (which doesn't declare them).
            confirmation = call_kwargs.pop(_KWARGS_PARAM, None)
            query = call_kwargs.pop(_QUERY_PARAM, None)
            approval = call_kwargs.pop(_APPROVAL_PARAM, None)
            model = spec.input_model.model_validate(call_kwargs)

            # Confirmation happens BEFORE any SDK mutation. Only destructive
            # operations are gated this way (v1 parity): create/update are gated
            # solely by the --write-tools allowlist and execute directly once
            # enabled. By the time this runs the human has already been asked (the
            # resolver did it, via whichever transport the negotiated revision
            # allows); `approval` is either their answer or the sentinel meaning
            # this caller could not be asked and must use the token exchange.
            gate_params = model.model_dump(exclude_none=True)
            message = gate_destructive_operation(
                approval,
                spec.name,
                gate_params,
                extract_confirmed_from_kwargs(confirmation),
                name_lookup=lambda: _resolve_resource_name(spec, gate_params),
            )
            if message is not None:
                # Stop; no mutation happens. Returned as a plain text block — it
                # intentionally does not match the resource outputSchema, same
                # pattern as v1.
                return CallToolResult(content=[TextContent(type="text", text=message)])

            return run_body(model, query)

    else:

        def impl(**call_kwargs: Any) -> Any:  # type: ignore[misc]
            query = call_kwargs.pop(_QUERY_PARAM, None)
            model = spec.input_model.model_validate(call_kwargs)
            return run_body(model, query)

    return_annotation = _return_annotation(spec)
    impl.__name__ = spec.name
    impl.__doc__ = spec.description
    # The return annotation must live on __signature__, not only __annotations__:
    # the framework's schema derivation reads the signature, so a bare
    # __annotations__["return"] is silently ignored and no outputSchema appears.
    impl.__signature__ = inspect.Signature(params, return_annotation=return_annotation)
    impl.__annotations__ = {**annotations, "return": return_annotation}

    return Tool.from_function(
        impl,
        name=spec.name,
        description=spec.description,
        annotations=_tool_annotations(spec),
    )


__all__ = ["build_function_tool"]
