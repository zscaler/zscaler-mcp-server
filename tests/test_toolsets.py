"""Tests for the toolset infrastructure.

Coverage:

* :class:`ToolsetCatalog` registration, lookup, and ``resolve()`` behaviour.
* The ``"default"`` and ``"all"`` keyword expansions.
* The "meta" toolset is always force-selected.
* :func:`toolset_for_tool` returns a known id for every registered tool.
* :func:`tool_helpers._is_in_selected_toolset` precedence behaviour.
* :class:`ZscalerMCPServer` integration:
    - default selection (no ``--toolsets``) preserves today's behaviour.
    - narrow selection drops out-of-scope tools at registration time.
    - per-toolset instructions are composed into ``FastMCP.instructions``
      and de-duplicated when two toolsets share the same snippet.
    - ``zscaler_list_toolsets`` / ``zscaler_get_toolset_tools`` /
      ``zscaler_enable_toolset`` behave as documented.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from zscaler_mcp.common.toolsets import (
    META_TOOLSET_ID,
    TOOLSETS,
    ToolsetCatalog,
    ToolsetMetadata,
    resolve_toolset_selection,
    toolset_for_tool,
)
from zscaler_mcp.common.tool_helpers import _is_in_selected_toolset


# ----------------------------------------------------------------------------
# Catalog primitives
# ----------------------------------------------------------------------------


class TestToolsetCatalog:
    def test_register_and_lookup(self):
        cat = ToolsetCatalog()
        ts = cat.register(ToolsetMetadata(id="x", service="x", description="X"))
        assert cat.get("x") is ts
        assert cat.has("x")
        assert cat.all_ids() == ["x"]

    def test_register_duplicate_raises(self):
        cat = ToolsetCatalog()
        cat.register(ToolsetMetadata(id="x", service="x", description="X"))
        with pytest.raises(ValueError, match="Duplicate toolset id"):
            cat.register(ToolsetMetadata(id="x", service="x", description="X"))

    def test_default_ids_filters_correctly(self):
        cat = ToolsetCatalog.from_iter([
            ToolsetMetadata(id="a", service="x", description="", default=True),
            ToolsetMetadata(id="b", service="x", description="", default=False),
            ToolsetMetadata(id="c", service="x", description="", default=True),
        ])
        assert cat.default_ids() == ["a", "c"]

    def test_for_service_groups_correctly(self):
        cat = ToolsetCatalog.from_iter([
            ToolsetMetadata(id="zia_a", service="zia", description=""),
            ToolsetMetadata(id="zpa_b", service="zpa", description=""),
            ToolsetMetadata(id="zia_c", service="zia", description=""),
        ])
        assert [t.id for t in cat.for_service("zia")] == ["zia_a", "zia_c"]
        assert [t.id for t in cat.for_service("zpa")] == ["zpa_b"]
        assert cat.for_service("missing") == []


# ----------------------------------------------------------------------------
# Selection resolution (default / all keywords, unknowns, meta force-add)
# ----------------------------------------------------------------------------


class TestResolveSelection:
    def _cat(self) -> ToolsetCatalog:
        return ToolsetCatalog.from_iter([
            ToolsetMetadata(id=META_TOOLSET_ID, service="meta", description="", default=True),
            ToolsetMetadata(id="a", service="zia", description="", default=True),
            ToolsetMetadata(id="b", service="zia", description="", default=False),
            ToolsetMetadata(id="c", service="zpa", description="", default=True),
        ])

    def test_none_expands_to_default(self):
        cat = self._cat()
        selected, unknown = cat.resolve(None)
        # Defaults: meta, a, c
        assert selected == {"meta", "a", "c"}
        assert unknown == []

    def test_empty_input_returns_empty(self):
        cat = self._cat()
        selected, unknown = cat.resolve([])
        assert selected == set()
        assert unknown == []

    def test_all_keyword_returns_every_id(self):
        cat = self._cat()
        selected, unknown = cat.resolve(["all"])
        assert selected == {"meta", "a", "b", "c"}
        assert unknown == []

    def test_default_keyword_expands(self):
        cat = self._cat()
        selected, unknown = cat.resolve(["default", "b"])
        # default => a + c, plus explicit b, plus meta force-add
        assert selected == {"meta", "a", "b", "c"}
        assert unknown == []

    def test_unknown_id_reported_separately(self):
        cat = self._cat()
        selected, unknown = cat.resolve(["a", "nope"])
        # a + meta force-add, "nope" surfaces as unknown
        assert selected == {"meta", "a"}
        assert unknown == ["nope"]

    def test_whitespace_ignored(self):
        cat = self._cat()
        selected, _ = cat.resolve(["  a  ", "", " "])
        assert selected == {"meta", "a"}

    def test_meta_always_force_added(self):
        cat = self._cat()
        selected, _ = cat.resolve(["b"])
        assert META_TOOLSET_ID in selected

    def test_resolve_helper_uses_canonical_catalog(self):
        # Smoke check the convenience function
        selected, _ = resolve_toolset_selection(["meta"])
        assert META_TOOLSET_ID in selected


# ----------------------------------------------------------------------------
# Tool-name → toolset mapping
# ----------------------------------------------------------------------------


class TestToolsetForTool:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            # explicit overrides
            ("zscaler_check_connectivity", META_TOOLSET_ID),
            ("zscaler_list_toolsets", META_TOOLSET_ID),
            ("zia_activate_configuration", "zia_admin"),
            ("zia_url_lookup", "zia_url_categories"),
            ("zia_geo_search", "zia_locations"),
            ("zia_list_devices", "zia_users"),
            ("zia_list_shadow_it_apps", "zia_shadow_it"),
            ("zia_list_cloud_app_policy", "zia_cloud_app_control"),
            # prefix rules
            ("zia_create_cloud_app_control_rule", "zia_cloud_app_control"),
            ("zia_create_cloud_firewall_dns_rule", "zia_cloud_firewall"),
            ("zia_list_cloud_firewall_ips_rules", "zia_cloud_firewall"),
            ("zia_create_cloud_firewall_rule", "zia_cloud_firewall"),
            ("zia_create_file_type_control_rule", "zia_file_type_control"),
            ("zia_create_ssl_inspection_rule", "zia_ssl_inspection"),
            ("zia_create_web_dlp_rule", "zia_dlp"),
            ("zia_create_sandbox_rule", "zia_sandbox"),
            ("zia_create_url_filtering_rule", "zia_url_filtering"),
            ("zia_create_url_category", "zia_url_categories"),
            ("zia_add_urls_to_category", "zia_url_categories"),
            ("zia_create_location", "zia_locations"),
            ("zia_create_gre_tunnel", "zia_locations"),
            ("zia_create_vpn_credential", "zia_locations"),
            ("zia_create_static_ip", "zia_locations"),
            ("zia_create_network_service", "zia_cloud_firewall"),
            ("zia_create_ip_destination_group", "zia_cloud_firewall"),
            # ZPA prefix rules
            ("zpa_create_access_policy_rule", "zpa_policy"),
            ("zpa_create_app_protection_rule", "zpa_policy"),
            ("zpa_create_app_connector_group", "zpa_connectors"),
            ("zpa_create_service_edge_group", "zpa_connectors"),
            ("zpa_create_application_segment", "zpa_app_segments"),
            ("zpa_create_segment_group", "zpa_app_segments"),
            ("zpa_create_server_group", "zpa_app_segments"),
            # bare-service fallbacks
            ("zcc_list_devices", "zcc"),
            ("zdx_list_devices", "zdx"),
            ("zid_list_users", "zid"),
            ("zeasm_list_findings", "zeasm"),
            ("zins_get_threat_class", "zins"),
            ("zms_list_resources", "zms"),
            ("ztw_list_admins", "ztw"),
        ],
    )
    def test_known_name_maps_to_expected_toolset(self, name, expected):
        assert toolset_for_tool(name) == expected
        # And every returned id must be a registered toolset.
        assert TOOLSETS.has(expected), f"Tool {name} maps to unregistered toolset {expected}"

    def test_unmapped_name_raises(self):
        with pytest.raises(KeyError, match="No toolset mapping"):
            toolset_for_tool("unrelated_tool_name")

    def test_every_registered_tool_resolves(self):
        """Every tool name registered in services.py must resolve cleanly.

        This is the same check we run interactively after touching
        toolsets.py — wiring it as a test means breaking the mapping
        becomes a CI failure, not a runtime surprise.
        """
        # Set dummy creds so the server can build without API calls.
        os.environ.setdefault("ZSCALER_CLIENT_ID", "dummy")
        os.environ.setdefault("ZSCALER_CLIENT_SECRET", "dummy")
        os.environ.setdefault("ZSCALER_CUSTOMER_ID", "dummy")
        os.environ.setdefault("ZSCALER_VANITY_DOMAIN", "dummy")

        from zscaler_mcp import services as svc_mod

        unmapped = []
        for _, cls in svc_mod.get_available_services().items():
            inst = cls(None)
            for tool_def in list(inst.read_tools) + list(inst.write_tools):
                try:
                    toolset_for_tool(tool_def["name"])
                except KeyError:
                    unmapped.append(tool_def["name"])
        assert unmapped == [], (
            f"{len(unmapped)} tool(s) have no toolset mapping: {unmapped[:10]}"
            f"{'...' if len(unmapped) > 10 else ''}"
        )


# ----------------------------------------------------------------------------
# tool_helpers — toolset filter precedence
# ----------------------------------------------------------------------------


class TestToolsetFilter:
    def test_none_means_no_filter(self):
        assert _is_in_selected_toolset("zia_list_url_filtering_rules", None) is True

    def test_meta_is_always_allowed(self):
        # Even with an empty selection, meta tools survive.
        assert _is_in_selected_toolset("zscaler_check_connectivity", set()) is True
        assert _is_in_selected_toolset("zscaler_list_toolsets", {"zia_dlp"}) is True

    def test_in_selection_passes(self):
        assert _is_in_selected_toolset(
            "zia_list_url_filtering_rules",
            {"zia_url_filtering"},
        ) is True

    def test_out_of_selection_filtered(self):
        assert _is_in_selected_toolset(
            "zia_list_url_filtering_rules",
            {"zpa_app_segments"},
        ) is False

    def test_unmapped_tool_is_dropped(self):
        # Unmapped tool names are warned + dropped, not raised.
        assert _is_in_selected_toolset("totally_unknown_tool", {"meta"}) is False


# ----------------------------------------------------------------------------
# Server integration tests
# ----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _dummy_creds(monkeypatch):
    """Provide dummy OneAPI creds so ZscalerMCPServer instantiation works.

    Also disables the entitlement filter so these toolset-only tests don't
    incidentally trigger a network call to ZIdentity. The filter has its
    own dedicated tests in tests/test_entitlements.py.
    """
    monkeypatch.setenv("ZSCALER_CLIENT_ID", "dummy")
    monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "dummy")
    monkeypatch.setenv("ZSCALER_CUSTOMER_ID", "dummy")
    monkeypatch.setenv("ZSCALER_VANITY_DOMAIN", "dummy")
    monkeypatch.setenv("ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER", "true")


class TestServerToolsetIntegration:
    def test_default_selection_loads_every_toolset(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer()
        # No --toolsets passed → every toolset whose service is enabled
        # (the autouse fixture above leaves all 9 services enabled).
        assert len(s.selected_toolsets) >= 25
        assert META_TOOLSET_ID in s.selected_toolsets

    def test_narrow_selection_only_loads_requested(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer(toolsets={"zia_url_filtering", "zpa_app_segments"})
        assert s.selected_toolsets == {
            "meta",
            "zia_url_filtering",
            "zpa_app_segments",
        }

    def test_default_keyword_expands(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer(toolsets={"default"})
        # Default-on subset is meaningfully smaller than "all"
        all_ids = TOOLSETS.all_ids()
        assert len(s.selected_toolsets) < len(all_ids)
        # Core toolsets are present
        for must_have in ("meta", "zia_url_filtering", "zpa_app_segments", "zdx", "zcc"):
            assert must_have in s.selected_toolsets

    def test_all_keyword_loads_every_toolset(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer(toolsets={"all"})
        assert s.selected_toolsets == set(TOOLSETS.all_ids())

    def test_unknown_id_logs_warning(self, caplog):
        from zscaler_mcp.server import ZscalerMCPServer

        with caplog.at_level("WARNING"):
            s = ZscalerMCPServer(toolsets={"zia_url_filtering", "this_does_not_exist"})
        # The known one survives; the unknown one drops out
        assert "zia_url_filtering" in s.selected_toolsets
        assert "this_does_not_exist" not in s.selected_toolsets
        assert any("this_does_not_exist" in r.message for r in caplog.records)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_instructions_are_composed_and_deduped(self, _mock_client, mock_fastmcp):
        """When two toolsets share the same instruction snippet (the ZIA
        rule-family snippet is bound to several toolsets), the composed
        ``instructions`` must include that text exactly once."""
        from zscaler_mcp.server import ZscalerMCPServer

        ZscalerMCPServer(
            toolsets={
                "zia_url_filtering",
                "zia_ssl_inspection",
                "zia_dlp",
                "zia_file_type_control",
                "zia_sandbox",
            },
        )
        instructions = mock_fastmcp.call_args.kwargs["instructions"]
        snippet = "Every ZIA rule resource enforces a 1-based"
        # Asserted once because the snippet is shared across all 5 above
        # toolsets — the dedupe in _compose_server_instructions must
        # collapse it into a single occurrence.
        assert instructions.count(snippet) == 1

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_instructions_omit_inactive_toolsets(self, _client, mock_fastmcp):
        from zscaler_mcp.server import ZscalerMCPServer

        ZscalerMCPServer(toolsets={"zia_url_filtering"})
        instructions = mock_fastmcp.call_args.kwargs["instructions"]
        # ZPA umbrella snippet is bound to zpa_app_segments — should NOT
        # appear when only zia_url_filtering is selected.
        assert "Application onboarding dependency chain" not in instructions
        # And the URL-categories snippet should NOT appear either.
        assert "predefined categories cannot be deleted" not in instructions

    def test_zscaler_list_toolsets_returns_full_catalog(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer(toolsets={"zia_url_filtering"})
        rows = s.zscaler_list_toolsets()
        ids = [r["id"] for r in rows]
        # Every registered toolset is represented
        assert set(ids) == set(TOOLSETS.all_ids())
        # currently_enabled accurately reflects selection
        for r in rows:
            if r["id"] == "zia_url_filtering" or r["id"] == META_TOOLSET_ID:
                assert r["currently_enabled"] is True
            elif r["id"] in ("zia_dlp", "zpa_app_segments"):
                assert r["currently_enabled"] is False
        # tool_count is non-zero for at least one well-known toolset
        url_filtering = next(r for r in rows if r["id"] == "zia_url_filtering")
        assert url_filtering["tool_count"] >= 5

    def test_zscaler_get_toolset_tools_returns_member_tools(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer()
        tools = s.zscaler_get_toolset_tools("zia_url_filtering")
        names = {t["name"] for t in tools}
        # All 5 url-filtering CRUD tools should be there
        assert {
            "zia_list_url_filtering_rules",
            "zia_get_url_filtering_rule",
            "zia_create_url_filtering_rule",
            "zia_update_url_filtering_rule",
            "zia_delete_url_filtering_rule",
        } <= names

    def test_zscaler_get_toolset_tools_unknown_returns_error(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer()
        result = s.zscaler_get_toolset_tools("not_a_real_toolset")
        assert isinstance(result, list) and len(result) == 1
        assert "error" in result[0]

    def test_zscaler_enable_toolset_registers_at_runtime(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer(toolsets={"zia_url_filtering"})
        assert "zia_dlp" not in s.selected_toolsets

        result = s.zscaler_enable_toolset("zia_dlp")
        assert result["status"] == "enabled"
        assert result["newly_registered"] >= 1
        assert "zia_dlp" in s.selected_toolsets

        # Enabling the same toolset twice is a no-op
        result2 = s.zscaler_enable_toolset("zia_dlp")
        assert result2["status"] == "already_enabled"
        assert result2["newly_registered"] == 0

    def test_zscaler_enable_toolset_unknown_returns_error(self):
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer()
        result = s.zscaler_enable_toolset("not_a_real_toolset")
        assert result["status"] == "error"
        assert "Unknown toolset id" in result["error"]


# ----------------------------------------------------------------------------
# Entitlement-aware meta-tool behaviour
# ----------------------------------------------------------------------------
#
# When the OneAPI entitlement filter has trimmed the active toolsets, the
# meta-tools (get_available_services / list_toolsets / get_toolset_tools /
# enable_toolset) must give the agent ONE consistent answer: "this is
# unavailable, do not retry". The screenshots that motivated these fixes
# showed the agent looping through multiple discovery paths trying to
# load a tool whose service was entitlement-stripped — every one of those
# paths must now return an authoritative "no".


class TestEntitlementAwareMetaTools:
    """Behaviour after the entitlement filter has trimmed selected_toolsets."""

    def _stripped_zpa_server(self):
        """Return a server instance simulating ZPA-stripped entitlements."""
        from zscaler_mcp.server import ZscalerMCPServer

        s = ZscalerMCPServer()
        # Simulate the post-filter state: token entitled only to ZIA, ZPA
        # stripped. We mutate the server directly because the real filter
        # is autouse-disabled in tests.
        s.entitlement_filter_state = "applied"
        s.entitled_services = ["zia"]
        s.selected_toolsets = {
            tsid for tsid in s.selected_toolsets
            if not tsid.startswith("zpa_")
        }
        return s

    def test_get_toolset_tools_marks_entitlement_stripped_as_unavailable(self):
        s = self._stripped_zpa_server()
        # zpa_create_segment_group lives in the zpa_app_segments toolset.
        results = s.zscaler_get_toolset_tools(
            "zpa_app_segments", name_contains="create_segment_group"
        )
        assert results, "get_toolset_tools must surface the tool, not return empty"
        hits = [r for r in results if r.get("name") == "zpa_create_segment_group"]
        assert len(hits) == 1
        hit = hits[0]
        assert hit["available"] is False
        assert "not entitled" in hit["unavailable_reason"].lower()

    def test_get_toolset_tools_keeps_entitled_tools_available(self):
        s = self._stripped_zpa_server()
        results = s.zscaler_get_toolset_tools(
            "zia_url_filtering", name_contains="list_url_filtering_rules"
        )
        assert results
        hit = next(r for r in results if r.get("name") == "zia_list_url_filtering_rules")
        assert hit["available"] is True
        assert "unavailable_reason" not in hit

    def test_get_available_services_reports_entitlement_truth(self):
        s = self._stripped_zpa_server()
        info = s.get_available_services()
        # ZIA is callable, ZPA is reported as unavailable, not silently
        # listed with a non-zero count.
        assert "zia" in info["enabled_services"]
        assert info["enabled_services"]["zia"]["tool_count"] > 0
        assert "zpa" not in info["enabled_services"]
        assert "unavailable_services" in info
        assert "zpa" in info["unavailable_services"]
        assert "note" in info
        assert "not entitled" in info["note"].lower()

    def test_list_toolsets_marks_entitlement_stripped_as_unenableable(self):
        s = self._stripped_zpa_server()
        rows = s.zscaler_list_toolsets()
        zpa_rows = [r for r in rows if r["service"] == "zpa"]
        assert zpa_rows, "ZPA toolsets must still be listed in the catalog"
        for row in zpa_rows:
            assert row["can_enable"] is False
            assert "unavailable_reason" in row
        # ZIA toolsets remain enableable
        zia_rows = [r for r in rows if r["service"] == "zia"]
        assert all(r["can_enable"] is True for r in zia_rows)

    def test_enable_toolset_refuses_entitlement_stripped(self):
        s = self._stripped_zpa_server()
        result = s.zscaler_enable_toolset("zpa_app_segments")
        assert result["status"] == "not_entitled"
        assert "not entitled" in result["error"].lower()
        assert "zpa_app_segments" not in s.selected_toolsets

    def test_enable_toolset_allows_entitled_service(self):
        s = self._stripped_zpa_server()
        # Make sure zia_dlp is currently disabled but entitled
        s.selected_toolsets.discard("zia_dlp")
        result = s.zscaler_enable_toolset("zia_dlp")
        assert result["status"] == "enabled"
        assert "zia_dlp" in s.selected_toolsets
