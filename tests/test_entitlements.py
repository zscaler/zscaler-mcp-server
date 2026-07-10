"""Tests for OneAPI product-entitlement downscoping."""

from __future__ import annotations

import base64
import json

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
