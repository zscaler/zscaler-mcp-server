"""Shaping tests for the ZCell (Zscaler Cellular) read-only tool family.

Same contract as the other service shaping tests: shapers drop SDK noise, coerce
ids to strings, tolerate camel/snake keys, and the AgentView base forbids
uncurated fields. Pure shaper tests — no SDK, no credentials.
"""

import pytest

from zscaler_mcp.tools.zcell.anomaly_policy import (
    AnomalyPolicySummary,
    _shape_iccid_violation,
    _shape_log,
    _shape_policy,
)
from zscaler_mcp.tools.zcell.audit_data_handling import AuditEntry, _shape_entry, _shape_metadata
from zscaler_mcp.tools.zcell.customer_data_handling import CustomerDataView, _shape_customer
from zscaler_mcp.tools.zcell.customer_region_handling import (
    RegionView,
    _shape_region,
    _shape_status,
)
from zscaler_mcp.tools.zcell.network_events import NetworkEventView, _shape_event
from zscaler_mcp.tools.zcell.sim_analytics import (
    _shape_country,
    _shape_day,
    _shape_map,
    _shape_summary,
)
from zscaler_mcp.tools.zcell.sim_analytics import (
    _shape_sim as _shape_usage_sim,
)
from zscaler_mcp.tools.zcell.sim_handling import SimDetail, _shape_search, _shape_sim
from zscaler_mcp.tools.zcell.sim_location_groups import (
    SimLocationGroupSummary,
    _shape_detail,
)
from zscaler_mcp.tools.zcell.sim_location_groups import (
    _shape_summary as _shape_slg_summary,
)
from zscaler_mcp.tools.zcell.tag_handling import TagView, _shape_tag

# =============================================================================
# Anomaly Policy
# =============================================================================


def test_anomaly_policy_curates_and_stringifies_id():
    raw = {
        "id": 208,
        "policyName": "GeoFence01",
        "policyType": "GEOFENCING",
        "enabled": True,
        "runningStatus": "RUNNING",
        "simLocationGroupIds": [219],
        "violations": 3,
        "jsonData": {"heavy": "blob"},  # noise — must be dropped
    }
    view = _shape_policy(raw)
    assert isinstance(view, AnomalyPolicySummary)
    d = view.model_dump()
    assert d["id"] == "208"
    assert d["policy_type"] == "GEOFENCING"
    assert d["sim_location_group_ids"] == [219]
    assert "jsonData" not in d


def test_anomaly_policy_log_and_iccid_violation_shape():
    log = _shape_log({"policyId": "208", "status": "ENABLED", "message": "ok", "recordedAt": 1})
    assert log.model_dump()["policy_id"] == "208"

    viol = _shape_iccid_violation(
        {"policyId": "208", "iccid": "8985", "eventType": "EXIT", "timestamp": 123}
    )
    assert viol.model_dump()["event_type"] == "EXIT"


# =============================================================================
# SIM Location Groups
# =============================================================================


def test_sim_location_group_summary_and_detail():
    summ = _shape_slg_summary({"id": 5, "name": "Fleet", "trackedDevices": ["8985"]})
    assert isinstance(summ, SimLocationGroupSummary)
    assert summ.model_dump()["id"] == "5"
    assert summ.model_dump()["tracked_devices"] == ["8985"]

    detail = _shape_detail(
        {
            "id": 5,
            "name": "Fleet",
            "geoFenceData": {"radius": 1},
            "linkedPolicies": [{"policyId": "208"}],
            "insideAndTrackedIccids": ["8985"],
        }
    )
    dd = detail.model_dump()
    assert dd["geo_fence_data"] == {"radius": 1}
    assert dd["inside_and_tracked_iccids"] == ["8985"]


# =============================================================================
# SIM Analytics
# =============================================================================


def test_sim_analytics_shapers_build():
    assert _shape_map({"iccid": ["8985"], "lat": 1.0, "lng": 2.0}).model_dump()["iccid"] == ["8985"]
    assert _shape_summary({"total": 10, "active": 7}).model_dump()["total"] == 10
    assert _shape_country({"country": "US", "usage": 100}).model_dump()["country"] == "US"
    assert _shape_day({"creationTime": 1, "usage": 50}).model_dump()["usage"] == 50
    assert _shape_usage_sim({"iccid": "8985", "usage": 5}).model_dump()["iccid"] == "8985"


# =============================================================================
# Customer Region Handling
# =============================================================================


def test_region_shapers():
    reg = _shape_region({"region": "AMER", "configured": True})
    assert isinstance(reg, RegionView)
    assert reg.model_dump()["configured"] is True

    status = _shape_status(
        {"region": "AMER", "operationalStatus": "UP", "mapACStatus": "OK", "bc": {"status": "UP"}}
    )
    sd = status.model_dump()
    assert sd["operational_status"] == "UP"
    assert sd["map_a_c_status"] == "OK"


# =============================================================================
# Audit Data Handling
# =============================================================================


def test_audit_entry_drops_data_blobs_and_stringifies_ids():
    raw = {
        "id": 1,
        "auditOperationType": "Update",
        "objectType": "AnomalyPolicy",
        "objectId": 208,
        "customerId": 42,
        "visibility": "Customer",
        "oldData": {"heavy": "blob"},
        "newData": {"heavy": "blob"},
    }
    view = _shape_entry(raw)
    assert isinstance(view, AuditEntry)
    d = view.model_dump()
    assert d["id"] == "1"
    assert d["object_id"] == "208"
    assert d["customer_id"] == "42"
    assert "oldData" not in d and "newData" not in d


def test_audit_metadata_shape():
    md = _shape_metadata({"operations": ["Create", "Update"], "objectTypes": ["Tag"]})
    assert md.model_dump()["operations"] == ["Create", "Update"]


# =============================================================================
# Network Events
# =============================================================================


def test_network_event_curates_subset():
    raw = {
        "timestamp": 1,
        "eventName": "SESSION_START",
        "outcome": "SUCCESS",
        "iccid": "8985",
        "country": "US",
        "operatorName": "Verizon",
        "ratType": "LTE",
        "locCid": "noise",  # dropped
    }
    view = _shape_event(raw)
    assert isinstance(view, NetworkEventView)
    d = view.model_dump()
    assert d["event_name"] == "SESSION_START"
    assert d["operator_name"] == "Verizon"
    assert "locCid" not in d


# =============================================================================
# SIM Handling
# =============================================================================


def test_sim_detail_shape_and_lists():
    raw = {
        "iccid": "8985",
        "imsi": "310",
        "status": "active",
        "networkStatus": "online",
        "ipAddress": ["10.0.0.1"],
        "tags": ["fleet"],
        "deviceType": "router",
    }
    view = _shape_sim(raw)
    assert isinstance(view, SimDetail)
    d = view.model_dump()
    assert d["network_status"] == "online"
    assert d["ip_address"] == ["10.0.0.1"]
    assert d["tags"] == ["fleet"]


def test_sim_search_envelope_extracts_content():
    raw = {
        "totalUsage": 1234,
        "pageDetails": {
            "content": [{"iccid": "8985", "status": "active"}],
            "totalElements": 1,
            "pageNumber": 0,
            "totalPages": 1,
        },
    }
    view = _shape_search(raw)
    d = view.model_dump()
    assert d["total_usage"] == 1234
    assert d["total_count"] == 1
    assert len(d["sims"]) == 1
    assert d["sims"][0]["iccid"] == "8985"


# =============================================================================
# Tag Handling
# =============================================================================


def test_tag_shape():
    tag = _shape_tag({"id": 1558, "name": "fleet", "tenantId": 42})
    assert isinstance(tag, TagView)
    d = tag.model_dump()
    assert d["id"] == "1558"
    assert d["tenant_id"] == "42"


# =============================================================================
# Customer Data Handling
# =============================================================================


def test_customer_data_shape():
    raw = {
        "id": "gi754",
        "name": "Acme",
        "email": "a@acme.com",
        "isActivated": True,
        "regions": ["AMER"],
        "totalSims": 100,
        "zia": {"orgId": "1", "cloudName": "zscalertwo"},
    }
    view = _shape_customer(raw)
    assert isinstance(view, CustomerDataView)
    d = view.model_dump()
    assert d["is_activated"] is True
    assert d["regions"] == ["AMER"]
    assert d["zia"] == {"orgId": "1", "cloudName": "zscalertwo"}


# =============================================================================
# Cross-cutting contract
# =============================================================================


@pytest.mark.parametrize(
    "view_cls",
    [AnomalyPolicySummary, SimLocationGroupSummary, RegionView, AuditEntry, SimDetail, TagView],
)
def test_views_forbid_uncurated_fields(view_cls):
    with pytest.raises(Exception):
        view_cls(definitely_not_a_field="leak")
