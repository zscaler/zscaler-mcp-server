"""Shaping tests for the ZMS tool families.

ZMS is GraphQL: list queries return a connection ``{nodes, page_info}`` and the
shapers map each node dict to a curated view. These tests exercise the shapers
and the connection helpers directly — no SDK, no credentials.
"""

from zscaler_mcp.tools.zms._common import nodes_of, page_info_of

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


# =============================================================================
# Agent groups / resources / resource groups / policy rules
# =============================================================================


# =============================================================================
# App zones / catalog / nonces / tags
# =============================================================================


# =============================================================================
# Cross-cutting
# =============================================================================
