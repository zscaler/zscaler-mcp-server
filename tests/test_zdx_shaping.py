"""Shaping tests for the new ZDX tool families (alerts, inventory, probes,
deep traces, writes).

These exercise the shapers directly — no SDK, no credentials — proving the
curated-view pattern drops SDK noise and is resilient to camel/snake keys.
"""

import pytest

from zscaler_mcp.tools.zdx._common import (
    ProbeSummary,
    TraceMetric,
    _shape_metric,
    _shape_probe,
)
from zscaler_mcp.tools.zdx.deeptrace_manage import OperationResult, StartedTrace
from zscaler_mcp.tools.zdx.list_alerts import (
    AffectedDeviceSummary,
    AlertDetail,
    AlertSummary,
    _shape_affected_device,
    _shape_alert_detail,
    _shape_alert_summary,
)
from zscaler_mcp.tools.zdx.list_deep_traces import (
    DeepTraceSummary,
    _shape_trace,
)
from zscaler_mcp.tools.zdx.list_software_inventory import (
    SoftwareInstallSummary,
    SoftwareSummary,
    _shape_software,
    _shape_software_install,
)

# =============================================================================
# Alerts
# =============================================================================

RAW_ALERT = {
    "id": 7473160764821179371,
    "ruleName": "High latency",
    "severity": "CRITICAL",
    "alertType": "PERFORMANCE",
    "startedOn": "1700000000",
    "numDevices": 42,
    "applicationName": "ServiceNow",
    "impactedDepartments": [{"id": "1", "name": "Sales"}, {"name": "IT"}],
    "impactedLocations": ["HQ", "Branch"],
    "internalHref": "/zdx/alerts/123",
}


def test_alert_summary_curates_and_coerces():
    view = _shape_alert_summary(RAW_ALERT)
    assert isinstance(view, AlertSummary)
    d = view.model_dump()
    assert d["id"] == "7473160764821179371"  # numeric -> string
    assert d["rule_name"] == "High latency"
    assert d["severity"] == "CRITICAL"
    assert d["num_devices"] == 42
    assert "internalHref" not in d


def test_alert_detail_extracts_impacted_scope_names():
    view = _shape_alert_detail(RAW_ALERT)
    assert isinstance(view, AlertDetail)
    d = view.model_dump()
    assert d["impacted_departments"] == ["Sales", "IT"]
    assert d["impacted_locations"] == ["HQ", "Branch"]
    assert "internalHref" not in d


def test_affected_device_pulls_nested_user():
    raw = {"id": 555, "name": "host1", "userdetails": {"id": 9, "email": "a@b.com"}}
    d = _shape_affected_device(raw).model_dump()
    assert isinstance(_shape_affected_device(raw), AffectedDeviceSummary)
    assert d["id"] == "555"
    assert d["user_id"] == "9"
    assert d["user_name"] == "a@b.com"


# =============================================================================
# Inventory
# =============================================================================


def test_software_summary_curates():
    raw = {
        "softwareKey": "Chrome_120",
        "softwareName": "Google Chrome",
        "vendor": "Google",
        "softwareVersion": "120.0",
        "installCount": 300,
        "userCount": 250,
        "rawTelemetryBlob": {"x": 1},
    }
    view = _shape_software(raw)
    assert isinstance(view, SoftwareSummary)
    d = view.model_dump()
    assert d["software_key"] == "Chrome_120"
    assert d["install_count"] == 300
    assert "rawTelemetryBlob" not in d


def test_software_install_curates():
    raw = {
        "software_key": "Chrome_120",
        "userId": 7,
        "deviceId": 88,
        "hostname": "h",
        "version": "120",
    }
    view = _shape_software_install(raw)
    assert isinstance(view, SoftwareInstallSummary)
    d = view.model_dump()
    assert d["user_id"] == "7"
    assert d["device_id"] == "88"
    assert d["software_version"] == "120"


# =============================================================================
# Probes
# =============================================================================


def test_probe_summary_keeps_id_for_deeptrace():
    raw = {"id": 266957, "name": "web-probe", "numProbes": 3, "avgScore": 88.5, "noise": "x"}
    view = _shape_probe(raw)
    assert isinstance(view, ProbeSummary)
    d = view.model_dump()
    assert d["id"] == "266957"
    assert d["avg_score"] == 88.5
    assert "noise" not in d


# =============================================================================
# Deep traces
# =============================================================================


def test_trace_summary_normalizes_timestamps_to_iso():
    raw = {"trace_id": 1, "status": "COMPLETE", "session_name": "s", "created": 1700000000}
    view = _shape_trace(raw)
    assert isinstance(view, DeepTraceSummary)
    d = view.model_dump()
    assert d["trace_id"] == "1"
    # convert_timestamps rewrites epoch -> ISO string.
    assert d["created"] is not None and "T" in d["created"]


def test_trace_metric_keeps_nested_payload():
    raw = {"metric": "latency", "unit": "ms", "datapoints": [{"t": 1, "v": 2}]}
    view = _shape_metric(raw)
    assert isinstance(view, TraceMetric)
    d = view.model_dump()
    assert d["name"] == "latency"
    assert d["data"]["datapoints"] == [{"t": 1, "v": 2}]


# =============================================================================
# Write result views
# =============================================================================


def test_started_trace_and_operation_result_views():
    st = StartedTrace(trace_id="t1", status="started", session_name="s")
    assert st.model_dump()["trace_id"] == "t1"
    op = OperationResult(success=True, message="done")
    assert op.model_dump() == {"success": True, "message": "done"}


def test_views_reject_uncurated_fields():
    with pytest.raises(Exception):
        AlertSummary(id="1", leaked="x")


def test_output_schema_lists_curated_fields_only():
    props = set(SoftwareSummary.output_schema()["properties"])
    assert props == {
        "software_key",
        "software_name",
        "vendor",
        "software_version",
        "install_count",
        "user_count",
    }
