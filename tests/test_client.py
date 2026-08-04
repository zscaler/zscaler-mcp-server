"""Tests for the Zscaler SDK client factory's configuration guards.

The factory distinguishes two kinds of missing configuration, and the
distinction is the point: OneAPI **credentials** authenticate the client and are
required for every product, whereas ``ZSCALER_CUSTOMER_ID`` / ``ZCELL_CUSTOMER_ID``
are **tenant scope** required by exactly one product each. Reporting the latter
as a missing credential sends operators to re-check auth that is already working.
"""

from __future__ import annotations

import pytest

from zscaler_mcp.client import _absent, get_zscaler_client

# The credential set that is valid for every product; individual tests drop or
# add to a copy of this.
FULL_CREDENTIALS = {
    "ZSCALER_CLIENT_ID": "client-id",
    "ZSCALER_CLIENT_SECRET": "client-secret",
    "ZSCALER_VANITY_DOMAIN": "example",
}

# Env vars the factory reads. Cleared before each test so a developer's real
# .env / shell cannot leak in and mask a missing-value assertion.
_FACTORY_VARS = (
    "ZSCALER_CLIENT_ID",
    "ZSCALER_CLIENT_SECRET",
    "ZSCALER_PRIVATE_KEY",
    "ZSCALER_VANITY_DOMAIN",
    "ZSCALER_CUSTOMER_ID",
    "ZCELL_CUSTOMER_ID",
    "ZSCALER_CLOUD",
    "ZSCALER_MCP_USER_AGENT_COMMENT",
)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Blank the factory's env surface and neutralise ``load_dotenv``."""
    for name in _FACTORY_VARS:
        monkeypatch.delenv(name, raising=False)
    # The factory calls load_dotenv() first; a real .env on the developer's box
    # would otherwise repopulate what we just cleared.
    monkeypatch.setattr("zscaler_mcp.client.load_dotenv", lambda *a, **k: False)


def _set(monkeypatch, values: dict[str, str]) -> None:
    for name, value in values.items():
        monkeypatch.setenv(name, value)


# ---------------------------------------------------------------------------
# _absent
# ---------------------------------------------------------------------------


def test_absent_reports_missing_and_blank_in_declaration_order():
    assert _absent({"A": "set", "B": None, "C": "   ", "D": ""}) == ["B", "C", "D"]


def test_absent_returns_empty_when_all_present():
    assert _absent({"A": "x", "B": "y"}) == []


# ---------------------------------------------------------------------------
# Missing OneAPI credentials — still reported as credentials
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dropped", ["ZSCALER_CLIENT_ID", "ZSCALER_VANITY_DOMAIN"])
def test_missing_credential_is_reported_as_a_credential(monkeypatch, dropped):
    creds = {k: v for k, v in FULL_CREDENTIALS.items() if k != dropped}
    _set(monkeypatch, creds)

    with pytest.raises(RuntimeError) as excinfo:
        get_zscaler_client(service="zia")

    message = str(excinfo.value)
    assert "missing OneAPI credentials" in message
    assert dropped in message


def test_blank_credential_counts_as_missing(monkeypatch):
    _set(monkeypatch, {**FULL_CREDENTIALS, "ZSCALER_CLIENT_ID": "   "})

    with pytest.raises(RuntimeError, match="missing OneAPI credentials"):
        get_zscaler_client(service="zia")


def test_credentials_are_checked_before_tenant_scope(monkeypatch):
    # Both a credential and the ZPA scope are absent. The credential problem is
    # the more fundamental one and must be what the operator is told about.
    _set(monkeypatch, {"ZSCALER_CLIENT_SECRET": "client-secret", "ZSCALER_CLIENT_ID": "client-id"})

    with pytest.raises(RuntimeError) as excinfo:
        get_zscaler_client(service="zpa")

    message = str(excinfo.value)
    assert "missing OneAPI credentials" in message
    assert "ZSCALER_VANITY_DOMAIN" in message
    assert "ZSCALER_CUSTOMER_ID" not in message


# ---------------------------------------------------------------------------
# Missing tenant scope — must NOT be reported as a credential
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("service", "variable"),
    [("zpa", "ZSCALER_CUSTOMER_ID"), ("zcell", "ZCELL_CUSTOMER_ID")],
)
def test_missing_tenant_scope_is_not_called_a_credential(monkeypatch, service, variable):
    _set(monkeypatch, FULL_CREDENTIALS)

    with pytest.raises(RuntimeError) as excinfo:
        get_zscaler_client(service=service)

    message = str(excinfo.value)
    assert variable in message
    # The regression this test exists for: the tenant ID was reported as a
    # missing credential, misdirecting operators to re-check working auth.
    assert "missing OneAPI credentials" not in message
    assert "tenant/customer ID" in message
    assert "not a OneAPI credential" in message
    # Name the product family so the operator knows what is affected...
    assert service in message
    # ...and say that a nonexistent value can mean "not entitled", so the
    # operator isn't left hunting for an ID that may not exist.
    assert "not entitled" in message


@pytest.mark.parametrize(
    ("service", "variable"),
    [("zpa", "ZSCALER_CUSTOMER_ID"), ("zcell", "ZCELL_CUSTOMER_ID")],
)
def test_blank_tenant_scope_counts_as_missing(monkeypatch, service, variable):
    _set(monkeypatch, {**FULL_CREDENTIALS, variable: "   "})

    with pytest.raises(RuntimeError) as excinfo:
        get_zscaler_client(service=service)

    assert variable in str(excinfo.value)


# ---------------------------------------------------------------------------
# Tenant scope is per-product, not global
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", ["zia", "zdx", "zcc", "ztw", "zid", "zins", "zms", None])
def test_other_services_do_not_require_any_tenant_scope(monkeypatch, service):
    # Products other than ZPA / ZCell must construct fine with no customer id.
    # Guards the "reads as OneAPI-wide when it is per-product" half of the bug.
    _set(monkeypatch, FULL_CREDENTIALS)
    constructed = {}
    monkeypatch.setattr(
        "zscaler.ZscalerClient", lambda config: constructed.setdefault("cfg", config)
    )

    get_zscaler_client(service=service)

    assert "customerId" not in constructed["cfg"]
    assert "zcellCustomerId" not in constructed["cfg"]


def test_zpa_scope_does_not_satisfy_zcell(monkeypatch):
    # The two ids are independent; ZPA's must not stand in for ZCell's.
    _set(monkeypatch, {**FULL_CREDENTIALS, "ZSCALER_CUSTOMER_ID": "zpa-tenant"})

    with pytest.raises(RuntimeError) as excinfo:
        get_zscaler_client(service="zcell")

    assert "ZCELL_CUSTOMER_ID" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Happy path — the guards don't block a fully-configured call
# ---------------------------------------------------------------------------


def test_zpa_constructs_when_scope_present(monkeypatch):
    _set(monkeypatch, {**FULL_CREDENTIALS, "ZSCALER_CUSTOMER_ID": "zpa-tenant"})
    constructed = {}
    monkeypatch.setattr(
        "zscaler.ZscalerClient", lambda config: constructed.setdefault("cfg", config)
    )

    get_zscaler_client(service="zpa")

    assert constructed["cfg"]["customerId"] == "zpa-tenant"
    assert constructed["cfg"]["clientId"] == "client-id"


def test_zcell_constructs_when_scope_present(monkeypatch):
    _set(monkeypatch, {**FULL_CREDENTIALS, "ZCELL_CUSTOMER_ID": "zcell-tenant"})
    constructed = {}
    monkeypatch.setattr(
        "zscaler.ZscalerClient", lambda config: constructed.setdefault("cfg", config)
    )

    get_zscaler_client(service="zcell")

    assert constructed["cfg"]["zcellCustomerId"] == "zcell-tenant"


def test_missing_secret_and_private_key_still_raises_value_error(monkeypatch):
    # Unchanged behaviour: the secret/key check is separate and stays a ValueError.
    _set(monkeypatch, {k: v for k, v in FULL_CREDENTIALS.items() if k != "ZSCALER_CLIENT_SECRET"})

    with pytest.raises(ValueError, match="ZSCALER_CLIENT_SECRET or ZSCALER_PRIVATE_KEY"):
        get_zscaler_client(service="zia")
