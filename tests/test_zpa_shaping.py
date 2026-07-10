"""Shaping tests for the ZPA application-segment, lookup, and LSS tool families
added in the v2 port.

Same contract as the segment-groups reference test: shapers drop SDK noise,
coerce ids to strings, tolerate camel/snake keys, and count relational members.
No SDK / no credentials.
"""

import pytest
from pydantic import ValidationError

from zscaler_mcp.tools.zpa.app_segments import (
    AppSegmentSummary,
    shape_detail as seg_detail,
    shape_summary as seg_summary,
)
from zscaler_mcp.tools.zpa.app_segments_ba import (
    shape_detail as ba_detail,
    shape_summary as ba_summary,
)
from zscaler_mcp.tools.zpa.app_segments_pra import (
    shape_detail as pra_detail,
    shape_summary as pra_summary,
)
from zscaler_mcp.tools.zpa._refs import RefItem, shape_ref
from zscaler_mcp.tools.zpa.get_segments_by_type import (
    _shape_segment_by_type as shape_segment_by_type,
)
from zscaler_mcp.tools.zpa.lss import (
    Catalog,
    shape_detail as lss_detail,
    shape_summary as lss_summary,
)


# =============================================================================
# Standard application segments
# =============================================================================


def test_app_segment_summary_counts_and_coerces_id():
    raw = {
        "id": 123456,
        "name": "Prod App",
        "enabled": True,
        "domainNames": ["a.example.com", "b.example.com"],
        "segmentGroupId": 99,
        "serverGroups": [{"id": "1"}, {"id": "2"}],
        "creationTime": "1700000000",  # noise
    }
    d = seg_summary(raw).model_dump()
    assert d["id"] == "123456"
    assert d["domain_name_count"] == 2
    assert d["server_group_count"] == 2
    assert d["segment_group_id"] == "99"
    assert "creationTime" not in d


def test_app_segment_detail_surfaces_ports_and_toggles():
    raw = {
        "id": "1",
        "name": "x",
        "enabled": False,
        "domain_names": ["a"],
        "server_group_ids": ["7"],
        "tcp_port_ranges": ["443", "443"],
        "bypass_type": "NEVER",
        "inspect_traffic_with_zia": True,
    }
    d = seg_detail(raw).model_dump()
    assert d["tcp_port_ranges"] == ["443", "443"]
    assert d["server_group_ids"] == ["7"]
    assert d["bypass_type"] == "NEVER"
    assert d["inspect_traffic_with_zia"] is True


def test_app_segment_view_forbids_extra():
    with pytest.raises(ValidationError):
        AppSegmentSummary(
            id="1",
            name="x",
            enabled=True,
            domain_name_count=0,
            server_group_count=0,
            bogus="nope",
        )


# =============================================================================
# Browser-access (BA) segments
# =============================================================================


def test_ba_segment_counts_clientless_apps():
    raw = {
        "id": "5",
        "name": "ba",
        "enabled": True,
        "domain_names": ["app.x"],
        "clientlessApps": [{"name": "App1"}, {"name": "App2"}],
    }
    assert ba_summary(raw).model_dump()["clientless_app_count"] == 2
    detail = ba_detail(raw).model_dump()
    assert detail["clientless_app_names"] == ["App1", "App2"]


# =============================================================================
# PRA segments
# =============================================================================


def test_pra_segment_counts_pra_apps():
    raw = {
        "id": "6",
        "name": "pra",
        "enabled": True,
        "praApps": [{"name": "ssh-box"}],
    }
    assert pra_summary(raw).model_dump()["pra_app_count"] == 1
    assert pra_detail(raw).model_dump()["pra_app_names"] == ["ssh-box"]


# =============================================================================
# Lookups (reference items + segments-by-type)
# =============================================================================


def test_ref_item_shape():
    r = shape_ref({"id": 42, "name": "Default", "description": "d"}).model_dump()
    assert r["id"] == "42" and r["name"] == "Default" and r["description"] == "d"
    assert isinstance(shape_ref({"id": "1"}), RefItem)


def test_segment_by_type_row():
    row = shape_segment_by_type(
        {"id": 9, "name": "seg", "enabled": True, "applicationType": "BROWSER_ACCESS", "appId": 3}
    ).model_dump()
    assert row["id"] == "9" and row["type"] == "BROWSER_ACCESS" and row["app_id"] == "3"


# =============================================================================
# LSS configs + catalog wrapper
# =============================================================================


def test_lss_config_summary_reads_nested_config_block():
    raw = {
        "id": "10",
        "config": {
            "name": "audit-feed",
            "enabled": True,
            "sourceLogType": "audit_logs",
            "lssHost": "siem.local",
            "lssPort": 5514,
        },
        "connectorGroups": [{"id": "1"}],
    }
    s = lss_summary(raw).model_dump()
    assert s["name"] == "audit-feed"
    assert s["source_log_type"] == "audit_logs"
    assert s["lss_port"] == "5514"
    assert s["connector_group_count"] == 1


def test_lss_config_detail_counts_filters():
    raw = {"id": "11", "config": {"name": "f", "filter": ["A", "B"], "useTls": True}}
    d = lss_detail(raw).model_dump()
    assert d["filter_count"] == 2 and d["use_tls"] is True


def test_lss_catalog_passes_payload_through():
    c = Catalog(kind="log_types", items=["a", "b"]).model_dump()
    assert c["kind"] == "log_types" and c["items"] == ["a", "b"]
