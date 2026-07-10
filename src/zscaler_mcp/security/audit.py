"""Tool-call audit logging + the sanitize/audit execution wrapper.

Ported from v1 (``zscaler_mcp/common/tool_helpers.py`` audit section). Two
concerns live here:

* **Audit logging** — opt-in via ``ZSCALER_MCP_LOG_TOOL_CALLS=true``. Emits a
  ``[TOOL CALL]`` / ``[TOOL OK]`` / ``[TOOL ERR]`` line per invocation on the
  dedicated ``zscaler_mcp.audit`` logger, with sensitive args redacted.
* **The execution wrapper** (:func:`wrap_tool`) — wraps a tool's *return value*
  with output sanitization (always, unless globally disabled) and, when audit
  logging is on, the timing/summary lines. This mirrors v1's
  ``_wrap_with_audit``: sanitize always, log only when enabled.

The wrapper operates on the *shaped* result (the curated Pydantic view objects
or list thereof) before the server encodes it to the wire — so the sanitizer
sees every admin-editable free-form string regardless of the final wire format.
"""

from __future__ import annotations

import functools
import logging
import os
import time
from typing import Any, Callable

from zscaler_mcp.security.sanitize import is_sanitization_enabled, sanitize_value

audit_logger = logging.getLogger("zscaler_mcp.audit")

_SENSITIVE_PARAMS = frozenset(
    {"password", "secret", "token", "key", "credential", "client_secret", "api_key"}
)

_log_tool_calls_enabled = os.environ.get("ZSCALER_MCP_LOG_TOOL_CALLS", "").lower() == "true"


def enable_tool_call_logging() -> None:
    """Turn per-tool-call audit logging on."""
    global _log_tool_calls_enabled
    _log_tool_calls_enabled = True


def disable_tool_call_logging() -> None:
    """Turn per-tool-call audit logging off."""
    global _log_tool_calls_enabled
    _log_tool_calls_enabled = False


def is_tool_call_logging_enabled() -> bool:
    """Return True if per-tool-call audit logging is active."""
    return _log_tool_calls_enabled


def refresh_tool_call_logging() -> None:
    """Re-read ``ZSCALER_MCP_LOG_TOOL_CALLS`` from the environment (reload hook)."""
    desired = os.environ.get("ZSCALER_MCP_LOG_TOOL_CALLS", "").lower() == "true"
    if desired:
        enable_tool_call_logging()
    else:
        disable_tool_call_logging()


def _sanitize_args(kwargs: dict) -> dict:
    """Redact sensitive parameter values for safe logging."""
    sanitized = {}
    for k, v in kwargs.items():
        lk = k.lower()
        if lk in _SENSITIVE_PARAMS or any(s in lk for s in ("secret", "password", "token", "key")):
            sanitized[k] = "***REDACTED***"
        elif v is None:
            continue
        else:
            sanitized[k] = v
    return sanitized


def _summarize_result(result: Any) -> str:
    """Produce a compact summary of a tool result for logging."""
    if isinstance(result, list):
        return f"{len(result)} items"
    if isinstance(result, dict):
        if "error" in result:
            return f"error: {str(result['error'])[:120]}"
        return f"dict ({len(result)} keys)"
    return type(result).__name__


def _maybe_sanitize(result: Any) -> Any:
    """Apply output sanitization unless globally disabled.

    Works on plain JSON-shaped data. Pydantic view objects are converted to
    dicts by the caller (the registry/server) before reaching the wire, so the
    wrapper here defends the dict/list form that actually leaves the process.
    """
    if not is_sanitization_enabled():
        return result
    return sanitize_value(result)


def wrap_tool(func: Callable[..., Any], tool_name: str) -> Callable[..., Any]:
    """Wrap a tool function with output sanitization + (optional) audit logging.

    Sanitization is always applied to the return value (cheap, on-by-default).
    Audit logging is emitted only when ``ZSCALER_MCP_LOG_TOOL_CALLS=true``.
    Mirrors v1's ``_wrap_with_audit``.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not _log_tool_calls_enabled:
            return _maybe_sanitize(func(*args, **kwargs))

        safe_args = _sanitize_args(kwargs)
        audit_logger.info("[TOOL CALL] %s | args: %s", tool_name, safe_args)

        t0 = time.monotonic()
        try:
            result = _maybe_sanitize(func(*args, **kwargs))
            elapsed_ms = (time.monotonic() - t0) * 1000
            audit_logger.info(
                "[TOOL OK]   %s | %dms | %s", tool_name, elapsed_ms, _summarize_result(result)
            )
            return result
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000
            audit_logger.error(
                "[TOOL ERR]  %s | %dms | %s: %s",
                tool_name,
                elapsed_ms,
                type(exc).__name__,
                exc,
            )
            raise

    return wrapper
