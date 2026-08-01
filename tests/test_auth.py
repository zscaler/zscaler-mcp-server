"""Tests for the MCP client auth layer (security/auth.py)."""

from __future__ import annotations

import base64

import pytest

from zscaler_mcp.security import auth

# ---------------------------------------------------------------------------
# API key provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_accepts_correct_key():
    p = auth.APIKeyAuthProvider("sk-secret")
    ok, err = await p.authenticate("Bearer sk-secret")
    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_api_key_rejects_wrong_key():
    p = auth.APIKeyAuthProvider("sk-secret")
    ok, err = await p.authenticate("Bearer wrong")
    assert ok is False
    assert err == "Invalid API key"


@pytest.mark.asyncio
async def test_api_key_rejects_missing_header():
    p = auth.APIKeyAuthProvider("sk-secret")
    ok, err = await p.authenticate("")
    assert ok is False


def test_api_key_rejects_empty_config():
    with pytest.raises(ValueError):
        auth.APIKeyAuthProvider("   ")


# ---------------------------------------------------------------------------
# Zscaler provider (no network — patch fetch_oneapi_token)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zscaler_basic_auth_validates(monkeypatch):
    p = auth.ZscalerAuthProvider("acme")
    monkeypatch.setattr(auth, "fetch_oneapi_token", lambda **kw: ("tok-123", None))
    creds = base64.b64encode(b"client:secret").decode()
    ok, err = await p.authenticate(f"Basic {creds}")
    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_zscaler_header_pair_validates(monkeypatch):
    p = auth.ZscalerAuthProvider("acme")
    monkeypatch.setattr(auth, "fetch_oneapi_token", lambda **kw: ("tok-123", None))
    headers = [
        (b"x-zscaler-client-id", b"client"),
        (b"x-zscaler-client-secret", b"secret"),
    ]
    ok, err = await p.authenticate("", headers)
    assert ok is True


@pytest.mark.asyncio
async def test_zscaler_caches_after_first_validation(monkeypatch):
    p = auth.ZscalerAuthProvider("acme")
    calls = {"n": 0}

    def fake_fetch(**kw):
        calls["n"] += 1
        return "tok", None

    monkeypatch.setattr(auth, "fetch_oneapi_token", fake_fetch)
    creds = base64.b64encode(b"client:secret").decode()
    await p.authenticate(f"Basic {creds}")
    await p.authenticate(f"Basic {creds}")
    assert calls["n"] == 1  # second call served from cache


@pytest.mark.asyncio
async def test_zscaler_rejects_bad_credentials(monkeypatch):
    p = auth.ZscalerAuthProvider("acme")
    monkeypatch.setattr(
        auth, "fetch_oneapi_token", lambda **kw: (None, "Invalid OneAPI credentials")
    )
    creds = base64.b64encode(b"client:bad").decode()
    ok, err = await p.authenticate(f"Basic {creds}")
    assert ok is False
    assert "Invalid OneAPI credentials" in err


@pytest.mark.asyncio
async def test_zscaler_requires_credentials():
    p = auth.ZscalerAuthProvider("acme")
    ok, err = await p.authenticate("")
    assert ok is False
    assert "requires credentials" in err


def test_zscaler_scheme_is_basic():
    assert auth.ZscalerAuthProvider("acme").scheme == "Basic"


# ---------------------------------------------------------------------------
# Config / factory
# ---------------------------------------------------------------------------


def test_auth_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "false")
    assert auth._read_auth_config() is None


def test_auth_autodetects_zscaler(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("ZSCALER_MCP_AUTH_MODE", raising=False)
    monkeypatch.delenv("ZSCALER_MCP_AUTH_JWKS_URI", raising=False)
    monkeypatch.delenv("ZSCALER_MCP_AUTH_API_KEY", raising=False)
    monkeypatch.setenv("ZSCALER_VANITY_DOMAIN", "acme")
    cfg = auth._read_auth_config()
    assert cfg["mode"] == "zscaler"


def test_apply_auth_middleware_noop_for_stdio():
    sentinel = object()
    assert auth.apply_auth_middleware(sentinel, "stdio") is sentinel


def test_apply_auth_middleware_disabled_passthrough(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "false")
    sentinel = object()
    assert auth.apply_auth_middleware(sentinel, "streamable-http") is sentinel


def test_apply_auth_middleware_wraps_when_enabled(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "api-key")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "sk-x")
    sentinel = object()
    wrapped = auth.apply_auth_middleware(sentinel, "streamable-http")
    assert isinstance(wrapped, auth.AuthMiddleware)
    assert wrapped.app is sentinel


# ---------------------------------------------------------------------------
# Mode parity: none / jwt / api-key / zscaler / oidc (the full v1 set)
# ---------------------------------------------------------------------------


def test_mode_none_disables_auth(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_AUTH_ENABLED", raising=False)
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "none")
    assert auth._read_auth_config() is None
    sentinel = object()
    assert auth.apply_auth_middleware(sentinel, "streamable-http") is sentinel


@pytest.mark.parametrize("mode", ["oidc", "oidcproxy", "oauth-proxy"])
def test_oidc_mode_bypasses_the_asgi_middleware(monkeypatch, mode):
    """OIDC is enforced by the SDK, so the middleware must pass the app through.

    Wrapping it here as well would authenticate every request twice, against two
    different notions of a valid token.
    """
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", mode)
    sentinel = object()
    assert auth.apply_auth_middleware(sentinel, "streamable-http") is sentinel


def test_unknown_mode_lists_all_supported(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "bogus")
    with pytest.raises(ValueError) as exc:
        auth._create_provider(auth._read_auth_config())
    msg = str(exc.value)
    for mode in ("none", "jwt", "zscaler", "api-key", "oidc"):
        assert mode in msg


# ---------------------------------------------------------------------------
# OIDC: this server as an OAuth 2.0 protected resource (RFC 9728)
#
# The IdP is the authorization server; we publish metadata naming it and verify
# the tokens it issues. Getting this wrong yields either a server that advertises
# a discovery document clients cannot use, or one that accepts tokens minted for
# some other application in the same tenant — so the settings are pinned here.
# ---------------------------------------------------------------------------

_OIDC_VARS = (
    "OIDCPROXY_CONFIG_URL",
    "OIDCPROXY_CLIENT_ID",
    "OIDCPROXY_CLIENT_SECRET",
    "OIDCPROXY_BASE_URL",
    "OIDCPROXY_AUDIENCE",
    "OIDCPROXY_REQUIRED_SCOPES",
)

_DISCOVERED = {
    "issuer": "https://login.microsoftonline.com/tenant-id/v2.0",
    "jwks_uri": "https://login.microsoftonline.com/tenant-id/discovery/v2.0/keys",
}


@pytest.fixture
def oidc_env(monkeypatch):
    """A configured OIDC mode with the IdP's discovery document stubbed out."""
    for var in _OIDC_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "oidc")
    monkeypatch.setenv(
        "OIDCPROXY_CONFIG_URL",
        "https://login.microsoftonline.com/tenant-id/v2.0/.well-known/openid-configuration",
    )
    monkeypatch.setenv("OIDCPROXY_BASE_URL", "https://mcp.example.com")
    monkeypatch.setenv("OIDCPROXY_CLIENT_ID", "client-abc")
    monkeypatch.setattr(auth, "_discover_oidc_endpoints", lambda _url: dict(_DISCOVERED))
    return monkeypatch


def test_resolve_oidc_auth_is_none_for_other_modes(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "api-key")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "sk-x")
    assert auth.resolve_oidc_auth() is None


def test_resolve_oidc_auth_is_none_when_auth_is_disabled(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "false")
    assert auth.resolve_oidc_auth() is None


def test_misconfiguration_exits_rather_than_serving_unauthenticated(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "oidc")
    for var in _OIDC_VARS:
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(SystemExit):
        auth.resolve_oidc_auth()


def test_required_config_is_named_in_the_error(monkeypatch):
    for var in _OIDC_VARS:
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError) as exc:
        auth.build_oidc_auth_kwargs()
    assert "OIDCPROXY_CONFIG_URL" in str(exc.value)
    assert "OIDCPROXY_BASE_URL" in str(exc.value)


def test_a_client_secret_is_no_longer_required(oidc_env):
    """Verifying a signature needs the IdP's public keys, not a credential of ours.

    Pinned because the secret used to be mandatory: leaving the old check in place
    would keep demanding a value that is now unused.
    """
    oidc_env.delenv("OIDCPROXY_CLIENT_SECRET", raising=False)
    assert auth.build_oidc_auth_kwargs()["auth"] is not None


def test_an_audience_is_mandatory(oidc_env):
    """Without one, any token from the same IdP tenant would be accepted.

    Entra ID puts the client id in ``aud``, so ``OIDCPROXY_CLIENT_ID`` defaults it;
    with neither set, refuse to start rather than authenticate the wrong callers.
    """
    oidc_env.delenv("OIDCPROXY_CLIENT_ID", raising=False)
    with pytest.raises(ValueError) as exc:
        auth.build_oidc_auth_kwargs()
    assert "OIDCPROXY_AUDIENCE" in str(exc.value)


def test_the_audience_defaults_to_the_client_id(oidc_env):
    verifier = auth.build_oidc_auth_kwargs()["token_verifier"]
    assert verifier._provider._audience == "client-abc"


def test_an_explicit_audience_wins(oidc_env):
    oidc_env.setenv("OIDCPROXY_AUDIENCE", "api://zscaler-mcp")
    verifier = auth.build_oidc_auth_kwargs()["token_verifier"]
    assert verifier._provider._audience == "api://zscaler-mcp"


def test_it_advertises_the_idp_as_the_authorization_server(oidc_env):
    """The inverse of the proxy design, and the whole point of the change.

    A proxy advertised *itself* as issuer so clients would come to it. As a
    resource server we name the IdP, so the client goes there directly and no OAuth
    endpoint has to be served from this process.
    """
    settings = auth.build_oidc_auth_kwargs()["auth"]
    assert str(settings.issuer_url).rstrip("/") == _DISCOVERED["issuer"]
    assert str(settings.resource_server_url).rstrip("/") == "https://mcp.example.com"


def test_it_never_claims_to_be_an_authorization_server(oidc_env):
    """Setting ``auth_server_provider`` would mount /authorize, /token, /register.

    We implement none of those, so the SDK would serve routes that fail — and it
    would also derive its own verifier, displacing ours.
    """
    kwargs = auth.build_oidc_auth_kwargs()
    assert set(kwargs) == {"auth", "token_verifier"}


def test_the_issuer_comes_from_discovery_not_the_config_url(oidc_env):
    """Entra ID's issuer is not a prefix of its discovery URL.

    Deriving it by trimming ``/.well-known/openid-configuration`` yields
    ``.../v2.0`` here by luck, but the general case fails, and the symptom is every
    token rejected for issuer mismatch. So the document is the source of truth.
    """
    oidc_env.setattr(
        auth,
        "_discover_oidc_endpoints",
        lambda _url: {"issuer": "https://actual-issuer.example", "jwks_uri": "https://k/keys"},
    )
    settings = auth.build_oidc_auth_kwargs()["auth"]
    assert str(settings.issuer_url).rstrip("/") == "https://actual-issuer.example"


def test_required_scopes_are_forwarded(oidc_env):
    oidc_env.setenv("OIDCPROXY_REQUIRED_SCOPES", "openid, zscaler.read")
    assert auth.build_oidc_auth_kwargs()["auth"].required_scopes == ["openid", "zscaler.read"]


def test_scopes_are_omitted_when_none_are_required(oidc_env):
    assert not auth.build_oidc_auth_kwargs()["auth"].required_scopes


def test_the_kwargs_are_accepted_by_a_real_mcpserver(oidc_env):
    """Let the real constructor validate the combination.

    Asserting kwarg names by hand would still pass if ``MCPServer`` tightened its
    validation, and this configuration is the one least likely to be exercised
    locally before a deploy.
    """
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("test", **auth.build_oidc_auth_kwargs())
    assert server.settings.auth is not None


def test_the_metadata_route_is_actually_mounted(oidc_env):
    """The end of the chain: RFC 9728 metadata on the wire.

    Everything above only checks what we hand the SDK. This asserts the SDK does
    mount ``/.well-known/oauth-protected-resource`` from it — the document the
    client reads to find the IdP. Without it the mode is inert.
    """
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("test", **auth.build_oidc_auth_kwargs())
    app = server.streamable_http_app(streamable_http_path="/mcp", host="127.0.0.1")
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/.well-known/oauth-protected-resource" in paths


class TestTokenVerification:
    """The verifier answers with a principal, and only for a valid token."""

    def _verifier(self, *, ok=True, claims=None):
        class _Provider:
            _audience = "client-abc"
            _jwt = type(
                "_Jwt", (), {"decode": staticmethod(lambda _t, **_k: claims or {"sub": "u1"})}
            )

            async def authenticate(self, _authorization):
                return (True, None) if ok else (False, "Token has expired")

        return auth._JWKSTokenVerifier(_Provider())

    async def test_a_rejected_token_yields_no_principal(self):
        assert await self._verifier(ok=False).verify_token("bad") is None

    async def test_claims_become_the_access_token(self):
        token = await self._verifier(
            claims={"sub": "user-1", "exp": 999, "scp": "zscaler.read zscaler.write"}
        ).verify_token("good")
        assert token.subject == "user-1"
        assert token.expires_at == 999
        assert token.scopes == ["zscaler.read", "zscaler.write"]

    async def test_space_delimited_and_list_scopes_both_work(self):
        """Entra ID sends ``scp`` as a space-delimited string; others send a list."""
        as_list = await self._verifier(claims={"scope": ["a", "b"]}).verify_token("good")
        as_string = await self._verifier(claims={"scope": "a b"}).verify_token("good")
        assert as_list.scopes == as_string.scopes == ["a", "b"]


# ---------------------------------------------------------------------------
# Provider registry (used by the entitlement filter's cache-first path)
# ---------------------------------------------------------------------------


def test_zscaler_provider_self_registers():
    before = len(auth.get_registered_zscaler_providers())
    p = auth.ZscalerAuthProvider("acme-reg-test")
    after = auth.get_registered_zscaler_providers()
    assert len(after) == before + 1
    assert p in after


@pytest.mark.asyncio
async def test_get_cached_token_returns_validated_token(monkeypatch):
    p = auth.ZscalerAuthProvider("acme")
    monkeypatch.setattr(auth, "fetch_oneapi_token", lambda **kw: ("cached-tok", None))
    creds = base64.b64encode(b"client:secret").decode()
    await p.authenticate(f"Basic {creds}")
    assert p.get_cached_token("client", "secret") == "cached-tok"


def test_get_cached_token_none_when_uncached():
    p = auth.ZscalerAuthProvider("acme")
    assert p.get_cached_token("nope", "nope") is None
