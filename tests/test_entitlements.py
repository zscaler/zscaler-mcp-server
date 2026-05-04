"""Tests for the OneAPI entitlement-driven toolset filter."""

from __future__ import annotations

import base64
import json
from typing import Optional, Tuple

import pytest

from zscaler_mcp.common.entitlements import (
    apply_entitlement_filter,
    decode_oneapi_token,
    extract_entitled_services,
    obtain_oneapi_token,
)
from zscaler_mcp.common.toolsets import META_TOOLSET_ID, TOOLSETS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_jwt(payload: dict) -> str:
    """Build a syntactically-valid (unsigned) JWT carrying the given payload."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=")
    body_bytes = json.dumps(payload).encode("utf-8")
    body = base64.urlsafe_b64encode(body_bytes).rstrip(b"=")
    sig = base64.urlsafe_b64encode(b"signature").rstrip(b"=")
    return f"{header.decode()}.{body.decode()}.{sig.decode()}"


def _stub_token(token: Optional[str], error: Optional[str] = None):
    """Build a callable usable as ``token_provider=`` in tests."""

    def _provider() -> Tuple[Optional[str], Optional[str]]:
        return token, error

    return _provider


# ---------------------------------------------------------------------------
# Override the global "filter disabled" fixture for THIS module so we can
# exercise the filter end-to-end. The filter is still cheap because every
# test injects a token_provider stub — no network calls.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _enable_filter_for_this_module(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER", raising=False)
    monkeypatch.setenv("ZSCALER_CLIENT_ID", "dummy-id")
    monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "dummy-secret")
    monkeypatch.setenv("ZSCALER_VANITY_DOMAIN", "dummy")
    monkeypatch.setenv("ZSCALER_CUSTOMER_ID", "dummy")


# ---------------------------------------------------------------------------
# decode_oneapi_token
# ---------------------------------------------------------------------------


class TestDecodeOneapiToken:
    def test_decodes_a_valid_token(self):
        payload = {"service-info": [{"prd": "ZIA"}]}
        token = _make_jwt(payload)
        assert decode_oneapi_token(token) == payload

    def test_pads_unpadded_base64url(self):
        payload = {"x": "y"}  # short payload → unpadded base64url
        token = _make_jwt(payload)
        assert decode_oneapi_token(token) == payload

    def test_rejects_non_three_part_token(self):
        assert decode_oneapi_token("only.two") is None
        assert decode_oneapi_token("a.b.c.d") is None

    def test_rejects_garbage_payload(self):
        assert decode_oneapi_token("aaa.@@@.bbb") is None

    def test_rejects_empty_or_none(self):
        assert decode_oneapi_token("") is None
        assert decode_oneapi_token(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# extract_entitled_services
# ---------------------------------------------------------------------------


class TestExtractEntitledServices:
    def test_extracts_known_products(self):
        payload = {
            "service-info": [
                {"prd": "ZIA"},
                {"prd": "ZPA"},
                {"prd": "ZCC"},
            ]
        }
        assert extract_entitled_services(payload) == {"zia", "zpa", "zcc"}

    def test_normalises_case(self):
        payload = {"service-info": [{"prd": "  zia  "}]}
        assert extract_entitled_services(payload) == {"zia"}

    def test_skips_unknown_products(self):
        payload = {"service-info": [{"prd": "MYSTERY_PRODUCT"}, {"prd": "ZPA"}]}
        assert extract_entitled_services(payload) == {"zpa"}

    def test_handles_missing_service_info(self):
        assert extract_entitled_services({}) == set()

    def test_handles_camelcase_alias(self):
        payload = {"serviceInfo": [{"prd": "ZDX"}]}
        assert extract_entitled_services(payload) == {"zdx"}

    def test_skips_non_dict_entries(self):
        payload = {"service-info": [None, "ZIA", {"prd": "ZIA"}]}
        assert extract_entitled_services(payload) == {"zia"}

    def test_zidentity_aliases_resolve_to_zid(self):
        for alias in ("ZIDENTITY", "ZID", "IDENTITY"):
            payload = {"service-info": [{"prd": alias}]}
            assert extract_entitled_services(payload) == {"zid"}


# ---------------------------------------------------------------------------
# apply_entitlement_filter — pure logic
# ---------------------------------------------------------------------------


class TestApplyEntitlementFilterPure:
    def test_intersects_selection_with_entitlements(self):
        token = _make_jwt({"service-info": [{"prd": "ZIA"}]})
        selection = {"zia_url_filtering", "zpa_app_segments", "zdx"}
        filtered, status = apply_entitlement_filter(selection, token_provider=_stub_token(token))
        # Only ZIA-mapped toolsets survive (plus meta).
        assert "zia_url_filtering" in filtered
        assert "zpa_app_segments" not in filtered
        assert "zdx" not in filtered
        assert META_TOOLSET_ID in filtered
        assert "entitlement filter applied" in status

    def test_when_selection_is_none_uses_full_catalog_as_baseline(self):
        token = _make_jwt({"service-info": [{"prd": "ZPA"}]})
        filtered, _ = apply_entitlement_filter(None, token_provider=_stub_token(token))
        # Every surviving toolset must be a ZPA toolset (or meta).
        for tsid in filtered:
            ts = TOOLSETS.get(tsid)
            assert ts is not None
            assert ts.service in ("zpa", "meta")

    def test_meta_always_survives_even_with_zero_entitlements(self):
        token = _make_jwt({"service-info": [{"prd": "MYSTERY"}]})
        filtered, status = apply_entitlement_filter(
            {"zia_url_filtering"}, token_provider=_stub_token(token)
        )
        # MYSTERY → no entitlements → filter SKIPS (returns selection
        # unchanged). The 'no recognizable entries' branch guards
        # against the worst case where we'd otherwise wipe the whole
        # toolset list.
        assert filtered == {"zia_url_filtering"}
        assert "no recognizable" in status

    def test_token_fetch_failure_skips_filter(self):
        filtered, status = apply_entitlement_filter(
            {"zia_url_filtering"},
            token_provider=_stub_token(None, error="Missing creds"),
        )
        assert filtered == {"zia_url_filtering"}
        assert "skipped" in status
        assert "Missing creds" in status

    def test_undecodable_token_skips_filter(self):
        filtered, status = apply_entitlement_filter(
            {"zia_url_filtering"}, token_provider=_stub_token("not.a.jwt")
        )
        assert filtered == {"zia_url_filtering"}
        assert "did not decode" in status

    def test_provider_exception_skips_filter(self):
        def _boom():
            raise RuntimeError("kaboom")

        filtered, status = apply_entitlement_filter({"zia_url_filtering"}, token_provider=_boom)
        assert filtered == {"zia_url_filtering"}
        assert "skipped" in status


# ---------------------------------------------------------------------------
# obtain_oneapi_token — cache-first / cold-fetch routing
# ---------------------------------------------------------------------------


class TestObtainOneapiToken:
    def test_returns_cached_token_when_available(self, monkeypatch):
        from zscaler_mcp import auth as auth_mod

        # Build a real ZscalerAuthProvider but pre-seed its cache, so we
        # can verify the cache-first path skips the network call.
        provider = auth_mod.ZscalerAuthProvider(vanity_domain="dummy")
        with provider._cache_lock:
            provider._cache[provider._credential_hash("dummy-id", "dummy-secret")] = (
                9999999999.0,
                "cached-token-xyz",
            )

        # If fetch_oneapi_token is called we want the test to fail loudly.
        monkeypatch.setattr(
            auth_mod,
            "fetch_oneapi_token",
            lambda **kw: pytest.fail("cold fetch should not run when cache is hot"),
        )

        token, error = obtain_oneapi_token()
        assert error is None
        assert token == "cached-token-xyz"

    def test_falls_back_to_cold_fetch_when_cache_empty(self, monkeypatch):
        from zscaler_mcp import auth as auth_mod

        # Make sure no leftover providers are registered from earlier tests.
        with auth_mod._zscaler_providers_lock:
            auth_mod._zscaler_providers.clear()

        monkeypatch.setattr(
            auth_mod,
            "fetch_oneapi_token",
            lambda **kw: ("freshly-minted", None),
        )

        token, error = obtain_oneapi_token()
        assert error is None
        assert token == "freshly-minted"

    def test_returns_error_when_creds_missing(self, monkeypatch):
        monkeypatch.delenv("ZSCALER_CLIENT_ID", raising=False)
        token, error = obtain_oneapi_token()
        assert token is None
        assert "Missing OneAPI credentials" in error


# ---------------------------------------------------------------------------
# Server-level integration: opt-out flag and end-to-end intersection.
# ---------------------------------------------------------------------------


class TestServerIntegration:
    def test_opt_out_flag_skips_filter(self, monkeypatch):
        from zscaler_mcp.server import ZscalerMCPServer

        # Stub the apply call to verify it isn't invoked.
        called = {"n": 0}

        def _spy(*a, **kw):
            called["n"] += 1
            return None, None

        monkeypatch.setattr("zscaler_mcp.common.entitlements.apply_entitlement_filter", _spy)

        server = ZscalerMCPServer(disable_entitlement_filter=True)
        assert server.disable_entitlement_filter is True
        assert called["n"] == 0
        # Selection is unchanged from the no-filter baseline.
        assert META_TOOLSET_ID in server.selected_toolsets

    def test_env_opt_out_skips_filter(self, monkeypatch):
        from zscaler_mcp.server import ZscalerMCPServer

        monkeypatch.setenv("ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER", "true")
        called = {"n": 0}

        def _spy(*a, **kw):
            called["n"] += 1
            return None, None

        monkeypatch.setattr("zscaler_mcp.common.entitlements.apply_entitlement_filter", _spy)

        server = ZscalerMCPServer()
        assert server.disable_entitlement_filter is True
        assert called["n"] == 0

    def test_filter_intersects_with_explicit_toolsets(self, monkeypatch):
        from zscaler_mcp.server import ZscalerMCPServer

        token = _make_jwt({"service-info": [{"prd": "ZIA"}]})

        # Replace obtain_oneapi_token so the filter doesn't hit the network.
        import zscaler_mcp.common.entitlements as ent_mod

        monkeypatch.setattr(
            ent_mod,
            "obtain_oneapi_token",
            lambda **kw: (token, None),
        )

        server = ZscalerMCPServer(
            toolsets={"zia_url_filtering", "zpa_app_segments"},
        )

        # ZPA toolset stripped because token only entitles ZIA.
        assert "zia_url_filtering" in server.selected_toolsets
        assert "zpa_app_segments" not in server.selected_toolsets
        assert META_TOOLSET_ID in server.selected_toolsets

    def test_filter_failure_is_non_fatal(self, monkeypatch):
        import zscaler_mcp.common.entitlements as ent_mod
        from zscaler_mcp.server import ZscalerMCPServer

        monkeypatch.setattr(
            ent_mod,
            "obtain_oneapi_token",
            lambda **kw: (None, "Cannot reach OneAPI auth endpoint"),
        )

        # Server must initialise even though the filter failed.
        server = ZscalerMCPServer(toolsets={"zia_url_filtering"})
        assert "zia_url_filtering" in server.selected_toolsets

    def test_filter_preserves_meta_toolset_when_token_entitles_only_unrelated_products(
        self, monkeypatch
    ):
        import zscaler_mcp.common.entitlements as ent_mod
        from zscaler_mcp.server import ZscalerMCPServer

        # Token entitles ZPA only, but the user only asked for ZIA toolsets.
        # Result: nothing user-requested survives, but META_TOOLSET_ID
        # is force-added.
        token = _make_jwt({"service-info": [{"prd": "ZPA"}]})
        monkeypatch.setattr(
            ent_mod,
            "obtain_oneapi_token",
            lambda **kw: (token, None),
        )

        server = ZscalerMCPServer(toolsets={"zia_url_filtering"})
        assert server.selected_toolsets == {META_TOOLSET_ID}
