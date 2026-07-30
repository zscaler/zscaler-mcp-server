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
# Mode parity: none / jwt / api-key / zscaler / oidcproxy (the full v1 set)
# ---------------------------------------------------------------------------


def test_mode_none_disables_auth(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_AUTH_ENABLED", raising=False)
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "none")
    assert auth._read_auth_config() is None
    sentinel = object()
    assert auth.apply_auth_middleware(sentinel, "streamable-http") is sentinel


def test_mode_oidcproxy_bypasses_asgi_middleware(monkeypatch):
    # In oidcproxy mode, FastMCP(auth=...) handles auth, so the ASGI middleware
    # path must pass the app through untouched.
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "oidcproxy")
    sentinel = object()
    assert auth.apply_auth_middleware(sentinel, "streamable-http") is sentinel


def test_unknown_mode_lists_all_supported(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "bogus")
    with pytest.raises(ValueError) as exc:
        auth._create_provider(auth._read_auth_config())
    msg = str(exc.value)
    for mode in ("none", "jwt", "zscaler", "api-key", "oidcproxy"):
        assert mode in msg


# ---------------------------------------------------------------------------
# resolve_fastmcp_auth — env-var oidcproxy builder
# ---------------------------------------------------------------------------


def test_resolve_fastmcp_auth_none_for_non_oidcproxy(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "api-key")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "sk-x")
    assert auth.resolve_fastmcp_auth() is None


def test_resolve_fastmcp_auth_none_when_disabled(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "false")
    assert auth.resolve_fastmcp_auth() is None


def test_resolve_fastmcp_auth_oidcproxy_misconfig_exits(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "oidcproxy")
    for var in (
        "OIDCPROXY_CONFIG_URL",
        "OIDCPROXY_CLIENT_ID",
        "OIDCPROXY_CLIENT_SECRET",
        "OIDCPROXY_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(SystemExit):
        auth.resolve_fastmcp_auth()


def test_build_oidcproxy_provider_requires_config(monkeypatch):
    for var in (
        "OIDCPROXY_CONFIG_URL",
        "OIDCPROXY_CLIENT_ID",
        "OIDCPROXY_CLIENT_SECRET",
        "OIDCPROXY_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError) as exc:
        auth.build_oidcproxy_provider()
    assert "OIDCPROXY_CONFIG_URL" in str(exc.value)


def test_missing_config_is_reported_before_missing_package(monkeypatch):
    """A misconfigured server must be told what config it lacks, not what package.

    ``fastmcp`` is an optional extra, so the import inside the builder can fail
    for a reason that has nothing to do with the operator's mistake. Validating
    config first keeps the error actionable on installs without the extra.
    """
    for var in (
        "OIDCPROXY_CONFIG_URL",
        "OIDCPROXY_CLIENT_ID",
        "OIDCPROXY_CLIENT_SECRET",
        "OIDCPROXY_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError):  # NOT ImportError
        auth.build_oidcproxy_provider()


# ---------------------------------------------------------------------------
# mcpserver_auth_kwargs — the FastMCP-provider -> MCPServer bridge
#
# ``MCPServer`` split FastMCP's single ``auth=<provider>`` parameter into
# declarative ``AuthSettings`` for the advertised OAuth metadata plus a
# behavioural provider. These tests pin the translation, since getting it wrong
# yields a server that either advertises a discovery document pointing nowhere or
# refuses to start.
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Stands in for a fastmcp ``OIDCProxy``.

    Only the attributes the bridge reads are modelled. A real ``OIDCProxy`` also
    satisfies ``mcp``'s authorization-server protocol, which is why the bridge can
    pass it through unchanged — asserting identity below is what pins that.
    """

    def __init__(self, **attrs):
        self.base_url = attrs.pop("base_url", "https://mcp.example.com")
        for key, value in attrs.items():
            setattr(self, key, value)


def test_auth_bridge_sets_settings_and_provider():
    kwargs = auth.mcpserver_auth_kwargs(_FakeProvider())
    assert set(kwargs) == {"auth", "auth_server_provider"}


def test_auth_bridge_passes_the_provider_through_unchanged():
    provider = _FakeProvider()
    assert auth.mcpserver_auth_kwargs(provider)["auth_server_provider"] is provider


def test_auth_bridge_does_not_also_set_a_token_verifier():
    """``MCPServer`` rejects provider and verifier together.

    Given a provider it derives the verifier itself, so setting both would make
    the server refuse to start — a startup crash reachable only in oidcproxy mode,
    which is exactly the configuration least likely to be exercised locally.
    """
    assert "token_verifier" not in auth.mcpserver_auth_kwargs(_FakeProvider())


def test_bridged_kwargs_are_accepted_by_mcpserver():
    """The real constructor validates this combination — let it do the asserting.

    Hand-checking the kwarg names would still pass if ``MCPServer`` tightened its
    validation, so the test builds an actual server instead.
    """
    from mcp.server.mcpserver import MCPServer

    kwargs = auth.mcpserver_auth_kwargs(_FakeProvider())
    server = MCPServer("test", **kwargs)
    assert server.settings.auth is not None


def test_auth_bridge_defaults_issuer_to_this_server():
    """An OAuth *proxy* is the issuer clients talk to, not the upstream IdP.

    The proxy fronts /authorize, /token and /register and forwards upstream, so
    advertising the IdP as issuer would send clients past the proxy entirely.
    """
    kwargs = auth.mcpserver_auth_kwargs(_FakeProvider(base_url="https://mcp.example.com"))
    settings = kwargs["auth"]
    assert str(settings.issuer_url).rstrip("/") == "https://mcp.example.com"
    assert str(settings.resource_server_url).rstrip("/") == "https://mcp.example.com"


def test_auth_bridge_honours_explicit_issuer_and_resource_urls():
    kwargs = auth.mcpserver_auth_kwargs(
        _FakeProvider(
            base_url="https://mcp.example.com",
            issuer_url="https://issuer.example.com",
            resource_base_url="https://resource.example.com",
        )
    )
    settings = kwargs["auth"]
    assert str(settings.issuer_url).rstrip("/") == "https://issuer.example.com"
    assert str(settings.resource_server_url).rstrip("/") == "https://resource.example.com"


def test_auth_bridge_forwards_required_scopes():
    kwargs = auth.mcpserver_auth_kwargs(_FakeProvider(required_scopes=("openid", "zscaler.read")))
    assert kwargs["auth"].required_scopes == ["openid", "zscaler.read"]


def test_auth_bridge_omits_scopes_when_none_required():
    kwargs = auth.mcpserver_auth_kwargs(_FakeProvider(required_scopes=None))
    assert not kwargs["auth"].required_scopes


def test_auth_bridge_refuses_a_provider_without_a_base_url():
    """No base_url means no advertisable issuer — refuse rather than mislead.

    Starting up anyway would serve an OAuth discovery document pointing nowhere,
    which fails later and further from the cause.
    """
    provider = _FakeProvider()
    provider.base_url = None
    with pytest.raises(ValueError) as exc:
        auth.mcpserver_auth_kwargs(provider)
    assert "OIDCPROXY_BASE_URL" in str(exc.value)


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
