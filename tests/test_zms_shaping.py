"""Shaping tests for the ZMS tool families.

ZMS is GraphQL: list queries return a connection ``{nodes, page_info}`` and the
shapers map each node dict to a curated view. These tests exercise the shapers
and the connection helpers directly — no SDK, no credentials.
"""

import pytest

from zscaler_mcp.tools.zms._common import nodes_of, page_info_of
from zscaler_mcp.tools.zms.agent_groups import AgentGroupSummary, _shape_group
from zscaler_mcp.tools.zms.agents import AgentStats, AgentSummary, _shape_agent, _shape_stats
from zscaler_mcp.tools.zms.app_catalog import AppCatalogSummary, _shape_entry
from zscaler_mcp.tools.zms.app_zones import AppZoneSummary, _shape_zone
from zscaler_mcp.tools.zms.nonces import NonceSummary, _shape_nonce
from zscaler_mcp.tools.zms.policy_rules import PolicyRuleSummary, _shape_rule
from zscaler_mcp.tools.zms.resource_groups import ResourceGroupSummary, _shape_group as _shape_rg
from zscaler_mcp.tools.zms.resources import ResourceSummary, _shape_resource
from zscaler_mcp.tools.zms.tags import (
    TagKeySummary,
    TagNamespaceSummary,
    TagValueSummary,
    _shape_key,
    _shape_namespace,
    _shape_value,
)

# =============================================================================
# Connection helpers
# =============================================================================


def test_nodes_of_handles_casing_and_missing():
    assert nodes_of({"nodes": [{"a": 1}]}) == [{"a": 1}]
    assert nodes_of({"Nodes": [{"a": 1}]}) == [{"a": 1}]
    assert nodes_of({}) == []
    assert nodes_of(None) == []
    # non-dict rows are filtered out
    assert nodes_of({"nodes": [{"a": 1}, "junk"]}) == [{"a": 1}]


def test_page_info_of_handles_casing():
    assert page_info_of({"pageInfo": {"totalCount": 5}}) == {"totalCount": 5}
    assert page_info_of({"page_info": {"totalCount": 5}}) == {"totalCount": 5}
    assert page_info_of({}) == {}


# =============================================================================
# Agents
# =============================================================================


def test_agent_summary_picks_first_ip_and_status():
    raw = {
        "eyezId": "ez-1",
        "name": "agent1",
        "connectionStatus": "CONNECTED",
        "version": "2.0",
        "osType": "LINUX",
        "ipAddresses": ["10.0.0.1", "10.0.0.2"],
        "telemetry": {"big": "blob"},
    }
    view = _shape_agent(raw)
    assert isinstance(view, AgentSummary)
    d = view.model_dump()
    assert d["eyez_id"] == "ez-1"
    assert d["connection_status"] == "CONNECTED"
    assert d["ip_address"] == "10.0.0.1"
    assert "telemetry" not in d


def test_agent_stats_keeps_payload():
    view = _shape_stats({"total": 10, "connected": 8})
    assert isinstance(view, AgentStats)
    d = view.model_dump()
    assert d["total"] == 10
    assert d["data"] == {"total": 10, "connected": 8}


# =============================================================================
# Agent groups / resources / resource groups / policy rules
# =============================================================================


def test_agent_group_summary():
    view = _shape_group({"eyezId": "g1", "name": "grp", "agentGroupType": "LINUX", "agentCount": 5})
    assert isinstance(view, AgentGroupSummary)
    d = view.model_dump()
    assert d["eyez_id"] == "g1"
    assert d["agent_group_type"] == "LINUX"
    assert d["agent_count"] == 5


def test_resource_summary_coerces_ips():
    raw = {
        "id": 1,
        "name": "vm1",
        "resourceType": "VIRTUAL_MACHINE",
        "cloudProvider": "AWS",
        "ipAddresses": ["1.1.1.1"],
    }
    view = _shape_resource(raw)
    assert isinstance(view, ResourceSummary)
    d = view.model_dump()
    assert d["id"] == "1"
    assert d["cloud_provider"] == "AWS"
    assert d["ip_addresses"] == ["1.1.1.1"]


def test_resource_group_summary_unmanaged():
    raw = {
        "id": "rg1",
        "name": "g",
        "groupType": "UnmanagedResourceGroup",
        "CIDRs": ["10/8"],
        "FQDNs": ["x.com"],
    }
    view = _shape_rg(raw)
    assert isinstance(view, ResourceGroupSummary)
    d = view.model_dump()
    assert d["cidrs"] == ["10/8"]
    assert d["fqdns"] == ["x.com"]


def test_policy_rule_summary():
    d = _shape_rule(
        {"id": 5, "name": "r", "action": "BLOCK", "priority": 2, "enabled": True}
    ).model_dump()
    assert isinstance(_shape_rule({"id": 5}), PolicyRuleSummary)
    assert d["action"] == "BLOCK"
    assert d["priority"] == 2


# =============================================================================
# App zones / catalog / nonces / tags
# =============================================================================


def test_app_zone_summary():
    d = _shape_zone({"id": "z1", "appZoneName": "Zone A", "resourceCount": 12}).model_dump()
    assert isinstance(_shape_zone({"id": "z1"}), AppZoneSummary)
    assert d["name"] == "Zone A"
    assert d["resource_count"] == 12


def test_app_catalog_keeps_nested_ports():
    raw = {
        "id": "a1",
        "name": "App",
        "category": "Database",
        "ports": [{"port": 5432, "protocol": "TCP"}],
    }
    view = _shape_entry(raw)
    assert isinstance(view, AppCatalogSummary)
    d = view.model_dump()
    assert d["ports"] == [{"port": 5432, "protocol": "TCP"}]


def test_nonce_summary():
    d = _shape_nonce(
        {"eyezId": "n1", "name": "nonce", "status": "ACTIVE", "expiresAt": 1700000000}
    ).model_dump()
    assert isinstance(_shape_nonce({"eyezId": "n1"}), NonceSummary)
    assert d["eyez_id"] == "n1"
    assert d["expires_at"] == "1700000000"


def test_tag_hierarchy_shapers():
    ns = _shape_namespace({"id": "ns1", "name": "env", "origin": "CUSTOM", "keyCount": 3})
    assert isinstance(ns, TagNamespaceSummary)
    assert ns.model_dump()["origin"] == "CUSTOM"

    key = _shape_key({"id": "k1", "keyName": "team", "valueCount": 4})
    assert isinstance(key, TagKeySummary)
    assert key.model_dump()["key_name"] == "team"

    val = _shape_value({"id": "v1", "name": "platform"})
    assert isinstance(val, TagValueSummary)
    assert val.model_dump()["name"] == "platform"


# =============================================================================
# Cross-cutting
# =============================================================================


def test_views_reject_uncurated_fields():
    with pytest.raises(Exception):
        AgentSummary(eyez_id="1", leaked="x")


def test_resource_output_schema_lists_curated_fields_only():
    props = set(ResourceSummary.output_schema()["properties"])
    assert props == {
        "id",
        "name",
        "resource_type",
        "status",
        "cloud_provider",
        "cloud_region",
        "platform_os",
        "ip_addresses",
    }
