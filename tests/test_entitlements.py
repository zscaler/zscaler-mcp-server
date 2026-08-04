"""Tests for OneAPI product-entitlement downscoping."""

from __future__ import annotations

import base64
import json
import logging

import pytest

from zscaler_mcp.security.entitlements import (
    PRD_TO_SERVICE,
    apply_entitlement_filter,
    decode_oneapi_token,
    extract_entitled_services,
)


def _make_token(payload: dict) -> str:
    """Build a fake (unsigned) 3-part JWT with the given payload."""
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{body}.signature"


# ---------------------------------------------------------------------------
# decode_oneapi_token
# ---------------------------------------------------------------------------


def test_decode_valid_token():
    payload = {"service-info": [{"prd": "ZPA"}], "sub": "abc"}
    decoded = decode_oneapi_token(_make_token(payload))
    assert decoded == payload


@pytest.mark.parametrize("bad", ["", "notajwt", "only.two", "a.b.c.d", "x.@@@.y"])
def test_decode_malformed_returns_none(bad):
    assert decode_oneapi_token(bad) is None


def test_decode_non_string_returns_none():
    assert decode_oneapi_token(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# extract_entitled_services
# ---------------------------------------------------------------------------


def test_extract_maps_prd_to_services():
    payload = {"service-info": [{"prd": "ZPA"}, {"prd": "ZIA"}, {"prd": "ZDX"}]}
    assert extract_entitled_services(payload) == {"zpa", "zia", "zdx"}


def test_extract_is_case_insensitive():
    payload = {"service-info": [{"prd": "zpa"}, {"prd": "Zia"}]}
    assert extract_entitled_services(payload) == {"zpa", "zia"}


def test_extract_supports_camelcase_claim_key():
    payload = {"serviceInfo": [{"prd": "ZPA"}]}
    assert extract_entitled_services(payload) == {"zpa"}


def test_extract_skips_unknown_prd_codes():
    payload = {"service-info": [{"prd": "ZPA"}, {"prd": "SOMETHING_NEW"}]}
    assert extract_entitled_services(payload) == {"zpa"}


def test_extract_handles_aliases():
    # ZIdentity surfaces under several aliases.
    assert PRD_TO_SERVICE["ZIDENTITY"] == "zid"
    assert PRD_TO_SERVICE["IDENTITY"] == "zid"
    assert PRD_TO_SERVICE["EASM"] == "zeasm"
    payload = {"service-info": [{"prd": "IDENTITY"}, {"prd": "EASM"}]}
    assert extract_entitled_services(payload) == {"zid", "zeasm"}


@pytest.mark.parametrize("payload", [{}, {"service-info": "nope"}, {"service-info": [123, "x"]}])
def test_extract_returns_empty_on_garbage(payload):
    assert extract_entitled_services(payload) == set()


# ---------------------------------------------------------------------------
# Observed `prd` values — pinned against a real ZIdentity token
# ---------------------------------------------------------------------------

# The exact `service-info[].prd` set emitted by a live ZIdentity tenant entitled
# to ZIA, ZCC, ZDX, Cloud Connector, ZIdentity and Z-Insights. Every one of these
# products answered its API successfully with that same bearer token, so all six
# must survive the filter.
OBSERVED_PRD_VALUES = ["CLOUD_CONNECTOR", "ZCC", "ZDX", "ZIA", "ZIAM", "ZINSIGHTS"]


@pytest.mark.parametrize(
    ("prd", "service"),
    [("CLOUD_CONNECTOR", "ztw"), ("ZIAM", "zid"), ("ZINSIGHTS", "zins")],
)
def test_observed_prd_aliases_are_mapped(prd, service):
    assert PRD_TO_SERVICE[prd] == service
    assert extract_entitled_services({"service-info": [{"prd": prd}]}) == {service}


def test_observed_token_maps_every_prd_value():
    payload = {"service-info": [{"prd": p} for p in OBSERVED_PRD_VALUES]}
    assert extract_entitled_services(payload) == {"ztw", "zcc", "zdx", "zia", "zid", "zins"}


def test_observed_token_does_not_strip_entitled_tools():
    # Regression: CLOUD_CONNECTOR / ZIAM / ZINSIGHTS were unmapped, so ztw, zid
    # and zins were downscoped away despite the tenant being entitled to them.
    token = _make_token({"service-info": [{"prd": p} for p in OBSERVED_PRD_VALUES]})
    available = {"zia", "zcc", "zdx", "ztw", "zid", "zins", "zpa"}
    allowed, status = apply_entitlement_filter(available, token_provider=lambda: (token, None))

    assert allowed == {"zia", "zcc", "zdx", "ztw", "zid", "zins"}
    # ZPA is genuinely absent from the token and must still be removed.
    assert "zpa" not in allowed
    assert "removed 1 service" in status
    assert "unmapped" not in status


# ---------------------------------------------------------------------------
# Unmapped `prd` reporting — a mapping gap must never be silent
# ---------------------------------------------------------------------------


def test_extract_warns_about_unmapped_prd_values(caplog):
    payload = {"service-info": [{"prd": "ZIA"}, {"prd": "BRAND_NEW_PRODUCT"}]}
    with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security.entitlements"):
        assert extract_entitled_services(payload) == {"zia"}

    assert "BRAND_NEW_PRODUCT" in caplog.text
    assert "no PRD_TO_SERVICE mapping" in caplog.text


def test_extract_does_not_warn_when_everything_maps(caplog):
    payload = {"service-info": [{"prd": "ZIA"}, {"prd": "ZPA"}]}
    with caplog.at_level(logging.WARNING, logger="zscaler_mcp.security.entitlements"):
        extract_entitled_services(payload)

    assert caplog.text == ""


def test_filter_reports_unmapped_prd_values_in_status():
    token = _make_token({"service-info": [{"prd": "ZIA"}, {"prd": "BRAND_NEW_PRODUCT"}]})
    allowed, status = apply_entitlement_filter({"zia", "zpa"}, token_provider=lambda: (token, None))

    assert allowed == {"zia"}
    assert "unmapped prd values ignored: ['BRAND_NEW_PRODUCT']" in status


def test_filter_skip_message_names_unmapped_values():
    # Nothing in the token maps: the operator must see WHY, not just "no
    # recognizable service-info entries", which reads like a malformed token.
    token = _make_token({"service-info": [{"prd": "MYSTERY_ONE"}, {"prd": "MYSTERY_TWO"}]})
    allowed, status = apply_entitlement_filter({"zia"}, token_provider=lambda: (token, None))

    assert allowed is None
    assert "unmapped: ['MYSTERY_ONE', 'MYSTERY_TWO']" in status


def test_unmapped_values_are_deduplicated_and_sorted():
    payload = {
        "service-info": [
            {"prd": "ZETA_PRODUCT"},
            {"prd": "ALPHA_PRODUCT"},
            {"prd": "ZETA_PRODUCT"},
        ]
    }
    _, status = apply_entitlement_filter(
        {"zia"}, token_provider=lambda: (_make_token(payload), None)
    )
    assert "['ALPHA_PRODUCT', 'ZETA_PRODUCT']" in status


def test_blank_prd_values_are_neither_mapped_nor_reported():
    payload = {"service-info": [{"prd": "ZIA"}, {"prd": "   "}]}
    allowed, status = apply_entitlement_filter(
        {"zia"}, token_provider=lambda: (_make_token(payload), None)
    )
    assert allowed == {"zia"}
    assert "unmapped" not in status


# ---------------------------------------------------------------------------
# apply_entitlement_filter — the downscope decision
# ---------------------------------------------------------------------------


def test_filter_intersects_available_with_entitled():
    token = _make_token({"service-info": [{"prd": "ZPA"}]})
    allowed, status = apply_entitlement_filter(
        {"zpa", "zia", "zdx"}, token_provider=lambda: (token, None)
    )
    assert allowed == {"zpa"}
    assert "kept 1 service" in status
    assert "removed 2 service" in status


def test_filter_keeps_all_when_fully_entitled():
    token = _make_token({"service-info": [{"prd": "ZPA"}, {"prd": "ZIA"}]})
    allowed, status = apply_entitlement_filter({"zpa", "zia"}, token_provider=lambda: (token, None))
    assert allowed == {"zpa", "zia"}
    assert "removed" not in status


def test_filter_skips_on_token_error():
    allowed, status = apply_entitlement_filter({"zpa"}, token_provider=lambda: (None, "bad creds"))
    assert allowed is None
    assert "skipped" in status and "bad creds" in status


def test_filter_skips_on_undecodable_token():
    allowed, status = apply_entitlement_filter({"zpa"}, token_provider=lambda: ("not.a.jwt", None))
    # "not.a.jwt" is 3 parts but the middle isn't valid base64 JSON.
    assert allowed is None
    assert "did not decode" in status


def test_filter_skips_when_no_service_info():
    token = _make_token({"sub": "abc"})  # no service-info claim
    allowed, status = apply_entitlement_filter({"zpa"}, token_provider=lambda: (token, None))
    assert allowed is None
    assert "no recognizable service-info" in status


def test_filter_skips_when_provider_raises():
    def boom():
        raise RuntimeError("network down")

    allowed, status = apply_entitlement_filter({"zpa"}, token_provider=boom)
    assert allowed is None
    assert "skipped" in status


def test_filter_intersection_never_invents_services():
    # Token is entitled to a product we have no tools for — result is empty,
    # not the entitled set.
    token = _make_token({"service-info": [{"prd": "ZDX"}]})
    allowed, _ = apply_entitlement_filter({"zpa"}, token_provider=lambda: (token, None))
    assert allowed == set()
