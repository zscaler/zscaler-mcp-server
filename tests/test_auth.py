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


# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------


class TestAuthBanner:
    """Every enabled auth mode must announce its posture at startup.

    The ``oidc`` mode silently stopped doing so once it began returning early
    from ``apply_auth_middleware`` — it logged a single line instead of the
    banner, so an operator reading the log could not tell the mode was active.
    Bypassing the ASGI middleware is correct; skipping the banner is not.
    """

    BANNER = "MCP CLIENT AUTHENTICATION ENABLED"

    @staticmethod
    def _configure(monkeypatch, mode):
        monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
        monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", mode)
        if mode == "jwt":
            monkeypatch.setenv("ZSCALER_MCP_AUTH_JWKS_URI", "https://idp.example.com/jwks")
            monkeypatch.setenv("ZSCALER_MCP_AUTH_ISSUER", "https://idp.example.com/")
            monkeypatch.setenv("ZSCALER_MCP_AUTH_AUDIENCE", "mcp")
        elif mode == "api-key":
            monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "k" * 32)
        elif mode == "zscaler":
            monkeypatch.setenv("ZSCALER_VANITY_DOMAIN", "acme")
        else:
            monkeypatch.setattr(
                auth,
                "_OIDC_POSTURE",
                {
                    "issuer": "https://idp.example.com/v2.0",
                    "resource": "https://mcp.example.com/mcp",
                    "audience": "client-id-guid",
                    "required_scopes": None,
                },
            )

    @pytest.mark.parametrize("mode", ["jwt", "api-key", "zscaler", "oidc"])
    def test_every_mode_logs_the_banner(self, monkeypatch, caplog, mode):
        self._configure(monkeypatch, mode)
        with caplog.at_level("INFO", logger="zscaler_mcp.security.auth"):
            auth.apply_auth_middleware(object(), "streamable-http")
        assert self.BANNER in caplog.text
        assert f"Mode: {mode}" in caplog.text
        assert "Transport: streamable-http" in caplog.text

    def test_oidc_banner_names_what_it_will_accept(self, monkeypatch, caplog):
        """The banner is the fastest way to diagnose a rejected token, so it has
        to carry the three values the verifier actually compares against."""
        self._configure(monkeypatch, "oidc")
        with caplog.at_level("INFO", logger="zscaler_mcp.security.auth"):
            auth.apply_auth_middleware(object(), "streamable-http")
        assert "https://idp.example.com/v2.0" in caplog.text
        assert "https://mcp.example.com/mcp" in caplog.text
        assert "client-id-guid" in caplog.text

    def test_oidc_banner_locates_the_metadata_document(self, monkeypatch, caplog):
        """A resource identifier with a path (which Entra ID requires) moves the
        metadata document, and an operator checking the bare path gets a 404."""
        self._configure(monkeypatch, "oidc")
        with caplog.at_level("INFO", logger="zscaler_mcp.security.auth"):
            auth.apply_auth_middleware(object(), "streamable-http")
        assert "https://mcp.example.com/.well-known/oauth-protected-resource/mcp" in caplog.text

    def test_metadata_path_tracks_the_resource_path(self):
        assert (
            auth._protected_resource_metadata_path("https://h/mcp")
            == "https://h/.well-known/oauth-protected-resource/mcp"
        )
        assert (
            auth._protected_resource_metadata_path("https://h")
            == "https://h/.well-known/oauth-protected-resource"
        )
        assert (
            auth._protected_resource_metadata_path("https://h/")
            == "https://h/.well-known/oauth-protected-resource"
        )

    def test_oidc_banner_degrades_without_network_io(self, monkeypatch, caplog):
        """If the resolved values are absent the banner still prints, from env."""
        monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
        monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "oidc")
        monkeypatch.setattr(auth, "_OIDC_POSTURE", None)
        monkeypatch.setenv("OIDCPROXY_BASE_URL", "https://mcp.example.com")
        monkeypatch.setenv("OIDCPROXY_CLIENT_ID", "abc")
        with caplog.at_level("INFO", logger="zscaler_mcp.security.auth"):
            auth.apply_auth_middleware(object(), "streamable-http")
        assert self.BANNER in caplog.text
        assert "https://mcp.example.com" in caplog.text


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


# =============================================================================
# Principal derivation, per auth mode
#
# `AuthProvider.principal()` is what makes a sealed SEP-2322 `requestState`
# caller-bound rather than merely call-bound. The cross-mode assertion in
# `test_protocol_2026_07_28.py` drives the middleware end-to-end, but only
# through `APIKeyAuthProvider` — diff coverage showed the jwt and zscaler
# implementations were never executed by any test, while the docs claimed all
# four modes. These cover the two that were missing, plus the base default.
# =============================================================================


class TestPrincipalDerivation:
    def test_base_provider_yields_no_principal(self):
        """The default is None, so a new provider fails closed rather than open.

        A provider that forgets to override `principal()` must not accidentally
        bind state to a wrong or shared identity — it binds to nothing, and the
        middleware then leaves the request unauthenticated for state purposes.
        """
        from zscaler_mcp.security.auth import AuthProvider

        class _Bare(AuthProvider):
            async def authenticate(self, authorization, headers_list=None):
                return True, None

        assert _Bare().principal("Bearer whatever") is None

    # -- jwt ---------------------------------------------------------------

    def _jwt_provider(self):
        from zscaler_mcp.security.auth import JWTAuthProvider

        provider = JWTAuthProvider.__new__(JWTAuthProvider)
        import jwt as _jwt

        provider._jwt = _jwt
        return provider

    def _signed(self, **claims):
        import jwt as _jwt

        # 32+ bytes: the signature is never verified here, but a short key
        # emits an InsecureKeyLengthWarning that clutters the run.
        return _jwt.encode(claims, "k" * 32, algorithm="HS256")

    def test_jwt_principal_comes_from_the_tokens_own_claims(self):
        token = self._signed(sub="user-42", azp="client-abc", exp=9999999999, scp="read write")
        principal = self._jwt_provider().principal(f"Bearer {token}")
        assert principal is not None
        assert principal.client_id == "client-abc"
        assert principal.subject == "user-42"
        assert principal.scopes == ["read", "write"]
        assert principal.expires_at == 9999999999

    def test_jwt_subject_distinguishes_two_users_of_one_oauth_client(self):
        """This is the property that matters: same client, different humans.

        Without `subject`, every user of a shared OAuth client would collapse to
        one principal and could spend each other's confirmations.
        """
        provider = self._jwt_provider()
        a = provider.principal(f"Bearer {self._signed(sub='alice', azp='shared')}")
        b = provider.principal(f"Bearer {self._signed(sub='bob', azp='shared')}")
        assert a.client_id == b.client_id == "shared"
        assert a.subject != b.subject

    def test_jwt_claim_precedence_falls_back_to_appid_then_aud(self):
        """Entra ID issues `appid`; some IdPs only set `aud`. Both must resolve."""
        provider = self._jwt_provider()
        assert provider.principal(f"Bearer {self._signed(appid='entra-app')}").client_id == (
            "entra-app"
        )
        assert provider.principal(f"Bearer {self._signed(aud='api://x')}").client_id == "api://x"

    def test_jwt_scope_claim_accepts_a_list_as_well_as_a_string(self):
        provider = self._jwt_provider()
        assert provider.principal(f"Bearer {self._signed(scope=['a', 'b'])}").scopes == ["a", "b"]

    def test_jwt_principal_is_none_without_a_two_part_authorization_header(self):
        provider = self._jwt_provider()
        assert provider.principal("") is None
        assert provider.principal("Bearer") is None

    # -- zscaler -----------------------------------------------------------

    def _zscaler_provider(self):
        from zscaler_mcp.security.auth import ZscalerAuthProvider

        return ZscalerAuthProvider.__new__(ZscalerAuthProvider)

    def test_zscaler_principal_is_the_client_id_from_basic_auth(self):
        import base64

        creds = base64.b64encode(b"oneapi-client-1:super-secret").decode()
        principal = self._zscaler_provider().principal(f"Basic {creds}")
        assert principal is not None
        assert principal.client_id == "zscaler:oneapi-client-1"

    def test_zscaler_principal_never_carries_the_secret(self):
        """The client id is an identifier; the secret must not reach sealed state."""
        import base64

        creds = base64.b64encode(b"oneapi-client-1:super-secret").decode()
        principal = self._zscaler_provider().principal(f"Basic {creds}")
        assert "super-secret" not in str(principal.client_id)
        assert principal.token == ""

    def test_zscaler_principal_reads_the_x_header_pair_too(self):
        """`AuthMiddleware` accepts both formats, so both must yield a principal."""
        headers = [
            (b"x-zscaler-client-id", b"header-client"),
            (b"x-zscaler-client-secret", b"header-secret"),
        ]
        principal = self._zscaler_provider().principal("", headers)
        assert principal is not None
        assert principal.client_id == "zscaler:header-client"

    def test_zscaler_two_client_ids_are_two_principals(self):
        import base64

        provider = self._zscaler_provider()

        def p(cid):
            creds = base64.b64encode(f"{cid}:secret".encode()).decode()
            return provider.principal(f"Basic {creds}").client_id

        assert p("tenant-a") != p("tenant-b")

    def test_zscaler_principal_is_none_when_no_credential_is_present(self):
        provider = self._zscaler_provider()
        assert provider.principal("") is None
        assert provider.principal("Basic ") is None
        assert provider.principal("Basic !!!not-base64!!!") is None
        # Basic auth with no colon carries no client id to bind to.
        import base64

        assert provider.principal(f"Basic {base64.b64encode(b'nocolon').decode()}") is None


class TestMiddlewarePrincipalPublication:
    """`AuthMiddleware` is the auth stack for jwt / api-key / zscaler.

    The SDK's `AuthContextMiddleware` is mounted only on the OIDC path, so these
    three modes get their identity published here or nowhere.
    """

    def _run(self, provider, headers):
        import asyncio

        from mcp.server.auth.middleware.auth_context import get_access_token

        from zscaler_mcp.security.auth import AuthMiddleware

        seen: dict = {}

        async def app(scope, receive, send):
            token = get_access_token()
            seen["client_id"] = None if token is None else token.client_id
            seen["scope_user"] = scope.get("user")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def receive():
            return {"type": "http.request"}

        async def send(_m):
            return None

        scope = {"type": "http", "path": "/mcp", "headers": headers}
        asyncio.run(AuthMiddleware(app, provider)(scope, receive, send))
        return seen

    def test_a_provider_without_a_principal_still_serves_the_request(self):
        """Authentication and identity are separate outcomes.

        A provider that authenticates but cannot name the caller must not fail the
        request — it means confirmations are call-bound but not caller-bound, which
        is a weaker binding, not a rejection. Verified via a provider that
        authenticates and returns no principal.
        """
        from zscaler_mcp.security.auth import AuthProvider

        class _AnonymousButValid(AuthProvider):
            async def authenticate(self, authorization, headers_list=None):
                return True, None

        seen = self._run(_AnonymousButValid(), [(b"authorization", b"Bearer anything")])
        assert seen["client_id"] is None
        assert seen["scope_user"] is None

    def test_the_context_is_reset_after_the_request(self):
        """A leaked contextvar would bind one caller's identity to the next request."""
        from mcp.server.auth.middleware.auth_context import get_access_token

        from zscaler_mcp.security.auth import APIKeyAuthProvider

        seen = self._run(APIKeyAuthProvider("key-x"), [(b"authorization", b"Bearer key-x")])
        assert seen["client_id"] is not None, "identity must be visible during the request"
        assert get_access_token() is None, "and gone once it completes"


# =============================================================================
# AWS Bedrock AgentCore credential paths
#
# Two relaxations the AgentCore fork carried, consolidated here. They exist
# because of one platform fact: `InvokeAgentRuntime` forwards only headers named
# in `requestHeaderAllowlist`, and the Console Sandbox playground offers no UI to
# set any header at all — so the caller frequently cannot present a credential
# even though the platform has already authenticated them.
#
# `X-Api-Key` is a second envelope for the same secret and is always on. The
# container-credential fallback genuinely admits an uncredentialed request, so it
# is gated on an explicit opt-in and must stay off everywhere else.
# =============================================================================


class TestPlatformAuthGate:
    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", raising=False)
        assert auth.platform_auth_trusted() is False

    @pytest.mark.parametrize("truthy", ["true", "1", "yes", "TRUE", " Yes "])
    def test_accepted_spellings(self, monkeypatch, truthy):
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", truthy)
        assert auth.platform_auth_trusted() is True

    @pytest.mark.parametrize("falsy", ["false", "0", "no", "", "  ", "maybe"])
    def test_anything_else_is_off(self, monkeypatch, falsy):
        """Fails closed on a typo.

        An operator who writes `TRUE_` or `on` gets the safe behaviour, not the
        one that admits anonymous callers.
        """
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", falsy)
        assert auth.platform_auth_trusted() is False


class TestApiKeyHeaderAlternatives:
    """`X-Api-Key` carries the same secret as `Authorization: Bearer`."""

    @pytest.mark.asyncio
    async def test_x_api_key_is_accepted(self):
        p = auth.APIKeyAuthProvider("sk-secret")
        ok, err = await p.authenticate("", [(b"x-api-key", b"sk-secret")])
        assert ok is True
        assert err is None

    @pytest.mark.asyncio
    async def test_x_api_key_is_matched_case_insensitively(self):
        """HTTP header names are case-insensitive and ASGI servers vary."""
        p = auth.APIKeyAuthProvider("sk-secret")
        ok, _ = await p.authenticate("", [(b"X-Api-Key", b"sk-secret")])
        assert ok is True

    @pytest.mark.asyncio
    async def test_a_wrong_x_api_key_is_rejected(self):
        p = auth.APIKeyAuthProvider("sk-secret")
        ok, err = await p.authenticate("", [(b"x-api-key", b"sk-wrong")])
        assert ok is False
        assert err == "Invalid API key"

    @pytest.mark.asyncio
    async def test_authorization_wins_and_a_bad_one_is_not_rescued(self):
        """A present `Authorization` is the caller's claim; honour it.

        Falling through to `X-Api-Key` after a failed Bearer check would let a
        caller retry two credentials in one request.
        """
        p = auth.APIKeyAuthProvider("sk-secret")
        ok, _ = await p.authenticate("Bearer sk-wrong", [(b"x-api-key", b"sk-secret")])
        assert ok is False

    @pytest.mark.asyncio
    async def test_the_error_names_both_accepted_headers(self):
        p = auth.APIKeyAuthProvider("sk-secret")
        _, err = await p.authenticate("", [])
        assert "Authorization: Bearer" in err
        assert "X-Api-Key" in err


class TestContainerCredentialFallbackIsGated:
    """The fallback admits a request carrying no credential at all.

    On AgentCore that is defensible: IAM or a customJwtAuthorizer ran before the
    sidecar forwarded the request. On the ECS / EC2 / EKS paths the container is
    reachable directly, and there the absence of a credential is the only thing
    between an anonymous caller and the tenant.
    """

    @pytest.mark.asyncio
    async def test_api_key_does_not_fall_back_by_default(self, monkeypatch):
        monkeypatch.delenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", raising=False)
        monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "sk-secret")
        p = auth.APIKeyAuthProvider("sk-secret")
        ok, _ = await p.authenticate("", [])
        assert ok is False, "the container's own key must not authenticate a stranger"

    @pytest.mark.asyncio
    async def test_api_key_falls_back_when_the_platform_is_trusted(self, monkeypatch):
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", "true")
        monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "sk-secret")
        p = auth.APIKeyAuthProvider("sk-secret")
        ok, err = await p.authenticate("", [])
        assert ok is True
        assert err is None

    @pytest.mark.asyncio
    async def test_a_trusted_platform_still_rejects_a_wrong_key(self, monkeypatch):
        """Trust removes the requirement to present a credential, not the check.

        A caller that DOES present one is still validated against it.
        """
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", "true")
        monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "sk-secret")
        p = auth.APIKeyAuthProvider("sk-secret")
        ok, _ = await p.authenticate("Bearer sk-wrong", [])
        assert ok is False

    @pytest.mark.asyncio
    async def test_zscaler_does_not_fall_back_by_default(self, monkeypatch):
        monkeypatch.delenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", raising=False)
        monkeypatch.setenv("ZSCALER_CLIENT_ID", "client")
        monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "secret")
        p = auth.ZscalerAuthProvider("acme")
        ok, err = await p.authenticate("", [])
        assert ok is False
        assert "requires credentials" in err

    @pytest.mark.asyncio
    async def test_zscaler_falls_back_when_the_platform_is_trusted(self, monkeypatch):
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", "true")
        monkeypatch.setenv("ZSCALER_CLIENT_ID", "client")
        monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "secret")
        monkeypatch.setattr(auth, "fetch_oneapi_token", lambda **kw: ("tok", None))
        p = auth.ZscalerAuthProvider("acme")
        ok, err = await p.authenticate("", [])
        assert ok is True
        assert err is None

    @pytest.mark.asyncio
    async def test_the_fallback_still_validates_the_container_credentials(self, monkeypatch):
        """A misconfigured container fails at the door, not on the first tool call."""
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", "true")
        monkeypatch.setenv("ZSCALER_CLIENT_ID", "client")
        monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "rotated-away")
        monkeypatch.setattr(
            auth, "fetch_oneapi_token", lambda **kw: (None, "Invalid OneAPI credentials")
        )
        p = auth.ZscalerAuthProvider("acme")
        ok, err = await p.authenticate("", [])
        assert ok is False
        assert "Invalid OneAPI credentials" in err

    @pytest.mark.asyncio
    async def test_trust_without_container_credentials_still_refuses(self, monkeypatch):
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", "true")
        monkeypatch.delenv("ZSCALER_CLIENT_ID", raising=False)
        monkeypatch.delenv("ZSCALER_CLIENT_SECRET", raising=False)
        p = auth.ZscalerAuthProvider("acme")
        ok, _ = await p.authenticate("", [])
        assert ok is False

    def test_the_fallback_still_produces_a_principal(self, monkeypatch):
        """Otherwise sealed requestState is call-bound but not caller-bound.

        This is the deployment where confirmations matter most, so losing the
        principal exactly here would be the worst place for it.
        """
        monkeypatch.setenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", "true")
        monkeypatch.setenv("ZSCALER_CLIENT_ID", "container-client")
        monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "secret")
        principal = auth.ZscalerAuthProvider("acme").principal("", [])
        assert principal is not None
        assert principal.client_id == "zscaler:container-client"
        assert principal.token == "", "the credential itself must never enter sealed state"

    def test_no_principal_without_trust(self, monkeypatch):
        monkeypatch.delenv("ZSCALER_MCP_TRUST_PLATFORM_AUTH", raising=False)
        monkeypatch.setenv("ZSCALER_CLIENT_ID", "container-client")
        monkeypatch.setenv("ZSCALER_CLIENT_SECRET", "secret")
        assert auth.ZscalerAuthProvider("acme").principal("", []) is None


class TestMiddlewareForwardsHeadersToEveryProvider:
    """Previously an isinstance check handed them only to ZscalerAuthProvider.

    That is why `X-Api-Key` could not work: the provider that needed to read it
    was never given the header list.
    """

    def _status(self, provider, headers):
        import asyncio

        from zscaler_mcp.security.auth import AuthMiddleware

        captured: dict = {}

        async def app(scope, receive, send):
            captured["status"] = 200
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            if message["type"] == "http.response.start":
                captured.setdefault("status", message["status"])

        scope = {"type": "http", "path": "/mcp", "headers": headers}
        asyncio.run(AuthMiddleware(app, provider)(scope, receive, send))
        return captured["status"]

    def test_x_api_key_authenticates_end_to_end(self):
        assert self._status(auth.APIKeyAuthProvider("sk-x"), [(b"x-api-key", b"sk-x")]) == 200

    def test_a_wrong_x_api_key_is_401_end_to_end(self):
        assert self._status(auth.APIKeyAuthProvider("sk-x"), [(b"x-api-key", b"sk-nope")]) == 401
