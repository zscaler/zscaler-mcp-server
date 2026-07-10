"""Shaping tests for the ZTW (Cloud & Branch Connector) tool family.

Same contract as the segment-groups reference test: shapers drop SDK noise,
coerce ids to strings, tolerate camel/snake keys, count relational members, and
the AgentView base forbids uncurated fields. No SDK / no credentials.
"""

import pytest
from pydantic import ValidationError

from zscaler_mcp.common.ztw_helpers import (
    validate_and_convert_country_code,
    validate_and_convert_country_codes,
)
from zscaler_mcp.tools.ztw.account_details import _shape_account_detail
from zscaler_mcp.tools.ztw.discovery_service import DiscoverySettings
from zscaler_mcp.tools.ztw.ip_destination_groups import (
    DestinationGroupSummary,
    shape_detail as shape_dest_detail,
    shape_summary as shape_dest_summary,
)
from zscaler_mcp.tools.ztw.ip_groups import (
    shape_detail as shape_ipg_detail,
    shape_summary as shape_ipg_summary,
)
from zscaler_mcp.tools.ztw.ip_source_groups import shape_summary as shape_src_summary
from zscaler_mcp.tools.ztw.list_admins import shape_admin_summary
from zscaler_mcp.tools.ztw.list_roles import RoleSummary, shape_role
from zscaler_mcp.tools.ztw.network_service_groups import shape_group as shape_nsg
from zscaler_mcp.tools.ztw.network_services import shape_service as shape_ns
from zscaler_mcp.tools.ztw.public_cloud_info import _shape_cloud_info


# =============================================================================
# Country helper
# =============================================================================


def test_country_helper_resolves_names_codes_and_country_prefix():
    assert validate_and_convert_country_code("Canada") == "COUNTRY_CA"
    assert validate_and_convert_country_code("US") == "COUNTRY_US"
    assert validate_and_convert_country_code("COUNTRY_GB") == "COUNTRY_GB"
    assert validate_and_convert_country_codes(["Canada", "US"]) == ["COUNTRY_CA", "COUNTRY_US"]


def test_country_helper_rejects_unknown():
    with pytest.raises(ValueError):
        validate_and_convert_country_code("Notalandia")


# =============================================================================
# IP destination groups
# =============================================================================


def test_dest_group_summary_counts_and_drops_noise():
    raw = {
        "id": 42,
        "name": "blocked-ips",
        "type": "DSTN_IP",
        "description": "deny list",
        "addresses": ["1.1.1.1", "2.2.2.2"],
        "countries": [],
        "creationTime": "1700000000",  # noise — must not appear
        "href": "/x/y",
    }
    d = shape_dest_summary(raw).model_dump()
    assert d["id"] == "42"  # coerced to str
    assert d["address_count"] == 2
    assert d["country_count"] == 0
    assert "creationTime" not in d and "href" not in d


def test_dest_group_detail_surfaces_members():
    raw = {
        "id": "7",
        "name": "geo",
        "type": "DSTN_OTHER",
        "countries": ["COUNTRY_CA"],
        "addresses": [],
    }
    d = shape_dest_detail(raw).model_dump()
    assert d["countries"] == ["COUNTRY_CA"]
    assert d["country_count"] == 1


def test_dest_group_view_forbids_extra_field():
    with pytest.raises(ValidationError):
        DestinationGroupSummary(
            id="1", name="x", type=None, description=None, address_count=0, country_count=0, bogus=1
        )


# =============================================================================
# IP groups + source groups
# =============================================================================


def test_ip_group_summary_and_detail():
    raw = {"id": 3, "name": "g", "ipAddresses": ["10.0.0.1"]}  # camelCase tolerated
    s = shape_ipg_summary(raw).model_dump()
    assert s["id"] == "3" and s["ip_address_count"] == 1
    d = shape_ipg_detail(raw).model_dump()
    assert d["ip_addresses"] == ["10.0.0.1"]


def test_ip_source_group_summary():
    raw = {"id": "9", "name": "src", "ip_addresses": ["192.168.0.0/24"]}
    s = shape_src_summary(raw).model_dump()
    assert s["id"] == "9" and s["ip_address_count"] == 1


# =============================================================================
# Network services + groups
# =============================================================================


def test_network_service_counts_port_ranges():
    raw = {
        "id": 1,
        "name": "https",
        "type": "STANDARD",
        "destTcpPorts": [{"start": 443}],
        "srcUdpPorts": [],
    }
    s = shape_ns(raw).model_dump()
    assert s["tcp_port_count"] == 1 and s["udp_port_count"] == 0


def test_network_service_group_counts_members():
    raw = {"id": "2", "name": "web", "services": [{"id": "1"}, {"id": "2"}]}
    g = shape_nsg(raw).model_dump()
    assert g["service_count"] == 2


# =============================================================================
# Admin roles + users
# =============================================================================


def test_role_summary():
    r = shape_role({"id": 5, "name": "Super Admin", "roleType": "EC_ADMIN"}).model_dump()
    assert r["id"] == "5" and r["role_type"] == "EC_ADMIN"
    assert isinstance(shape_role({"id": "1", "name": "n"}), RoleSummary)


def test_admin_summary_extracts_nested_role_name():
    raw = {"id": "11", "loginName": "jdoe", "userName": "John", "role": {"name": "Admin"}}
    s = shape_admin_summary(raw).model_dump()
    assert s["login_name"] == "jdoe" and s["role_name"] == "Admin"


# =============================================================================
# Cloud + discovery
# =============================================================================


def test_cloud_info_and_account_detail():
    ci = _shape_cloud_info({"id": 1, "accountName": "prod", "cloudProvider": "AWS"}).model_dump()
    assert ci["id"] == "1" and ci["cloud_type"] == "AWS" and ci["name"] == "prod"
    ad = _shape_account_detail({"id": "2", "accountId": "999"}).model_dump()
    assert ad["account_id"] == "999"


def test_discovery_settings_keeps_payload():
    d = DiscoverySettings(discovery_role="r", external_id="e", settings={"k": "v"}).model_dump()
    assert d["settings"] == {"k": "v"} and d["discovery_role"] == "r"
