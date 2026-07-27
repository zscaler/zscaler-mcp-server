"""Bridge a :class:`ToolSpec` onto a FastMCP ``FunctionTool``.

This is the single adapter between v2's self-declared tool records and the MCP
framework. It is the one place that knows how to:

* flatten the tool's Pydantic ``input_model`` into a callable signature so the
  advertised ``inputSchema`` is flat (``search``, ``detail``, …) — the shape an
  agent expects — instead of a nested ``{"args": {...}}`` wrapper;
* attach the curated view's ``outputSchema`` (so the advertised output shape and
  the shaped result can never drift — DESIGN.md §5 Pillar B);
* wrap the tool body with the security layer in the right order:
  HMAC write-confirmation (writes only) → sanitize + audit (every tool).

Every tool — read or write — flows through here, so the security guarantees are
uniform and declared once, not re-implemented per tool (DESIGN.md §6).
"""

from __future__ import annotations

import inspect
import logging
from typing import Annotated, Any, Optional

import pydantic_core
from fastmcp.tools import FunctionTool
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent, ToolAnnotations
from pydantic import Field

from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.common.token_metrics import is_token_reporting_enabled, token_usage_block
from zscaler_mcp.encoding import encode
from zscaler_mcp.registry.spec import DELETE, ToolSpec
from zscaler_mcp.security import check_confirmation, extract_confirmed_from_kwargs, wrap_tool

# Reuse the dedicated audit logger so token usage shows up on the same channel as
# the [TOOL CALL] / [TOOL OK] lines (filterable independently of app logging).
_audit_logger = logging.getLogger("zscaler_mcp.audit")

# Sentinel for write tools' confirmation channel. Mirrors v1: the agent passes
# kwargs='{"confirmation_token": "..."}' to confirm a destructive op.
_KWARGS_PARAM = "kwargs"

# Caller-supplied JMESPath expression on list tools (v1 parity).
_QUERY_PARAM = "query"


def _output_schema(spec: ToolSpec) -> dict[str, Any] | None:
    """The advertised outputSchema for the tool, or ``None``.

    ``None`` is the normal case: a tool that returns a Zscaler API record does
    NOT advertise a schema, because the attribute set of a resource belongs to
    the API, not to this server. Declaring it here would be a snapshot that
    silently goes stale the moment engineering adds a field — the failure mode
    behind issue #88 — and the SDK itself documents reads the same way (query
    params are enumerated; the response is just ``record.as_dict()``).

    A schema IS advertised for the few tools whose result the server constructs
    itself (``OperationResult`` and friends), since that shape really is ours.
    The MCP spec requires an object-typed outputSchema, so a list tool's array
    is marked with ``x-fastmcp-wrap-result`` and FastMCP wraps it under a
    ``result`` key — matching what :func:`_to_tool_result` builds either way.
    The human-readable text block is independently produced by the encoder.
    """
    if spec.output_view is None:
        return None
    schema = spec.output_view.output_schema()
    if spec.is_list:
        return {
            "type": "object",
            "properties": {"result": {"type": "array", "items": schema}},
            "required": ["result"],
            "x-fastmcp-wrap-result": True,
        }
    return schema


def _to_tool_result(spec: ToolSpec, value: Any) -> ToolResult:
    """Package a shaped tool return into a FastMCP ``ToolResult``.

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

    return ToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=structured,
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
        return ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    return ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=spec.destructive,
        idempotentHint=spec.idempotent,
        openWorldHint=False,
    )


def _build_signature(spec: ToolSpec) -> tuple[list[inspect.Parameter], dict[str, Any]]:
    """Flatten the input model's fields into callable parameters.

    Returns ``(parameters, annotations)``. Each input-model field becomes a
    keyword parameter with the same name, annotation, and default, so FastMCP's
    schema generation produces a flat inputSchema.

    Two channels are added here rather than in the tool modules, so no tool can
    forget them and new tools inherit them for free: list tools get the optional
    JMESPath ``query`` parameter, and DELETE tools get the ``kwargs`` parameter
    carrying the HMAC confirmation token.
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
                    "call, for client-side filtering and projection. Field names are "
                    "exactly what the Zscaler API returns. Examples: "
                    '"[?enabled==`true`]", "[*].{name: name, id: id}", "length(@)". '
                    "Omit to get the full records."
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

    return params, annotations


def build_function_tool(spec: ToolSpec) -> FunctionTool:
    """Construct the FastMCP ``FunctionTool`` for a spec, with the full security wrap."""
    secured_fn = wrap_tool(spec.fn, spec.name)
    params, annotations = _build_signature(spec)

    def impl(**call_kwargs: Any) -> ToolResult:
        # Separate the two bridge-owned channels from the real tool inputs, so
        # neither reaches the input model (which doesn't declare them).
        confirmation = call_kwargs.pop(_KWARGS_PARAM, None)
        query = call_kwargs.pop(_QUERY_PARAM, None)

        # Build + validate the typed input model from the flat kwargs.
        model = spec.input_model.model_validate(call_kwargs)

        # Destructive tools (DELETE) enforce HMAC confirmation BEFORE any SDK
        # mutation. This mirrors v1 exactly: only destructive operations require
        # the double-confirm; create/update are gated solely by the --write-tools
        # allowlist (read-only by default) and execute directly once enabled.
        if spec.action == DELETE:
            confirmed = extract_confirmed_from_kwargs(confirmation)
            params_for_token = model.model_dump(exclude_none=True)
            message = check_confirmation(spec.name, confirmed, params_for_token)
            if message is not None:
                # Stop and ask the user; no mutation happens. The confirmation
                # prompt is returned as a plain text block (it intentionally does
                # not match the resource outputSchema — same pattern as v1).
                return ToolResult(content=[TextContent(type="text", text=message)])

        result = secured_fn(model)
        # Caller-side filtering/projection runs AFTER the tool returns, so the
        # encoder and the token accounting below both measure what the agent
        # actually receives.
        if spec.supports_query:
            result = apply_jmespath(result, query)
        return _to_tool_result(spec, result)

    impl.__name__ = spec.name
    impl.__doc__ = spec.description
    impl.__signature__ = inspect.Signature(params)
    impl.__annotations__ = {**annotations, "return": Any}

    # DELETE tools are additionally POLYMORPHIC: the first call returns the HMAC
    # confirmation prompt (a plain-text envelope, no structured content), and only
    # the confirmed second call returns a result. A strict outputSchema can never
    # describe both, and the MCP server rejects any result that lacks structured
    # content when an outputSchema is declared ("outputSchema defined but no
    # structured output returned"). So deletes never advertise one, even though
    # their OperationResult is a synthetic shape we do own.
    output_schema = None if spec.action == DELETE else _output_schema(spec)

    return FunctionTool.from_function(
        impl,
        name=spec.name,
        description=spec.description,
        output_schema=output_schema,
        annotations=_tool_annotations(spec),
    )


__all__ = ["build_function_tool"]
