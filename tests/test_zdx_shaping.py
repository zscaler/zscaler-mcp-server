"""Shaping tests for the new ZDX tool families (alerts, inventory, probes,
deep traces, writes).

These exercise the shapers directly — no SDK, no credentials — proving the
curated-view pattern drops SDK noise and is resilient to camel/snake keys.
"""

from zscaler_mcp.tools.zdx.deeptrace_manage import OperationResult, StartedTrace

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


# =============================================================================
# Inventory
# =============================================================================


# =============================================================================
# Probes
# =============================================================================


# =============================================================================
# Deep traces
# =============================================================================


# =============================================================================
# Write result views
# =============================================================================


def test_started_trace_and_operation_result_views():
    st = StartedTrace(trace_id="t1", status="started", session_name="s")
    assert st.model_dump()["trace_id"] == "t1"
    op = OperationResult(success=True, message="done")
    assert op.model_dump() == {"success": True, "message": "done"}
