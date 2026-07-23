"""Shaping tests for the ZIA (Internet Access) tool family.

Same contract as the other service shaping tests: shapers drop SDK noise, coerce
ids to strings, tolerate camel/snake keys, count relational members, and the
AgentView base forbids uncurated fields. No SDK / no credentials.

Also covers the ZIA-specific helpers (rank/order validation, rule-payload
assembly) and the shared rule/settings view modules.
"""

import pytest
from pydantic import ValidationError

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
from zscaler_mcp.tools.zia._rules_common import (
    RuleDetail,
    RuleSummary,
    shape_rule_detail,
    shape_rule_summary,
)
from zscaler_mcp.tools.zia._settings import Settings, to_settings
from zscaler_mcp.tools.zia.gre_ranges import shape_range as shape_gre_range
from zscaler_mcp.tools.zia.gre_tunnels import shape_tunnel as shape_gre_tunnel
from zscaler_mcp.tools.zia.ip_source_groups import (
    SourceGroupSummary,
)
from zscaler_mcp.tools.zia.ip_source_groups import (
    shape_summary as shape_src_summary,
)
from zscaler_mcp.tools.zia.location_management import shape_loc_detail, shape_loc_summary
from zscaler_mcp.tools.zia.network_services import shape_service_summary
from zscaler_mcp.tools.zia.network_services_group import shape_group_summary
from zscaler_mcp.tools.zia.static_ips import shape_summary as shape_static_summary
from zscaler_mcp.tools.zia.time_intervals import shape_summary as shape_ti_summary
from zscaler_mcp.tools.zia.url_categories import (
    UrlCategorySummary,
    shape_lookup,
)
from zscaler_mcp.tools.zia.url_categories import (
    shape_detail as shape_cat_detail,
)
from zscaler_mcp.tools.zia.url_categories import (
    shape_summary as shape_cat_summary,
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


def test_rule_summary_counts_members_and_drops_noise():
    raw = {
        "id": 100,
        "name": "Block social",
        "state": "ENABLED",
        "action": "BLOCK",
        "order": 3,
        "rank": 7,
        "description": "x",
        "locations": [{"id": "1"}, {"id": "2"}],
        "groups": [{"id": "9"}],
        "lastModifiedTime": 1700000000,  # noise
        "accessControl": "READ_WRITE",  # noise
    }
    s = shape_rule_summary(raw).model_dump()
    assert s["id"] == "100"  # coerced to str
    assert s["enabled"] is True  # state -> enabled
    assert s["action"] == "BLOCK"
    assert s["member_counts"]["locations"] == 2
    assert s["member_counts"]["groups"] == 1
    assert "lastModifiedTime" not in s and "accessControl" not in s


def test_rule_summary_collapses_object_action():
    """SSL inspection reports ``action`` as a nested object; the summary must
    collapse it to its ``type`` string instead of failing validation."""
    raw = {
        "id": 184200,
        "name": "Zscaler Recommended Exemptions",
        "order": 1,
        "rank": 7,
        "urlCategories": ["GLOBAL_INT_GBL_SSL_BYPASS"],
        "action": {
            "type": "DO_NOT_DECRYPT",
            "doNotDecryptSubActions": {"bypassOtherPolicies": True},
            "overrideDefaultCertificate": False,
        },
        "state": "ENABLED",
        "predefined": True,
    }
    s = shape_rule_summary(raw).model_dump()
    assert s["id"] == "184200"
    assert s["action"] == "DO_NOT_DECRYPT"
    assert s["enabled"] is True
    assert s["member_counts"]["url_categories"] == 1
    # Detail view collapses the same way.
    d = shape_rule_detail(raw).model_dump()
    assert d["action"] == "DO_NOT_DECRYPT"


def test_rule_detail_surfaces_member_ids():
    raw = {
        "id": "5",
        "name": "r",
        "state": "DISABLED",
        "locations": [{"id": "1"}, {"id": "2"}],
    }
    d = shape_rule_detail(raw)
    assert isinstance(d, RuleDetail)
    dump = d.model_dump()
    assert dump["enabled"] is False
    assert dump["member_ids"]["locations"] == ["1", "2"]


def test_rule_summary_view_forbids_extra_field():
    with pytest.raises(ValidationError):
        RuleSummary(id="1", name="x", bogus=1)


# =============================================================================
# Shared settings view
# =============================================================================


def test_to_settings_wraps_as_dict_payload():
    class _Obj:
        def as_dict(self):
            return {"knob_a": True, "knob_b": 5}

    s = to_settings(_Obj())
    assert isinstance(s, Settings)
    assert s.model_dump()["settings"] == {"knob_a": True, "knob_b": 5}


def test_to_settings_accepts_plain_dict():
    s = to_settings({"x": 1})
    assert s.model_dump()["settings"] == {"x": 1}


# =============================================================================
# Network objects
# =============================================================================


def test_ip_source_group_summary():
    raw = {"id": 9, "name": "src", "ipAddresses": ["192.168.0.0/24"]}
    s = shape_src_summary(raw).model_dump()
    assert s["id"] == "9" and s["ip_address_count"] == 1


def test_source_group_view_forbids_extra():
    with pytest.raises(ValidationError):
        SourceGroupSummary(id="1", name="x", ip_address_count=0, bogus=True)


def test_network_service_and_group_summaries():
    svc = shape_service_summary(
        {"id": 1, "name": "https", "type": "STANDARD", "destTcpPorts": [{"start": 443}]}
    ).model_dump()
    assert svc["id"] == "1"
    grp = shape_group_summary({"id": "2", "name": "web", "services": [{"id": "1"}]}).model_dump()
    assert grp["id"] == "2"


# =============================================================================
# Traffic
# =============================================================================


def test_location_summary_and_detail():
    raw = {"id": 11, "name": "HQ", "country": "US", "tz": "GMT"}
    s = shape_loc_summary(raw).model_dump()
    assert s["id"] == "11" and s["name"] == "HQ"
    d = shape_loc_detail(raw).model_dump()
    assert d["id"] == "11"


def test_static_ip_summary():
    s = shape_static_summary({"id": 3, "ipAddress": "1.2.3.4"}).model_dump()
    assert s["id"] == "3"


def test_gre_tunnel_and_range():
    t = shape_gre_tunnel({"id": 7, "sourceIp": "1.1.1.1"}).model_dump()
    assert t["id"] == "7"
    r = shape_gre_range({"startIpAddress": "1.1.1.1", "endIpAddress": "1.1.1.10"}).model_dump()
    assert "start_ip_address" in r or "startIpAddress" not in r


# =============================================================================
# Time intervals
# =============================================================================


def test_time_interval_summary_camel_and_snake():
    s = shape_ti_summary(
        {"id": 4, "name": "biz", "startTime": 480, "endTime": 1020, "daysOfWeek": ["MON", "TUE"]}
    ).model_dump()
    assert s["id"] == "4"
    assert s["start_time"] == 480 and s["end_time"] == 1020
    assert s["days_of_week"] == ["MON", "TUE"]


# =============================================================================
# URL categories
# =============================================================================


def test_url_category_summary_counts_urls():
    raw = {
        "id": "CUSTOM_01",
        "configuredName": "Blocked",
        "superCategory": "USER_DEFINED",
        "customCategory": True,
        "urls": ["a.com", "b.com", "c.com"],
        "val": 999,  # noise
    }
    s = shape_cat_summary(raw).model_dump()
    assert s["id"] == "CUSTOM_01"
    assert s["custom_category"] is True
    assert s["url_count"] == 3
    assert "val" not in s


def test_url_category_detail_surfaces_lists():
    raw = {
        "id": "FINANCE",
        "configured_name": "Finance",
        "custom_category": False,
        "urls": ["bank.com"],
        "keywords": ["loan"],
        "ip_ranges": ["10.0.0.0/8"],
    }
    d = shape_cat_detail(raw).model_dump()
    assert d["urls"] == ["bank.com"]
    assert d["keywords"] == ["loan"]
    assert d["ip_ranges"] == ["10.0.0.0/8"]
    assert d["url_count"] == 1


def test_url_lookup_entry():
    e = shape_lookup({"url": "google.com", "urlClassifications": ["SEARCH_ENGINES"]}).model_dump()
    assert e["url"] == "google.com"
    assert e["url_classifications"] == ["SEARCH_ENGINES"]


def test_url_category_view_forbids_extra():
    with pytest.raises(ValidationError):
        UrlCategorySummary(id="1", custom_category=False, url_count=0, bogus=1)
