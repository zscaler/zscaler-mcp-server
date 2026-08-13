"""Pagination reaches the ZPA policy-rules API (issue #96).

The ``/policySet/rules/policyType/{type}`` endpoint paginates (default 20 rows,
max 500) and the SDK does not auto-page, so ``page`` / ``page_size`` / ``search``
must travel from the tool inputs to the SDK call — otherwise callers silently
see only the first 20 rules of a policy whose evaluation order matters.

``ListRulesInput`` is shared by all five policy-rule families (access, timeout,
forwarding, isolation, app-protection), so exercising the shared helper plus a
registry sweep of the advertised schemas covers every one of them.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from zscaler_mcp.registry import REGISTRY, discover_tools
from zscaler_mcp.tools.zpa._policy_common import ListRulesInput, list_rules

_POLICY_LIST_TOOLS = [
    "zpa_list_access_policy_rules",
    "zpa_list_timeout_policy_rules",
    "zpa_list_forwarding_policy_rules",
    "zpa_list_isolation_policy_rules",
    "zpa_list_app_protection_rules",
]

# Every other ZPA list-style tool whose SDK method documents page/page_size —
# the same 20-row truncation applied to all of them (issue #96 sweep).
# Deliberately absent: the LSS catalogs (static, the API does not paginate),
# get_zpa_isolation_profile (SDK list_cbi_profiles has no pagination), and
# get_zpa_app_segments_by_type (SDK documents page_size/search but no page).
_OTHER_PAGINATED_TOOLS = [
    "zpa_list_ba_certificates",
    "zpa_list_pra_credentials",
    "zpa_list_pra_portals",
    "zpa_list_provisioning_keys",
    "get_zpa_saml_attribute",
    "get_zpa_scim_attribute",
    "get_zpa_scim_group",
    "get_zpa_app_protection_profile",
    "get_zpa_posture_profile",
    "get_zpa_trusted_network",
    "get_zpa_enrollment_certificate",
]


class _FakePolicies:
    def __init__(self) -> None:
        self.captured: dict[str, Any] | None = None

    def list_rules(self, policy_type: str, query_params: dict[str, Any]):
        self.captured = {"policy_type": policy_type, **query_params}
        return [], None, None


def _fake_client(policies: _FakePolicies):
    class _Zpa:
        pass

    class _Client:
        pass

    zpa = _Zpa()
    zpa.policies = policies
    client = _Client()
    client.zpa = zpa
    return client


def _call(**kwargs: Any) -> dict[str, Any]:
    policies = _FakePolicies()
    with patch(
        "zscaler_mcp.tools.zpa._policy_common.get_zscaler_client",
        return_value=_fake_client(policies),
    ):
        list_rules("access", ListRulesInput(**kwargs))
    assert policies.captured is not None
    return policies.captured


def test_pagination_params_reach_the_sdk():
    captured = _call(page=3, page_size=500, search="Engineering", microtenant_id="mt1")
    assert captured == {
        "policy_type": "access",
        "page": "3",
        "page_size": "500",
        "search": "Engineering",
        "microtenant_id": "mt1",
    }


def test_omitted_params_are_not_sent():
    # The API's own defaults govern anything the caller leaves unset.
    assert _call() == {"policy_type": "access"}


def test_page_size_is_capped_at_the_api_maximum():
    with pytest.raises(ValueError):
        ListRulesInput(page_size=501)
    with pytest.raises(ValueError):
        ListRulesInput(page=0)


def test_every_policy_family_advertises_pagination():
    """The shared input model must reach all five families' schemas."""
    discover_tools()
    for name in _POLICY_LIST_TOOLS:
        spec = REGISTRY.get(name)
        assert spec is not None, f"{name} is not registered"
        fields = spec.input_model.model_fields
        for param in ("page", "page_size", "search"):
            assert param in fields, f"{name} is missing '{param}'"


def test_every_other_paginated_zpa_list_tool_advertises_pagination():
    """The sweep: every ZPA list tool whose SDK method paginates exposes it."""
    discover_tools()
    for name in _OTHER_PAGINATED_TOOLS:
        spec = REGISTRY.get(name)
        assert spec is not None, f"{name} is not registered"
        fields = spec.input_model.model_fields
        for param in ("page", "page_size"):
            assert param in fields, f"{name} is missing '{param}'"
