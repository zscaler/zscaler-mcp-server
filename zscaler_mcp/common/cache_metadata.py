"""Tool-list / resource-read cache metadata (MCP SEP-2549 prototype, P4).

SEP-2549 of the MCP ``2026-07-28`` release candidate adds two fields to
``Result`` (the base class of every JSON-RPC response):

* ``ttlMs`` — milliseconds the client may cache the result before
  revalidation. Mirrors HTTP ``Cache-Control: max-age``.
* ``cacheScope`` — either ``"global"`` (every connecting client sees the
  same value) or ``"user"`` (the value depends on the authenticated
  caller).

For a server registering 280+ tools whose inventory is essentially
static after startup, this is a meaningful round-trip / bandwidth win
for any cache-aware MCP client (Claude Desktop / Cursor / Bedrock
AgentCore Gateway once the spec ships in their SDKs).

The MCP Python SDK already accepts the field on the wire: every
:class:`mcp.types.Result` subclass carries
``model_config = ConfigDict(extra="allow")`` and a top-level
``meta: dict | None = Field(alias="_meta")``. So we can write the
metadata today; emitting it is just a matter of attaching a small
wrapper to the registered ``ListToolsRequest`` handler on the lowlevel
server.

**Off by default** until two preconditions ship:

1. A shipping MCP client (Claude / Cursor / VS Code / Bedrock) actually
   honours ``Result.meta.ttlMs`` and ``Result.meta.cacheScope``.
2. We emit ``notifications/tools/list_changed`` after
   :meth:`ZscalerMCPServer.zscaler_enable_toolset` mutates the inventory.
   Today FastMCP exposes no public hook for that (tracked at
   ``server.py:1395-1399``), so a client that DID honour ``ttlMs`` could
   see a stale view for the cached window after a runtime toolset
   enable. The cooperating mitigation in this module is the
   "invalidation grace" — when the inventory mutates we serve a very
   short ``ttlMs`` for a brief window so caches are forced to refresh.

Operators flip on via:

.. code-block:: bash

   ZSCALER_MCP_TOOL_LIST_CACHE=true \\
   ZSCALER_MCP_TOOL_LIST_TTL_MS=600000 \\
   zscaler-mcp --transport streamable-http

When the spec lands more broadly we may flip the default to ``true``.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

from zscaler_mcp.common.logging import get_logger

logger = get_logger(__name__)

# Default TTL: 5 minutes. Conservative for a tenant whose ``--toolsets``
# / ``--enabled-tools`` / ``--disabled-tools`` selection is fixed but
# whose ``zscaler_enable_toolset`` runtime path can still mutate the
# inventory. Operators with a strictly static inventory can raise this
# to 3_600_000 (1 hour) via ``ZSCALER_MCP_TOOL_LIST_TTL_MS``.
DEFAULT_TTL_MS = 300_000

# When the tool inventory was just mutated by a runtime
# ``zscaler_enable_toolset`` call, serve a tiny TTL for this many
# milliseconds. Lets any spec-aware client refresh promptly even though
# we don't yet emit ``notifications/tools/list_changed``.
INVALIDATION_GRACE_MS = 5_000

# Monotonic counter — bumps on every runtime mutation of the tool
# inventory. Exposed to tests and to future ``notifications/tools/
# list_changed`` plumbing.
_inventory_version: int = 0

# ``time.monotonic()`` timestamp of the most recent mutation, or 0.0
# when the inventory has not mutated since startup. Used to gate the
# invalidation-grace window.
_last_mutation_ts: float = 0.0


def tool_inventory_version() -> int:
    """Return the current monotonic tool-inventory version.

    Bumps each time :func:`bump_tool_inventory_version` is called. Useful
    for observability and for future emission of
    ``notifications/tools/list_changed`` (which needs a version-like
    handle to communicate to clients).
    """
    return _inventory_version


def bump_tool_inventory_version() -> None:
    """Signal that the tool inventory just mutated.

    Called from ``ZscalerMCPServer.zscaler_enable_toolset`` after a
    successful ``register_read_tools`` / ``register_write_tools`` run.
    After this fires, :func:`build_tool_list_cache_metadata` emits a
    short ``ttlMs`` for the next :data:`INVALIDATION_GRACE_MS` window so
    any client that honours ``ttlMs`` refreshes promptly. This is the
    cooperating-cache mitigation for the missing
    ``notifications/tools/list_changed`` emit.
    """
    global _inventory_version, _last_mutation_ts
    _inventory_version += 1
    _last_mutation_ts = time.monotonic()
    logger.debug("tool inventory version bumped to %d", _inventory_version)


def reset_tool_inventory_state_for_tests() -> None:
    """Reset the module-level state. Test-only helper."""
    global _inventory_version, _last_mutation_ts
    _inventory_version = 0
    _last_mutation_ts = 0.0


def is_tool_list_cache_enabled() -> bool:
    """``True`` when ``ZSCALER_MCP_TOOL_LIST_CACHE`` is truthy.

    See module docstring for the two preconditions gating the default
    flip to ``True``.
    """
    raw = os.environ.get("ZSCALER_MCP_TOOL_LIST_CACHE", "false").strip().lower()
    return raw in ("true", "1", "yes", "on")


def _operator_ttl_ms() -> int:
    """Return the operator-configured TTL, or the conservative default."""
    raw = os.environ.get("ZSCALER_MCP_TOOL_LIST_TTL_MS")
    if not raw:
        return DEFAULT_TTL_MS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning(
            "ZSCALER_MCP_TOOL_LIST_TTL_MS=%r is not an integer; using default %d",
            raw,
            DEFAULT_TTL_MS,
        )
        return DEFAULT_TTL_MS
    if value < 0:
        logger.warning(
            "ZSCALER_MCP_TOOL_LIST_TTL_MS=%d is negative; using default %d",
            value,
            DEFAULT_TTL_MS,
        )
        return DEFAULT_TTL_MS
    return value


def build_tool_list_cache_metadata() -> Dict[str, Any]:
    """Build the ``{"ttlMs": ..., "cacheScope": ...}`` dict to attach to
    the next ``tools/list`` response.

    Returns an **empty dict** when:

    * caching is operator-disabled (``ZSCALER_MCP_TOOL_LIST_CACHE``
      unset / false), or
    * the operator-configured TTL is ``0`` (explicit "do not cache").

    Inside the invalidation grace window (right after a runtime toolset
    enable), the returned ``ttlMs`` is clamped down so cache-aware
    clients refresh quickly. ``cacheScope`` is always ``"global"`` —
    the Zscaler inventory is operator-scoped, not per-user.
    """
    if not is_tool_list_cache_enabled():
        return {}

    ttl = _operator_ttl_ms()
    if ttl == 0:
        return {}

    if _last_mutation_ts > 0.0:
        elapsed_ms = (time.monotonic() - _last_mutation_ts) * 1000.0
        if elapsed_ms < INVALIDATION_GRACE_MS:
            # Serve a tiny TTL — just enough that an actively-refreshing
            # client picks up the new inventory on its next poll.
            remaining_ms = max(0, int(INVALIDATION_GRACE_MS - elapsed_ms))
            ttl = min(ttl, remaining_ms)

    return {
        "ttlMs": ttl,
        # "global" is the accurate scope: two clients connecting to the
        # SAME server see the SAME filtered inventory (entitlement +
        # operator flags are server-wide, not per-caller). Switch to
        # "user" only if/when per-caller toolset filtering ships.
        "cacheScope": "global",
    }


def attach_tool_list_cache_metadata(server: Any) -> None:
    """Wrap the registered ``ListToolsRequest`` handler so its response
    carries ``ttlMs`` / ``cacheScope`` in ``_meta``.

    No-op when :func:`is_tool_list_cache_enabled` returns ``False``.
    Idempotent: calling this twice on the same FastMCP server does not
    double-wrap (a marker attribute is set on the wrapper).

    The wrapper attaches at the MCP SDK boundary — it reads the
    ``ServerResult(ListToolsResult(...))`` returned by FastMCP's own
    handler and merges the cache fields into the
    ``ListToolsResult.meta`` dict. No FastMCP internals are duplicated;
    if the SDK changes its return shape we silently degrade to the
    untagged response rather than crash startup.

    The expected ``server`` is a :class:`fastmcp.FastMCP` (or
    :class:`mcp.server.fastmcp.FastMCP`) instance whose ``_mcp_server``
    attribute is the lowlevel ``mcp.server.lowlevel.Server`` that owns
    ``request_handlers``.
    """
    if not is_tool_list_cache_enabled():
        return

    try:
        from mcp import types
    except Exception:  # pragma: no cover - SDK missing
        logger.warning(
            "MCP SDK not importable; tool list cache wiring skipped"
        )
        return

    lowlevel = getattr(server, "_mcp_server", None)
    if lowlevel is None:
        logger.warning(
            "FastMCP server has no _mcp_server attribute; "
            "tool list cache wiring skipped"
        )
        return

    handlers = getattr(lowlevel, "request_handlers", None)
    if handlers is None or types.ListToolsRequest not in handlers:
        logger.warning(
            "ListToolsRequest handler not registered yet; "
            "tool list cache wiring skipped (call _register_tools first)"
        )
        return

    original = handlers[types.ListToolsRequest]

    if getattr(original, "_zscaler_cache_wrapped", False):
        return  # already wrapped — idempotent

    async def cache_metadata_wrapper(req):
        result = await original(req)
        meta = build_tool_list_cache_metadata()
        if not meta:
            return result

        list_result = getattr(result, "root", None)
        if list_result is None or not hasattr(list_result, "tools"):
            # Unexpected SDK shape — return untouched rather than crash.
            return result

        current_meta = dict(list_result.meta) if list_result.meta else {}
        current_meta.update(meta)
        list_result.meta = current_meta
        return result

    cache_metadata_wrapper._zscaler_cache_wrapped = True  # type: ignore[attr-defined]
    handlers[types.ListToolsRequest] = cache_metadata_wrapper
    logger.info(
        "Tool list cache metadata enabled (ttlMs=%d default, scope=global)",
        _operator_ttl_ms(),
    )


__all__ = [
    "DEFAULT_TTL_MS",
    "INVALIDATION_GRACE_MS",
    "attach_tool_list_cache_metadata",
    "build_tool_list_cache_metadata",
    "bump_tool_inventory_version",
    "is_tool_list_cache_enabled",
    "reset_tool_inventory_state_for_tests",
    "tool_inventory_version",
]
