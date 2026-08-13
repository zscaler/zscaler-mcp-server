"""Tenant-scope IDs are not credentials — the errors must not conflate them.

Issue #98: a missing ``ZSCALER_CUSTOMER_ID`` (ZPA) or ``ZCELL_CUSTOMER_ID``
(ZCell) was reported as "missing OneAPI credentials", sending operators to
re-check a client ID / secret that was working fine, and hiding that a missing
customer ID can mean "tenant not entitled to this product" rather than
"misconfigured".

Env vars are pinned to empty strings (not deleted) so ``load_dotenv()`` — which
never overrides existing variables — cannot re-populate them from a local .env.
"""

from __future__ import annotations

import pytest

from zscaler_mcp.client import get_zscaler_client

_ALL_VARS = [
    "ZSCALER_CLIENT_ID",
    "ZSCALER_CLIENT_SECRET",
    "ZSCALER_PRIVATE_KEY",
    "ZSCALER_VANITY_DOMAIN",
    "ZSCALER_CUSTOMER_ID",
    "ZCELL_CUSTOMER_ID",
]


def _pin_env(monkeypatch, **present: str) -> None:
    for name in _ALL_VARS:
        monkeypatch.setenv(name, present.get(name, ""))


def test_missing_credentials_still_reported_as_credentials(monkeypatch):
    _pin_env(monkeypatch)
    with pytest.raises(RuntimeError, match="OneAPI credentials"):
        get_zscaler_client(service="zia")


def test_missing_zpa_customer_id_is_not_called_a_credential(monkeypatch):
    _pin_env(monkeypatch, ZSCALER_CLIENT_ID="id", ZSCALER_VANITY_DOMAIN="acme")
    with pytest.raises(RuntimeError) as exc:
        get_zscaler_client(service="zpa")
    message = str(exc.value)
    assert "ZSCALER_CUSTOMER_ID" in message
    assert "zpa" in message
    assert "not an OneAPI credential" in message
    assert "entitled" in message
    assert "missing OneAPI credentials" not in message


def test_missing_zcell_customer_id_is_not_called_a_credential(monkeypatch):
    _pin_env(monkeypatch, ZSCALER_CLIENT_ID="id", ZSCALER_VANITY_DOMAIN="acme")
    with pytest.raises(RuntimeError) as exc:
        get_zscaler_client(service="zcell")
    message = str(exc.value)
    assert "ZCELL_CUSTOMER_ID" in message
    assert "zcell" in message
    assert "not an OneAPI credential" in message
    assert "missing OneAPI credentials" not in message


def test_missing_credentials_win_over_missing_scope(monkeypatch):
    # When BOTH are absent the operator should fix credentials first — the
    # credential error must be the one raised.
    _pin_env(monkeypatch)
    with pytest.raises(RuntimeError, match="OneAPI credentials"):
        get_zscaler_client(service="zpa")


def test_scope_ids_not_required_for_other_services(monkeypatch):
    # zia does not need either customer ID: with creds present the scope check
    # must not fire (the call proceeds past it to the secret/key check).
    _pin_env(monkeypatch, ZSCALER_CLIENT_ID="id", ZSCALER_VANITY_DOMAIN="acme")
    with pytest.raises(ValueError, match="ZSCALER_CLIENT_SECRET or ZSCALER_PRIVATE_KEY"):
        get_zscaler_client(service="zia")
