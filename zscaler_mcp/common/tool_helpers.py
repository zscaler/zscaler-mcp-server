"""Helper functions for tool registration."""

import fnmatch
import functools
import time
from typing import Dict, List, Optional, Set

from mcp.types import ToolAnnotations

from zscaler_mcp.common.logging import get_logger

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


def _wrap_with_audit(func, tool_name: str):
    """Wrap a tool function with audit logging."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _log_tool_calls_enabled:
            return func(*args, **kwargs)

        safe_args = _sanitize_args(kwargs)
        audit_logger.info("[TOOL CALL] %s | args: %s", tool_name, safe_args)

        t0 = time.monotonic()
        try:
            result = func(*args, **kwargs)
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


def register_read_tools(
    server,
    tools: List[Dict[str, any]],
    enabled_tools: Optional[Set[str]] = None,
    disabled_tools: Optional[Set[str]] = None,
) -> int:
    """Register read-only tools.

    Read-only tools are always registered regardless of write mode settings.
    These tools perform safe operations that only retrieve information.

    Args:
        server: The MCP server instance
        tools: List of tool definitions with 'func', 'name', 'description'
        enabled_tools: Set of enabled tool names (if None, all tools are enabled)
        disabled_tools: Set of tool name patterns to exclude (supports wildcards via fnmatch)

    Returns:
        Number of tools registered

    Example:
        read_tools = [
            {
                "func": zpa_list_application_segments,
                "name": "zpa_list_application_segments",
                "description": "List ZPA application segments (read-only)"
            }
        ]
        count = register_read_tools(server, read_tools)
    """
    count = 0
    for tool_def in tools:
        tool_name = tool_def["name"]

        # Skip if not in enabled_tools (when enabled_tools is specified)
        if enabled_tools and tool_name not in enabled_tools:
            logger.debug(f"Skipping read tool (not enabled): {tool_name}")
            continue

        if disabled_tools and any(
            fnmatch.fnmatch(tool_name, pattern) for pattern in disabled_tools
        ):
            logger.debug(f"Skipping read tool (excluded by --disabled-tools): {tool_name}")
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

        # Skip if not in enabled_tools (when enabled_tools is specified)
        if enabled_tools and tool_name not in enabled_tools:
            logger.debug(f"Skipping write tool (not in enabled_tools): {tool_name}")
            continue

        if disabled_tools and any(
            fnmatch.fnmatch(tool_name, pattern) for pattern in disabled_tools
        ):
            logger.debug(f"Skipping write tool (excluded by --disabled-tools): {tool_name}")
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
