"""Tests for zscaler_mcp.common.cache_metadata (P4 / SEP-2549 prototype).

Covers:

* env-var-driven opt-in (``ZSCALER_MCP_TOOL_LIST_CACHE``)
* env-var-driven TTL (``ZSCALER_MCP_TOOL_LIST_TTL_MS``) with negative /
  non-numeric handling
* invalidation-grace window after ``bump_tool_inventory_version``
* idempotent ``attach_tool_list_cache_metadata``
* wrapper actually merges ``ttlMs`` / ``cacheScope`` into
  ``ListToolsResult._meta``
* wrapper degrades gracefully when the SDK shape is unexpected
* the ``enable_toolset`` integration bumps the version counter on a
  successful runtime registration
"""

from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from zscaler_mcp.common import cache_metadata
from zscaler_mcp.common.cache_metadata import (
    DEFAULT_TTL_MS,
    INVALIDATION_GRACE_MS,
    _operator_ttl_ms,
    attach_tool_list_cache_metadata,
    build_tool_list_cache_metadata,
    bump_tool_inventory_version,
    is_tool_list_cache_enabled,
    reset_tool_inventory_state_for_tests,
    tool_inventory_version,
)


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset module-level state before every test."""
    reset_tool_inventory_state_for_tests()
    for key in (
        "ZSCALER_MCP_TOOL_LIST_CACHE",
        "ZSCALER_MCP_TOOL_LIST_TTL_MS",
    ):
        os.environ.pop(key, None)
    yield
    reset_tool_inventory_state_for_tests()
    for key in (
        "ZSCALER_MCP_TOOL_LIST_CACHE",
        "ZSCALER_MCP_TOOL_LIST_TTL_MS",
    ):
        os.environ.pop(key, None)


class TestIsToolListCacheEnabled:
    def test_default_is_off(self):
        assert is_tool_list_cache_enabled() is False

    @pytest.mark.parametrize("val", ["true", "True", "TRUE", "1", "yes", "on", "  true  "])
    def test_truthy_values(self, val):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = val
        assert is_tool_list_cache_enabled() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", "off", "", "anything-else"])
    def test_falsy_values(self, val):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = val
        assert is_tool_list_cache_enabled() is False


class TestOperatorTtlMs:
    def test_default_when_unset(self):
        assert _operator_ttl_ms() == DEFAULT_TTL_MS

    def test_explicit_value(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "60000"
        assert _operator_ttl_ms() == 60000

    def test_zero_is_honoured(self):
        # 0 means "do not cache" — the helper returns it as-is; the
        # builder above interprets it.
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "0"
        assert _operator_ttl_ms() == 0

    def test_negative_falls_back_to_default(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "-1"
        assert _operator_ttl_ms() == DEFAULT_TTL_MS

    def test_non_numeric_falls_back_to_default(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "not-a-number"
        assert _operator_ttl_ms() == DEFAULT_TTL_MS


class TestBuildToolListCacheMetadata:
    def test_returns_empty_when_disabled(self):
        # opt-in off ⇒ empty
        assert build_tool_list_cache_metadata() == {}

    def test_returns_empty_when_ttl_zero(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "0"
        assert build_tool_list_cache_metadata() == {}

    def test_returns_ttl_and_scope_when_enabled(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "120000"
        meta = build_tool_list_cache_metadata()
        assert meta == {"ttlMs": 120000, "cacheScope": "global"}

    def test_default_ttl_when_only_opt_in_set(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        meta = build_tool_list_cache_metadata()
        assert meta == {"ttlMs": DEFAULT_TTL_MS, "cacheScope": "global"}

    def test_grace_window_clamps_ttl_after_bump(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "600000"  # 10 min
        bump_tool_inventory_version()
        meta = build_tool_list_cache_metadata()
        # Inside the grace window, ttl is clamped to <= INVALIDATION_GRACE_MS
        assert meta["cacheScope"] == "global"
        assert meta["ttlMs"] <= INVALIDATION_GRACE_MS

    def test_grace_window_clamp_does_not_inflate_below_configured(self):
        """If operator already configured a small TTL, grace window must
        not raise it."""
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "1000"  # 1 s
        bump_tool_inventory_version()
        meta = build_tool_list_cache_metadata()
        assert meta["ttlMs"] <= 1000

    def test_outside_grace_window_returns_full_ttl(self, monkeypatch):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "60000"

        # Simulate "bump happened a long time ago" by patching
        # time.monotonic so the elapsed window is far past
        # INVALIDATION_GRACE_MS.
        bump_tool_inventory_version()
        real_monotonic = cache_metadata.time.monotonic
        bumped_at = cache_metadata._last_mutation_ts

        def far_future():
            return bumped_at + 999.0  # 999 seconds later

        monkeypatch.setattr(cache_metadata.time, "monotonic", far_future)
        try:
            meta = build_tool_list_cache_metadata()
            assert meta == {"ttlMs": 60000, "cacheScope": "global"}
        finally:
            monkeypatch.setattr(cache_metadata.time, "monotonic", real_monotonic)


class TestInventoryVersion:
    def test_starts_at_zero(self):
        assert tool_inventory_version() == 0

    def test_bump_increments(self):
        bump_tool_inventory_version()
        assert tool_inventory_version() == 1
        bump_tool_inventory_version()
        assert tool_inventory_version() == 2

    def test_reset_returns_to_zero(self):
        bump_tool_inventory_version()
        bump_tool_inventory_version()
        reset_tool_inventory_state_for_tests()
        assert tool_inventory_version() == 0


class TestAttachToolListCacheMetadata:
    def _build_fake_server(self):
        """Build a FastMCP-shaped server with a fake registered
        ListToolsRequest handler that returns a fake ServerResult."""
        from mcp import types

        async def original_handler(req):
            list_result = types.ListToolsResult(tools=[])
            return SimpleNamespace(root=list_result)

        lowlevel = SimpleNamespace(
            request_handlers={types.ListToolsRequest: original_handler}
        )
        return SimpleNamespace(_mcp_server=lowlevel), original_handler

    def test_noop_when_disabled(self):
        server, original = self._build_fake_server()
        attach_tool_list_cache_metadata(server)
        # Handler was not replaced.
        from mcp import types

        assert server._mcp_server.request_handlers[types.ListToolsRequest] is original

    def test_attaches_when_enabled(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        server, original = self._build_fake_server()
        attach_tool_list_cache_metadata(server)
        from mcp import types

        wrapper = server._mcp_server.request_handlers[types.ListToolsRequest]
        assert wrapper is not original
        assert getattr(wrapper, "_zscaler_cache_wrapped", False) is True

    def test_idempotent(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        server, _ = self._build_fake_server()
        attach_tool_list_cache_metadata(server)
        from mcp import types

        first = server._mcp_server.request_handlers[types.ListToolsRequest]
        attach_tool_list_cache_metadata(server)
        second = server._mcp_server.request_handlers[types.ListToolsRequest]
        assert first is second

    def test_wrapper_merges_meta(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "120000"
        server, _ = self._build_fake_server()
        attach_tool_list_cache_metadata(server)
        from mcp import types

        wrapper = server._mcp_server.request_handlers[types.ListToolsRequest]
        result = asyncio.run(wrapper(MagicMock()))
        list_result = result.root
        assert list_result.meta is not None
        assert list_result.meta["ttlMs"] == 120000
        assert list_result.meta["cacheScope"] == "global"

    def test_wrapper_preserves_existing_meta(self):
        """The wrapper merges into _meta; pre-existing keys survive."""
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        os.environ["ZSCALER_MCP_TOOL_LIST_TTL_MS"] = "120000"

        from mcp import types

        async def original_with_meta(req):
            list_result = types.ListToolsResult(
                tools=[], _meta={"customField": "preserved"}
            )
            return SimpleNamespace(root=list_result)

        lowlevel = SimpleNamespace(
            request_handlers={types.ListToolsRequest: original_with_meta}
        )
        server = SimpleNamespace(_mcp_server=lowlevel)
        attach_tool_list_cache_metadata(server)

        wrapper = server._mcp_server.request_handlers[types.ListToolsRequest]
        result = asyncio.run(wrapper(MagicMock()))
        list_result = result.root
        assert list_result.meta["customField"] == "preserved"
        assert list_result.meta["ttlMs"] == 120000

    def test_wrapper_skips_when_root_missing(self):
        """If the SDK return shape changes, the wrapper degrades to a
        no-op rather than crashing."""
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        from mcp import types

        unexpected_result = SimpleNamespace(root=None)

        async def original(req):
            return unexpected_result

        lowlevel = SimpleNamespace(
            request_handlers={types.ListToolsRequest: original}
        )
        server = SimpleNamespace(_mcp_server=lowlevel)
        attach_tool_list_cache_metadata(server)

        wrapper = server._mcp_server.request_handlers[types.ListToolsRequest]
        result = asyncio.run(wrapper(MagicMock()))
        assert result is unexpected_result  # unchanged

    def test_noop_when_no_mcp_server_attr(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        server = SimpleNamespace()  # missing _mcp_server
        # Must not raise.
        attach_tool_list_cache_metadata(server)

    def test_noop_when_handler_not_registered(self):
        os.environ["ZSCALER_MCP_TOOL_LIST_CACHE"] = "true"
        server = SimpleNamespace(
            _mcp_server=SimpleNamespace(request_handlers={})
        )
        # Must not raise.
        attach_tool_list_cache_metadata(server)


class TestEnableToolsetIntegration:
    """Verify the integration point in zscaler_enable_toolset bumps the
    inventory version on successful runtime registration.

    Reaches into ``ZscalerMCPServer.zscaler_enable_toolset`` indirectly by
    monkey-patching the registration helpers so we don't need a full
    server boot.
    """

    def test_bump_invoked_on_successful_register(self, monkeypatch):
        from zscaler_mcp import server as server_mod

        # Pre-condition: counter at zero
        reset_tool_inventory_state_for_tests()
        assert tool_inventory_version() == 0

        # Build a minimal stub of ZscalerMCPServer just enough to call
        # zscaler_enable_toolset's body. We don't need a real FastMCP —
        # the registration helpers are stubbed to return a positive
        # count.
        instance = MagicMock(spec=server_mod.ZscalerMCPServer)
        instance.selected_toolsets = {"meta"}
        instance.services = {
            "zia": MagicMock(
                read_tools=[{"name": "zia_list_locations"}],
                write_tools=[],
            )
        }
        instance.enabled_tools = []
        instance.disabled_tools = []
        instance.enable_write_tools = False
        instance.write_tools = []
        instance.server = MagicMock()

        # Map "zia_list_locations" to a toolset id matching what we'll
        # ask to enable.
        with patch(
            "zscaler_mcp.common.toolsets.toolset_for_tool",
            return_value="zia_locations",
        ), patch(
            "zscaler_mcp.common.tool_helpers.register_read_tools",
            return_value=3,
        ), patch(
            "zscaler_mcp.common.tool_helpers.register_write_tools",
            return_value=0,
        ):
            # Call the unbound method against our stub instance.
            result = server_mod.ZscalerMCPServer.zscaler_enable_toolset(
                instance, "zia_locations"
            )

        assert result["status"] == "enabled"
        assert result["newly_registered"] == 3
        # The integration is the only test-visible bumper.
        assert tool_inventory_version() == 1
