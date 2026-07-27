"""Shaping tests for the ZIA (Internet Access) tool family.

Same contract as the other service shaping tests: shapers drop SDK noise, coerce
ids to strings, tolerate camel/snake keys, count relational members, and the
AgentView base forbids uncurated fields. No SDK / no credentials.

Also covers the ZIA-specific helpers (rank/order validation, rule-payload
assembly) and the shared rule/settings view modules.
"""

import pytest

from zscaler_mcp.common.zia_helpers import (
    DEFAULT_RULE_ORDER,
    DEFAULT_RULE_RANK,
    apply_default_order,
    apply_default_rank,
    build_rule_payload,
    merge_advanced,
    validate_order,
    validate_rank,
)

# =============================================================================
# Helpers: rank / order
# =============================================================================


def test_rank_validation_and_default():
    assert validate_rank(0) == 0
    assert validate_rank(7) == 7
    assert apply_default_rank(None) == DEFAULT_RULE_RANK
    assert apply_default_rank(3) == 3
    with pytest.raises(ValueError):
        validate_rank(8)
    with pytest.raises(ValueError):
        validate_rank(-1)


def test_order_validation_and_default():
    assert validate_order(1) == 1
    assert apply_default_order(None) == DEFAULT_RULE_ORDER
    assert apply_default_order(5) == 5
    with pytest.raises(ValueError):
        validate_order(0)


# =============================================================================
# Helpers: payload assembly
# =============================================================================


def test_build_rule_payload_drops_none_and_parses_lists():
    payload = build_rule_payload(
        scalars={"name": "r", "description": None, "enabled": True, "order": 1},
        lists={"locations": '["1","2"]', "groups": None},
        advanced={"dest_addresses": ["1.1.1.1", "2.2.2.2"], "custom_flag": True},
    )
    assert payload["name"] == "r"
    assert "description" not in payload  # None dropped
    assert payload["enabled"] is True
    assert payload["locations"] == ["1", "2"]  # JSON string parsed
    assert "groups" not in payload  # None list dropped
    assert payload["dest_addresses"] == ["1.1.1.1", "2.2.2.2"]  # advanced list parsed
    assert payload["custom_flag"] is True  # advanced scalar passthrough


def test_merge_advanced_is_in_place_and_skips_none():
    base = {"a": 1}
    out = merge_advanced(base, {"b": 2, "c": None})
    assert out is base
    assert base == {"a": 1, "b": 2}


# =============================================================================
# Shared rule views
# =============================================================================


# =============================================================================
# Shared settings view
# =============================================================================


# =============================================================================
# Network objects
# =============================================================================


# =============================================================================
# Traffic
# =============================================================================


# =============================================================================
# Time intervals
# =============================================================================


# =============================================================================
# URL categories
# =============================================================================
