"""Helper functions for tool registration."""

import fnmatch
import functools
import time
from typing import Dict, List, Optional, Set

from mcp.types import ToolAnnotations

from zscaler_mcp.common.logging import get_logger
from zscaler_mcp.common.sanitize import is_sanitization_enabled, sanitize_value
from zscaler_mcp.common.toolsets import META_TOOLSET_ID, toolset_for_tool

logger = get_logger(__name__)
audit_logger = get_logger("zscaler_mcp.audit")

_SENSITIVE_PARAMS = frozenset({
    "password", "secret", "token", "key", "credential",
    "client_secret", "api_key", "private_key", "confirmation_token",
})

_log_tool_calls_enabled = False


def enable_tool_call_logging():
    """Enable audit logging for all tool invocations."""
    global _log_tool_calls_enabled
    _log_tool_calls_enabled = True
    audit_logger.info("Tool-call audit logging enabled")


def is_tool_call_logging_enabled() -> bool:
    """Return True if per-tool-call audit logging has been enabled."""
    return _log_tool_calls_enabled


def _sanitize_args(kwargs: dict) -> dict:
    """Redact sensitive parameter values for safe logging."""
    sanitized = {}
    for k, v in kwargs.items():
        if k.lower() in _SENSITIVE_PARAMS or any(s in k.lower() for s in ("secret", "password", "token", "key")):
            sanitized[k] = "***REDACTED***"
        elif v is None:
            continue
        else:
            sanitized[k] = v
    return sanitized


def _summarize_result(result) -> str:
    """Produce a compact summary of a tool result for logging."""
    if isinstance(result, list):
        if len(result) == 1 and isinstance(result[0], dict):
            inner = result[0]
            if "error" in inner:
                return f"error: {inner['error'][:120]}"
            if "nodes" in inner and isinstance(inner["nodes"], list):
                return f"{len(inner['nodes'])} nodes"
            if "status" in inner and inner.get("status") == "no_data":
                return "no data"
        return f"{len(result)} items"
    if isinstance(result, dict):
        if "error" in result:
            return f"error: {result['error'][:120]}"
        return f"dict ({len(result)} keys)"
    return str(type(result).__name__)


def _maybe_sanitize(result):
    """Apply output sanitization unless globally disabled.

    Centralised here so every wrapped tool — read or write, audited
    or not — passes through the same defense. Sanitization itself is
    a no-op when the env-var toggle is off (see
    :mod:`zscaler_mcp.common.sanitize`).
    """
    if not is_sanitization_enabled():
        return result
    return sanitize_value(result)


def _wrap_with_audit(func, tool_name: str):
    """Wrap a tool function with output sanitization and (optional) audit logging.

    Sanitization is always applied to the return value (it's a cheap,
    on-by-default defense against prompt-injection payloads embedded
    in admin-editable Zscaler resource fields). Audit logging is
    only emitted when ``--log-tool-calls`` /
    ``ZSCALER_MCP_LOG_TOOL_CALLS=true`` is active.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _log_tool_calls_enabled:
            return _maybe_sanitize(func(*args, **kwargs))

        safe_args = _sanitize_args(kwargs)
        audit_logger.info("[TOOL CALL] %s | args: %s", tool_name, safe_args)

        t0 = time.monotonic()
        try:
            result = func(*args, **kwargs)
            result = _maybe_sanitize(result)
            elapsed_ms = (time.monotonic() - t0) * 1000
            summary = _summarize_result(result)
            audit_logger.info(
                "[TOOL OK]   %s | %dms | %s", tool_name, elapsed_ms, summary
            )
            return result
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000
            audit_logger.error(
                "[TOOL ERR]  %s | %dms | %s: %s",
                tool_name, elapsed_ms, type(exc).__name__, exc,
            )
            raise

    return wrapper


def _is_in_selected_toolset(
    tool_name: str, selected_toolsets: Optional[Set[str]]
) -> bool:
    """Decide whether a tool passes the active toolset filter.

    Rules:
        * ``selected_toolsets is None`` → no filter; always allowed.
        * The ``meta`` toolset is always allowed (its tools are core
          infrastructure: connectivity check, discovery, search).
        * Otherwise the tool's toolset id (resolved via
          :func:`toolset_for_tool`) must be in ``selected_toolsets``.

    A KeyError raised by :func:`toolset_for_tool` is logged at WARNING
    and the tool is dropped — an unmapped tool is a bug, but we'd
    rather hide it than crash the entire server at registration time.
    """
    if selected_toolsets is None:
        return True
    try:
        tsid = toolset_for_tool(tool_name)
    except KeyError as exc:
        logger.warning("Tool %s has no toolset mapping; dropping. %s", tool_name, exc)
        return False
    if tsid == META_TOOLSET_ID:
        return True
    return tsid in selected_toolsets


def register_read_tools(
    server,
    tools: List[Dict[str, any]],
    enabled_tools: Optional[Set[str]] = None,
    disabled_tools: Optional[Set[str]] = None,
    selected_toolsets: Optional[Set[str]] = None,
) -> int:
    """Register read-only tools.

    Read-only tools are always registered regardless of write mode settings.
    These tools perform safe operations that only retrieve information.

    Filter precedence (most restrictive wins):
        1. ``disabled_tools`` (fnmatch patterns) — always excluded.
        2. ``selected_toolsets`` — only tools whose toolset is in this
           set survive (``meta`` toolset is always exempt).
        3. ``enabled_tools`` — explicit name allowlist (additive intent;
           narrows further when both are given).

    Args:
        server: The MCP server instance.
        tools: List of tool definitions with 'func', 'name', 'description'.
        enabled_tools: Set of enabled tool names (if None, all tools are
            allowed by name).
        disabled_tools: Set of tool name patterns to exclude (supports
            wildcards via fnmatch).
        selected_toolsets: Set of toolset ids (e.g. ``{"zia_url_filtering",
            "zpa_app_segments"}``) to include. ``None`` disables toolset
            filtering. The ``meta`` toolset is always exempt.

    Returns:
        Number of tools registered.
    """
    count = 0
    for tool_def in tools:
        tool_name = tool_def["name"]

        if disabled_tools and any(
            fnmatch.fnmatch(tool_name, pattern) for pattern in disabled_tools
        ):
            logger.debug(f"Skipping read tool (excluded by --disabled-tools): {tool_name}")
            continue

        if not _is_in_selected_toolset(tool_name, selected_toolsets):
            logger.debug(f"Skipping read tool (not in selected toolsets): {tool_name}")
            continue

        if enabled_tools and tool_name not in enabled_tools:
            logger.debug(f"Skipping read tool (not in --enabled-tools): {tool_name}")
            continue

        fn = _wrap_with_audit(tool_def["func"], tool_name)
        server.add_tool(
            fn,
            name=tool_name,
            description=tool_def["description"],
            annotations=ToolAnnotations(
                readOnlyHint=True
            ),  # Mark as read-only for AI agent permission frameworks
        )
        logger.debug(f"✅ Registered read-only tool: {tool_name}")
        count += 1

    return count


def register_write_tools(
    server,
    tools: List[Dict[str, any]],
    enabled_tools: Optional[Set[str]] = None,
    enable_write_tools: bool = False,
    write_tools: Optional[Set[str]] = None,
    disabled_tools: Optional[Set[str]] = None,
    selected_toolsets: Optional[Set[str]] = None,
) -> int:
    """Register write tools (only if enable_write_tools is True).

    Write tools are only registered when explicitly enabled via the
    --enable-write-tools flag. When write_tools allowlist is provided,
    only tools matching the allowlist patterns will be registered.
    This provides defense-in-depth security.

    Args:
        server: The MCP server instance
        tools: List of tool definitions with 'func', 'name', 'description'
        enabled_tools: Set of enabled tool names (if None, all tools are enabled)
        enable_write_tools: Enable write operations (default: False)
        write_tools: Explicit allowlist of write tools (supports wildcards like 'zpa_create_*')
        disabled_tools: Set of tool name patterns to exclude (supports wildcards via fnmatch)

    Returns:
        Number of tools registered

    Example:
        write_tools = [
            {
                "func": zpa_create_application_segment,
                "name": "zpa_create_application_segment",
                "description": "Create a new ZPA application segment (write operation)"
            }
        ]
        # Register all write tools
        count = register_write_tools(server, write_tools, enable_write_tools=True)

        # Register only allowlisted write tools
        count = register_write_tools(server, write_tools, enable_write_tools=True,
                                     write_tools={'zpa_create_*', 'zpa_delete_*'})
    """
    if not enable_write_tools:
        logger.info(f"🔒 Write tools disabled - skipping {len(tools)} write tools for safety")
        logger.info("   To enable write operations, use --enable-write-tools flag")
        return 0

    # Allowlist is MANDATORY when write tools are enabled
    if not write_tools or len(write_tools) == 0:
        logger.warning("⚠️  SECURITY: --enable-write-tools flag is set")
        logger.warning("⚠️  However, NO write tools allowlist specified (--write-tools)")
        logger.warning("⚠️  For security, 0 write tools will be registered")
        logger.info(f"🔒 Blocked {len(tools)} write tools (allowlist required)")
        logger.info("   To enable specific write tools, use: --write-tools 'pattern1,pattern2'")
        logger.info("   Example: --write-tools 'zpa_create_*,zia_delete_*'")
        return 0

    # Explicit allowlist is active
    logger.warning(f"⚠️  Write tools enabled with explicit allowlist ({len(write_tools)} patterns)")
    logger.warning(f"⚠️  Allowlist patterns: {', '.join(sorted(write_tools))}")

    count = 0
    skipped = 0

    for tool_def in tools:
        tool_name = tool_def["name"]

        if disabled_tools and any(
            fnmatch.fnmatch(tool_name, pattern) for pattern in disabled_tools
        ):
            logger.debug(f"Skipping write tool (excluded by --disabled-tools): {tool_name}")
            continue

        if not _is_in_selected_toolset(tool_name, selected_toolsets):
            logger.debug(f"Skipping write tool (not in selected toolsets): {tool_name}")
            continue

        if enabled_tools and tool_name not in enabled_tools:
            logger.debug(f"Skipping write tool (not in --enabled-tools): {tool_name}")
            continue

        # Check write_tools allowlist (supports wildcards)
        if write_tools:
            # Check if tool matches any pattern in the allowlist
            matched = any(fnmatch.fnmatch(tool_name, pattern) for pattern in write_tools)

            if not matched:
                logger.debug(f"🔒 Skipping write tool (not in allowlist): {tool_name}")
                skipped += 1
                continue
            else:
                logger.debug(f"✅ Tool matches allowlist: {tool_name}")

        fn = _wrap_with_audit(tool_def["func"], tool_name)
        server.add_tool(
            fn,
            name=tool_name,
            description=tool_def["description"],
            annotations=ToolAnnotations(
                destructiveHint=True
            ),  # Mark as destructive/write operation for AI agent permission frameworks
        )
        logger.debug(f"⚠️  Registered write tool: {tool_name}")
        count += 1

    if write_tools and skipped > 0:
        logger.info(f"🔒 Security: {skipped} write tools blocked by allowlist, {count} allowed")

    return count
