"""W3C Trace Context propagation (MCP SEP-414 prototype).

The MCP ``2026-07-28`` release candidate standardises ``traceparent``,
``tracestate``, and ``baggage`` key names in request ``_meta`` so distributed
traces correlate across MCP clients, gateways, and servers.

This module wires three extraction paths into the audit wrapper, each safe to
land independently of the others. Listed in the priority the wrapper uses:

1. **Explicit bound context** — anything that called
   :func:`bind_trace_context` earlier in the same task wins. Reserved for
   future middleware / framework integrations.
2. **MCP request_ctx.meta (spec-correct)** —
   :func:`extract_trace_context_from_mcp_request_ctx` reads
   ``mcp.server.lowlevel.server.request_ctx.get().meta`` for the standard
   ``traceparent`` / ``tracestate`` / ``baggage`` keys. The MCP SDK sets this
   :class:`contextvars.ContextVar` on the **same task** that calls the tool, so
   it survives the streamable-http session task-spawn boundary that defeats
   ASGI middleware. This is the path that lights up end-to-end today when a
   client sends ``params._meta.traceparent`` in a ``tools/call`` JSON-RPC
   request.
3. **kwargs ``_meta`` shim** — :func:`try_extract_from_tool_kwargs` accepts
   ``_meta`` nested inside the tool's own ``kwargs`` (or inside a
   ``kwargs: str`` JSON string, mirroring the native-elicitation transport
   shim). Reserved for unit tests and synthetic clients.

:class:`TraceContextMiddleware` is provided for completeness on HTTP transports
(stdio has no middleware surface). It correctly extracts headers into the
``ContextVar`` for the request task, but **on the MCP SDK's streamable-http
transport the dispatch handler runs in a sibling task spawned from the session
manager's lifespan-level task group, so the ContextVar does not propagate to
the tool function**. The middleware is kept as best-effort coverage for
future SDK versions that may share request context across that boundary, and
as a defense-in-depth fallback for any transport that does keep the dispatch
on the request task. It costs nothing at runtime and has explicit unit
tests; the spec-correct path above is the one operators should rely on.

The active trace is stored in a :class:`contextvars.ContextVar` for the
duration of the tool call. :func:`get_zscaler_client` forwards the headers to
the Zscaler SDK's ``RequestExecutor._custom_headers`` so downstream OneAPI
calls participate in the same trace.
"""

from __future__ import annotations

import contextvars
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from zscaler_mcp.common.logging import get_logger

logger = get_logger(__name__)

_TRACEPARENT_RE = re.compile(
    r"^00-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})$",
    re.IGNORECASE,
)

_ALL_ZERO_TRACE_ID = "0" * 32
_ALL_ZERO_SPAN_ID = "0" * 16
_MAX_HEADER_VALUE_LEN = 8192

_trace_context_var: contextvars.ContextVar[Optional["TraceContext"]] = contextvars.ContextVar(
    "zscaler_mcp_trace_context",
    default=None,
)


@dataclass(frozen=True)
class TraceContext:
    """Immutable W3C trace context for one MCP tool invocation."""

    traceparent: str
    tracestate: Optional[str] = None
    baggage: Optional[str] = None

    @property
    def trace_id(self) -> str:
        match = _TRACEPARENT_RE.match(self.traceparent)
        if not match:
            return ""
        return match.group("trace_id").lower()


def validate_traceparent(value: str) -> bool:
    """Return True when *value* matches the W3C ``traceparent`` grammar."""
    if not value or not isinstance(value, str):
        return False
    match = _TRACEPARENT_RE.match(value.strip())
    if not match:
        return False
    trace_id = match.group("trace_id").lower()
    span_id = match.group("span_id").lower()
    if trace_id == _ALL_ZERO_TRACE_ID or span_id == _ALL_ZERO_SPAN_ID:
        return False
    return True


def _normalize_optional_header(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > _MAX_HEADER_VALUE_LEN:
        return None
    return text


def build_trace_context(
    traceparent: str,
    *,
    tracestate: Any = None,
    baggage: Any = None,
) -> Optional[TraceContext]:
    """Build a :class:`TraceContext` or return ``None`` when invalid."""
    if not validate_traceparent(traceparent):
        return None
    return TraceContext(
        traceparent=traceparent.strip(),
        tracestate=_normalize_optional_header(tracestate),
        baggage=_normalize_optional_header(baggage),
    )


def extract_trace_context_from_meta(meta: Any) -> Optional[TraceContext]:
    """Extract trace fields from an MCP ``_meta`` dict."""
    if not isinstance(meta, dict):
        return None
    traceparent = meta.get("traceparent")
    if not isinstance(traceparent, str):
        return None
    return build_trace_context(
        traceparent,
        tracestate=meta.get("tracestate"),
        baggage=meta.get("baggage"),
    )


def _header_lookup(headers: Mapping[str, str], name: str) -> Optional[str]:
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value
    return None


def extract_trace_context_from_http_headers(
    headers: Mapping[str, str],
) -> Optional[TraceContext]:
    """Extract trace fields from W3C HTTP request headers."""
    traceparent = _header_lookup(headers, "traceparent")
    if not traceparent:
        return None
    return build_trace_context(
        traceparent,
        tracestate=_header_lookup(headers, "tracestate"),
        baggage=_header_lookup(headers, "baggage"),
    )


def get_current_trace_context() -> Optional[TraceContext]:
    """Return the trace context bound to the current tool call, if any."""
    return _trace_context_var.get()


def bind_trace_context(ctx: Optional[TraceContext]) -> contextvars.Token:
    """Bind *ctx* to the current context. Returns a token for :func:`reset_trace_context`."""
    return _trace_context_var.set(ctx)


def reset_trace_context(token: contextvars.Token) -> None:
    """Restore the trace context from before :func:`bind_trace_context`."""
    _trace_context_var.reset(token)


def try_extract_from_tool_kwargs(kwargs: Mapping[str, Any]) -> Optional[TraceContext]:
    """Prototype shim: read ``_meta`` from tool kwargs or a JSON ``kwargs`` string."""
    direct = kwargs.get("_meta")
    if direct is not None:
        ctx = extract_trace_context_from_meta(direct)
        if ctx:
            return ctx

    raw_kwargs = kwargs.get("kwargs")
    if not isinstance(raw_kwargs, str) or not raw_kwargs.strip():
        return None
    try:
        parsed = json.loads(raw_kwargs)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return extract_trace_context_from_meta(parsed.get("_meta"))


def extract_trace_context_from_mcp_request_ctx() -> Optional[TraceContext]:
    """Read trace context from the active MCP ``request_ctx`` ContextVar.

    The MCP Python SDK exposes a module-level ContextVar at
    ``mcp.server.lowlevel.server.request_ctx`` that holds the active
    :class:`mcp.shared.context.RequestContext`. The SDK sets it just before
    dispatching the JSON-RPC handler on the same task, so it propagates
    correctly through FastMCP's ``anyio.to_thread.run_sync`` into the sync
    tool function. ``RequestContext.meta`` is a ``RequestParams.Meta`` pydantic
    model whose ``model_config = ConfigDict(extra="allow")`` keeps the standard
    W3C keys (``traceparent``, ``tracestate``, ``baggage``) intact through
    validation when a client sends them in ``params._meta``.

    Returns ``None`` when:

    * the MCP SDK is not importable (e.g. doc generation, unit tests that stub
      the module),
    * ``request_ctx`` is unset on the current task (no active MCP request),
    * the active ``RequestContext.meta`` is ``None``, or
    * ``meta`` lacks a valid ``traceparent``.

    This is the spec-correct path under MCP 2026-07-28 SEP-414 and is the
    extraction the audit wrapper relies on for end-to-end propagation today.
    """
    try:
        from mcp.server.lowlevel.server import request_ctx as _mcp_request_ctx  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - SDK missing
        return None

    try:
        ctx = _mcp_request_ctx.get()
    except LookupError:
        return None
    except Exception:  # pragma: no cover - defensive against future SDK shape changes
        return None

    if ctx is None:
        return None

    meta = getattr(ctx, "meta", None)
    if meta is None:
        return None

    if isinstance(meta, dict):
        meta_dict: Dict[str, Any] = meta
    elif hasattr(meta, "model_dump"):
        try:
            meta_dict = meta.model_dump()
        except Exception:  # pragma: no cover - defensive
            return None
    else:
        meta_dict = {
            key: getattr(meta, key)
            for key in ("traceparent", "tracestate", "baggage")
            if hasattr(meta, key)
        }

    return extract_trace_context_from_meta(meta_dict)


def format_audit_trace_suffix() -> str:
    """Compact suffix for audit log lines, e.g. `` | trace=abc123...``."""
    ctx = get_current_trace_context()
    if ctx is None or not ctx.trace_id:
        return ""
    return f" | trace={ctx.trace_id}"


def sdk_trace_headers() -> Dict[str, str]:
    """W3C headers to forward to the Zscaler SDK request executor."""
    ctx = get_current_trace_context()
    if ctx is None:
        return {}
    headers = {"traceparent": ctx.traceparent}
    if ctx.tracestate:
        headers["tracestate"] = ctx.tracestate
    if ctx.baggage:
        headers["baggage"] = ctx.baggage
    return headers


def apply_trace_headers_to_client(client: Any) -> None:
    """Inject the active trace headers into a Zscaler SDK client instance."""
    headers = sdk_trace_headers()
    if not headers:
        return
    try:
        executor = getattr(client, "_request_executor", None)
        if executor is None:
            return
        custom = getattr(executor, "_custom_headers", None)
        if custom is None:
            executor._custom_headers = dict(headers)
        else:
            custom.update(headers)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Failed to apply trace headers to SDK client: %s", exc)


class TraceContextMiddleware:
    """ASGI middleware — bind W3C trace headers for the request lifetime."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        header_map = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        ctx = extract_trace_context_from_http_headers(header_map)
        token = bind_trace_context(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_trace_context(token)


__all__ = [
    "TraceContext",
    "TraceContextMiddleware",
    "apply_trace_headers_to_client",
    "bind_trace_context",
    "build_trace_context",
    "extract_trace_context_from_http_headers",
    "extract_trace_context_from_mcp_request_ctx",
    "extract_trace_context_from_meta",
    "format_audit_trace_suffix",
    "get_current_trace_context",
    "reset_trace_context",
    "sdk_trace_headers",
    "try_extract_from_tool_kwargs",
    "validate_traceparent",
]
