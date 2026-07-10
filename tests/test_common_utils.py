"""Tests for the product-agnostic helpers in common/utils.py."""

from __future__ import annotations

import pytest

from zscaler_mcp.common.utils import (
    get_combined_user_agent,
    get_mcp_user_agent,
    parse_list,
)


def test_parse_list_from_json_string():
    assert parse_list('["a", "b"]') == ["a", "b"]


def test_parse_list_passthrough_list():
    assert parse_list(["a", "b"]) == ["a", "b"]


def test_parse_list_passthrough_non_string():
    assert parse_list(123) == 123


def test_parse_list_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON string"):
        parse_list("[not json")


def test_user_agent_shape():
    ua = get_mcp_user_agent()
    assert ua.startswith("zscaler-mcp/")
    assert ua.count("/") >= 2  # name/version/os-arch


def test_combined_user_agent_with_comment():
    assert get_combined_user_agent("acme") == f"{get_mcp_user_agent()} (acme)"


def test_combined_user_agent_without_comment():
    assert get_combined_user_agent(None) == get_mcp_user_agent()
    assert get_combined_user_agent("   ") == get_mcp_user_agent()
