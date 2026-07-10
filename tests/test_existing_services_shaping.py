"""Backfill shaping tests for the ZCC / EASM / ZIdentity / Z-Insights tool
families that were added without tests.

Same contract as the segment-groups reference test: shapers drop SDK noise,
coerce ids to strings, tolerate camel/snake keys, and the AgentView base forbids
uncurated fields. No SDK / no credentials.
"""

import pytest

# EASM
from zscaler_mcp.tools.easm.findings import FindingSummary, _shape_finding_summary
from zscaler_mcp.tools.easm.lookalike_domains import _shape_lookalike_summary
from zscaler_mcp.tools.easm.organizations import OrganizationSummary, _shape_organization

# ZCC
from zscaler_mcp.tools.zcc.list_devices import DeviceSummary as ZccDeviceSummary
from zscaler_mcp.tools.zcc.list_devices import _shape_device
from zscaler_mcp.tools.zcc.list_forwarding_profiles import _shape_profile
from zscaler_mcp.tools.zcc.list_trusted_networks import _shape_network

# ZIdentity
from zscaler_mcp.tools.zid.groups import GroupSummary, shape_group
from zscaler_mcp.tools.zid.users import UserSummary, shape_user

# Z-Insights
from zscaler_mcp.tools.zins.firewall import FirewallRow
from zscaler_mcp.tools.zins.firewall import _shape_row as _shape_fw_row
from zscaler_mcp.tools.zins.shadow_it import ShadowItApp, _shape_app
from zscaler_mcp.tools.zins.web_traffic import TrafficRow
from zscaler_mcp.tools.zins.web_traffic import _shape_row as _shape_traffic_row

# =============================================================================
# ZCC
# =============================================================================


def test_zcc_device_curates_and_keeps_udid():
    raw = {
        "udid": "d-29-9b",
        "user": "jdoe@acme.com",
        "machineHostname": "laptop-1",
        "osVersion": "macOS 14",
        "agentVersion": "4.2",
        "registrationState": "REGISTERED",
        "policyBlob": {"x": 1},
    }
    view = _shape_device(raw)
    assert isinstance(view, ZccDeviceSummary)
    d = view.model_dump()
    assert d["udid"] == "d-29-9b"
    assert d["registration_state"] == "REGISTERED"
    assert "policyBlob" not in d


def test_zcc_profile_and_network_shape():
    assert _shape_profile({"id": 1, "name": "prod"}).model_dump()["name"] == "prod"
    assert _shape_network({"id": 2, "name": "office"}).model_dump()["name"] == "office"


# =============================================================================
# EASM
# =============================================================================


def test_easm_organization_and_finding():
    org = _shape_organization({"id": "o1", "name": "Acme"})
    assert isinstance(org, OrganizationSummary)
    assert org.model_dump()["id"] == "o1"

    finding = _shape_finding_summary({"id": 99, "name": "Exposed port", "severity": "critical"})
    assert isinstance(finding, FindingSummary)
    assert finding.model_dump()["id"] == "99"


def test_easm_lookalike_summary_shapes():
    view = _shape_lookalike_summary({"lookalike": "acme-login.com"})
    assert view.model_dump()  # builds without error


# =============================================================================
# ZIdentity
# =============================================================================


def test_zid_group_and_user_curate():
    g = shape_group({"id": 10, "name": "Engineering"})
    assert isinstance(g, GroupSummary)
    assert g.model_dump()["id"] == "10"

    u = shape_user({"id": 20, "loginName": "jdoe", "displayName": "J Doe"})
    assert isinstance(u, UserSummary)
    assert u.model_dump()["id"] == "20"


# =============================================================================
# Z-Insights
# =============================================================================


def test_zins_traffic_and_firewall_and_shadow_it_rows_build():
    t = _shape_traffic_row({"key": "HQ", "transactions": 100})
    assert isinstance(t, TrafficRow)

    f = _shape_fw_row({"key": "ALLOW", "sessions": 5})
    assert isinstance(f, FirewallRow)

    a = _shape_app({"name": "Dropbox", "risk_index": "HIGH"})
    assert isinstance(a, ShadowItApp)


# =============================================================================
# Cross-cutting contract
# =============================================================================


@pytest.mark.parametrize(
    "view_cls",
    [ZccDeviceSummary, OrganizationSummary, GroupSummary, UserSummary],
)
def test_views_forbid_uncurated_fields(view_cls):
    with pytest.raises(Exception):
        view_cls(definitely_not_a_field="leak")
