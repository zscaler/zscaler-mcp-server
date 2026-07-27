"""Shaping tests for the ZTW (Cloud & Branch Connector) tool family.

Same contract as the segment-groups reference test: shapers drop SDK noise,
coerce ids to strings, tolerate camel/snake keys, count relational members, and
the AgentView base forbids uncurated fields. No SDK / no credentials.
"""

import pytest

from zscaler_mcp.common.ztw_helpers import (
    validate_and_convert_country_code,
    validate_and_convert_country_codes,
)
from zscaler_mcp.tools.ztw.discovery_service import DiscoverySettings

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


# =============================================================================
# IP groups + source groups
# =============================================================================


# =============================================================================
# Network services + groups
# =============================================================================


# =============================================================================
# Admin roles + users
# =============================================================================


# =============================================================================
# Cloud + discovery
# =============================================================================


def test_discovery_settings_keeps_payload():
    d = DiscoverySettings(discovery_role="r", external_id="e", settings={"k": "v"}).model_dump()
    assert d["settings"] == {"k": "v"} and d["discovery_role"] == "r"
