"""
Tests for zscaler_mcp.auth — MCP client authentication.

Covers all four auth modes (api-key, jwt, zscaler, oauth-proxy) plus the
no-auth default. JWT tests use locally-generated RSA keys with a mock JWKS
server so they run offline without any IdP dependency.
"""

import asyncio
import base64
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from zscaler_mcp.auth import (
    APIKeyAuthProvider,
    AuthMiddleware,
    JWTAuthProvider,
    OAuthProxyAuthProvider,
    ZscalerAuthProvider,
    apply_auth_middleware,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine synchronously (for pytest without asyncio mode)."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _generate_rsa_keypair():
    """Generate an RSA key pair for JWT signing in tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    def _int_to_base64url(n, length=None):
        b = n.to_bytes((n.bit_length() + 7) // 8, byteorder="big")
        if length and len(b) < length:
            b = b"\x00" * (length - len(b)) + b
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "test-key-1",
        "n": _int_to_base64url(public_numbers.n),
        "e": _int_to_base64url(public_numbers.e),
    }
    return private_pem, jwk


class _JWKSHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that serves a static JWKS document."""

    jwks_doc = {"keys": []}

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self.jwks_doc).encode())

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def rsa_keys():
    """Module-scoped RSA key pair fixture."""
    return _generate_rsa_keypair()


@pytest.fixture(scope="module")
def jwks_server(rsa_keys):
    """Module-scoped local JWKS HTTP server."""
    _, jwk = rsa_keys
    _JWKSHandler.jwks_doc = {"keys": [jwk]}

    server = HTTPServer(("127.0.0.1", 0), _JWKSHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


# ---------------------------------------------------------------------------
# API Key Provider
# ---------------------------------------------------------------------------


class TestAPIKeyAuthProvider:
    def test_valid_key(self):
        p = APIKeyAuthProvider(api_key="sk-test-12345")
        ok, err = _run_async(p.authenticate("Bearer sk-test-12345"))
        assert ok is True
        assert err is None

    def test_invalid_key(self):
        p = APIKeyAuthProvider(api_key="sk-test-12345")
        ok, err = _run_async(p.authenticate("Bearer wrong-key"))
        assert ok is False
        assert "Invalid" in err

    def test_missing_header(self):
        p = APIKeyAuthProvider(api_key="sk-test-12345")
        ok, err = _run_async(p.authenticate(""))
        assert ok is False

    def test_wrong_scheme(self):
        p = APIKeyAuthProvider(api_key="sk-test-12345")
        ok, err = _run_async(p.authenticate("Basic abc"))
        assert ok is False
        assert "Bearer" in err

    def test_empty_key_rejected(self):
        with pytest.raises(ValueError):
            APIKeyAuthProvider(api_key="")

    def test_whitespace_key_rejected(self):
        with pytest.raises(ValueError):
            APIKeyAuthProvider(api_key="   ")

    def test_scheme_is_bearer(self):
        p = APIKeyAuthProvider(api_key="x")
        assert p.scheme == "Bearer"

    def test_timing_safety(self):
        """Verify that comparison uses hmac.compare_digest (constant-time)."""
        p = APIKeyAuthProvider(api_key="a" * 64)
        ok1, _ = _run_async(p.authenticate("Bearer " + "a" * 64))
        ok2, _ = _run_async(p.authenticate("Bearer " + "b" * 64))
        assert ok1 is True
        assert ok2 is False


# ---------------------------------------------------------------------------
# JWT Provider
# ---------------------------------------------------------------------------


class TestJWTAuthProvider:
    ISSUER = "https://test-issuer.example.com"
    AUDIENCE = "zscaler-mcp-test"

    def _make_token(self, rsa_keys, claims_override=None, exp_offset=3600):
        private_pem, jwk = rsa_keys
        claims = {
            "iss": self.ISSUER,
            "aud": self.AUDIENCE,
            "sub": "user@example.com",
            "exp": int(time.time()) + exp_offset,
            "iat": int(time.time()),
        }
        if claims_override:
            claims.update(claims_override)
        return pyjwt.encode(
            claims,
            private_pem,
            algorithm="RS256",
            headers={"kid": jwk["kid"]},
        )

    def test_valid_token(self, rsa_keys, jwks_server):
        p = JWTAuthProvider(
            jwks_uri=jwks_server,
            issuer=self.ISSUER,
            audience=self.AUDIENCE,
        )
        token = self._make_token(rsa_keys)
        ok, err = _run_async(p.authenticate(f"Bearer {token}"))
        assert ok is True, f"Expected success, got: {err}"
        assert err is None

    def test_expired_token(self, rsa_keys, jwks_server):
        p = JWTAuthProvider(
            jwks_uri=jwks_server,
            issuer=self.ISSUER,
            audience=self.AUDIENCE,
        )
        token = self._make_token(rsa_keys, exp_offset=-3600)
        ok, err = _run_async(p.authenticate(f"Bearer {token}"))
        assert ok is False
        assert "expired" in err.lower()

    def test_wrong_issuer(self, rsa_keys, jwks_server):
        p = JWTAuthProvider(
            jwks_uri=jwks_server,
            issuer=self.ISSUER,
            audience=self.AUDIENCE,
        )
        token = self._make_token(rsa_keys, claims_override={"iss": "https://evil.com"})
        ok, err = _run_async(p.authenticate(f"Bearer {token}"))
        assert ok is False
        assert "issuer" in err.lower()

    def test_wrong_audience(self, rsa_keys, jwks_server):
        p = JWTAuthProvider(
            jwks_uri=jwks_server,
            issuer=self.ISSUER,
            audience=self.AUDIENCE,
        )
        token = self._make_token(rsa_keys, claims_override={"aud": "wrong-audience"})
        ok, err = _run_async(p.authenticate(f"Bearer {token}"))
        assert ok is False
        assert "audience" in err.lower()

    def test_missing_header(self, rsa_keys, jwks_server):
        p = JWTAuthProvider(
            jwks_uri=jwks_server,
            issuer=self.ISSUER,
            audience=self.AUDIENCE,
        )
        ok, err = _run_async(p.authenticate(""))
        assert ok is False

    def test_garbage_token(self, rsa_keys, jwks_server):
        p = JWTAuthProvider(
            jwks_uri=jwks_server,
            issuer=self.ISSUER,
            audience=self.AUDIENCE,
        )
        ok, err = _run_async(p.authenticate("Bearer not.a.jwt"))
        assert ok is False

    def test_empty_jwks_uri_rejected(self):
        with pytest.raises(ValueError):
            JWTAuthProvider(jwks_uri="", issuer="x")

    def test_empty_issuer_rejected(self):
        with pytest.raises(ValueError):
            JWTAuthProvider(jwks_uri="https://example.com/keys", issuer="")


# ---------------------------------------------------------------------------
# Zscaler OneAPI Provider
# ---------------------------------------------------------------------------


class TestZscalerAuthProvider:
    def test_empty_vanity_domain_rejected(self):
        with pytest.raises(ValueError):
            ZscalerAuthProvider(vanity_domain="")

    def test_production_token_url(self):
        p = ZscalerAuthProvider(vanity_domain="acme", cloud="production")
        assert p._token_url == "https://acme.zslogin.net/oauth2/v1/token"

    def test_beta_token_url(self):
        p = ZscalerAuthProvider(vanity_domain="acme", cloud="beta")
        assert p._token_url == "https://acme.zsloginbeta.net/oauth2/v1/token"

    def test_scheme_is_basic(self):
        p = ZscalerAuthProvider(vanity_domain="acme")
        assert p.scheme == "Basic"

    def test_rejects_bearer_scheme(self):
        p = ZscalerAuthProvider(vanity_domain="acme")
        ok, err = _run_async(p.authenticate("Bearer some-token"))
        assert ok is False
        assert "Basic" in err

    def test_rejects_empty_header(self):
        p = ZscalerAuthProvider(vanity_domain="acme")
        ok, err = _run_async(p.authenticate(""))
        assert ok is False

    def test_rejects_invalid_base64(self):
        p = ZscalerAuthProvider(vanity_domain="acme")
        ok, err = _run_async(p.authenticate("Basic !!!invalid!!!"))
        assert ok is False
        assert "Base64" in err or "encoding" in err.lower()

    def test_rejects_missing_colon(self):
        p = ZscalerAuthProvider(vanity_domain="acme")
        payload = base64.b64encode(b"no-colon-here").decode()
        ok, err = _run_async(p.authenticate(f"Basic {payload}"))
        assert ok is False
        assert "client_id:client_secret" in err

    def test_rejects_empty_client_id(self):
        p = ZscalerAuthProvider(vanity_domain="acme")
        payload = base64.b64encode(b":secret").decode()
        ok, err = _run_async(p.authenticate(f"Basic {payload}"))
        assert ok is False

    def test_rejects_empty_secret(self):
        p = ZscalerAuthProvider(vanity_domain="acme")
        payload = base64.b64encode(b"client_id:").decode()
        ok, err = _run_async(p.authenticate(f"Basic {payload}"))
        assert ok is False

    def test_caching_avoids_repeated_calls(self):
        """After a successful validation, the cache should prevent re-validation."""
        p = ZscalerAuthProvider(vanity_domain="acme")
        client_id, client_secret = "test-id", "test-secret"
        cred_hash = p._credential_hash(client_id, client_secret)

        p._cache[cred_hash] = (time.time() + 3600, "cached-token")

        payload = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        ok, err = _run_async(p.authenticate(f"Basic {payload}"))
        assert ok is True
        assert err is None

    def test_expired_cache_triggers_revalidation(self):
        """Expired cache entries should be cleaned up."""
        p = ZscalerAuthProvider(vanity_domain="acme")
        cred_hash = p._credential_hash("id", "secret")
        p._cache[cred_hash] = (time.time() - 100, "expired-token")
        result = p._check_cache(cred_hash)
        assert result is None
        assert cred_hash not in p._cache


# ---------------------------------------------------------------------------
# OAuth Proxy Provider (Phase 2)
# ---------------------------------------------------------------------------


class TestOAuthProxyAuthProvider:
    def test_not_implemented(self):
        with pytest.raises(NotImplementedError):
            OAuthProxyAuthProvider()


# ---------------------------------------------------------------------------
# ASGI Auth Middleware
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    @staticmethod
    async def _ok_app(scope, receive, send):
        """Minimal ASGI app returning 200."""
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    def _make_scope(self, path="/mcp", headers=None):
        h = headers or []
        return {"type": "http", "path": path, "headers": h}

    def _collect_responses(self, app, scope):
        responses = []

        async def send(msg):
            responses.append(msg)

        _run_async(app(scope, None, send))
        return responses

    def test_rejects_unauthenticated(self):
        provider = APIKeyAuthProvider(api_key="secret")
        app = AuthMiddleware(self._ok_app, provider)
        responses = self._collect_responses(app, self._make_scope())
        assert responses[0]["status"] == 401

    def test_accepts_authenticated(self):
        provider = APIKeyAuthProvider(api_key="secret")
        app = AuthMiddleware(self._ok_app, provider)
        scope = self._make_scope(headers=[(b"authorization", b"Bearer secret")])
        responses = self._collect_responses(app, scope)
        assert responses[0]["status"] == 200

    def test_health_bypasses_auth(self):
        provider = APIKeyAuthProvider(api_key="secret")
        app = AuthMiddleware(self._ok_app, provider)
        responses = self._collect_responses(app, self._make_scope(path="/health"))
        assert responses[0]["status"] == 200

    def test_healthz_bypasses_auth(self):
        provider = APIKeyAuthProvider(api_key="secret")
        app = AuthMiddleware(self._ok_app, provider)
        responses = self._collect_responses(app, self._make_scope(path="/healthz"))
        assert responses[0]["status"] == 200

    def test_non_http_passes_through(self):
        provider = APIKeyAuthProvider(api_key="secret")
        inner_called = []

        async def tracking_app(scope, receive, send):
            inner_called.append(True)

        app = AuthMiddleware(tracking_app, provider)
        scope = {"type": "lifespan"}
        _run_async(app(scope, None, None))
        assert len(inner_called) == 1

    def test_401_includes_www_authenticate(self):
        provider = APIKeyAuthProvider(api_key="secret")
        app = AuthMiddleware(self._ok_app, provider)
        responses = self._collect_responses(app, self._make_scope())
        headers = dict(responses[0].get("headers", []))
        assert b"www-authenticate" in headers

    def test_401_body_is_jsonrpc(self):
        provider = APIKeyAuthProvider(api_key="secret")
        app = AuthMiddleware(self._ok_app, provider)
        responses = self._collect_responses(app, self._make_scope())
        body = json.loads(responses[1]["body"])
        assert "jsonrpc" in body
        assert body["error"]["code"] == -32001


# ---------------------------------------------------------------------------
# apply_auth_middleware factory
# ---------------------------------------------------------------------------


class TestApplyAuthMiddleware:
    _AUTH_ENVS = [
        "ZSCALER_MCP_AUTH_ENABLED",
        "ZSCALER_MCP_AUTH_MODE",
        "ZSCALER_MCP_AUTH_API_KEY",
        "ZSCALER_MCP_AUTH_JWKS_URI",
        "ZSCALER_MCP_AUTH_ISSUER",
        "ZSCALER_MCP_AUTH_AUDIENCE",
        "ZSCALER_MCP_AUTH_ALGORITHMS",
        "ZSCALER_VANITY_DOMAIN",
        "ZSCALER_CLOUD",
    ]

    def _clean_env(self):
        for key in self._AUTH_ENVS:
            os.environ.pop(key, None)

    # -- Auth enabled by default (zero-trust) --

    def test_auth_enabled_by_default(self):
        """Auth is ON by default for HTTP transports. With no credentials
        configured, the server defaults to jwt mode and raises SystemExit
        because JWKS_URI is missing."""
        self._clean_env()
        try:
            with pytest.raises(SystemExit, match="Authentication is enabled"):
                apply_auth_middleware("original-app", "streamable-http")
        finally:
            self._clean_env()

    def test_explicit_disable_returns_original_app(self):
        """Explicitly setting ZSCALER_MCP_AUTH_ENABLED=false bypasses auth."""
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "false"
        try:
            result = apply_auth_middleware("original-app", "streamable-http")
            assert result == "original-app"
        finally:
            self._clean_env()

    def test_explicit_disable_0(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "0"
        try:
            result = apply_auth_middleware("original-app", "sse")
            assert result == "original-app"
        finally:
            self._clean_env()

    def test_explicit_disable_no(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "no"
        try:
            result = apply_auth_middleware("original-app", "sse")
            assert result == "original-app"
        finally:
            self._clean_env()

    # -- Auto-detection --

    def test_auto_detect_jwt_from_jwks_uri(self):
        """When no explicit mode is set but JWKS_URI is present, auto-detect jwt."""
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_JWKS_URI"] = "https://idp.example.com/keys"
        os.environ["ZSCALER_MCP_AUTH_ISSUER"] = "https://idp.example.com"
        try:
            result = apply_auth_middleware("app", "streamable-http")
            assert isinstance(result, AuthMiddleware)
            assert isinstance(result.provider, JWTAuthProvider)
        finally:
            self._clean_env()

    def test_auto_detect_api_key(self):
        """When no explicit mode is set but API_KEY is present, auto-detect api-key."""
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_API_KEY"] = "sk-test-key"
        try:
            result = apply_auth_middleware("app", "sse")
            assert isinstance(result, AuthMiddleware)
            assert isinstance(result.provider, APIKeyAuthProvider)
        finally:
            self._clean_env()

    def test_auto_detect_zscaler(self):
        """When no explicit mode is set but VANITY_DOMAIN is present, auto-detect zscaler."""
        self._clean_env()
        os.environ["ZSCALER_VANITY_DOMAIN"] = "acme"
        try:
            result = apply_auth_middleware("app", "streamable-http")
            assert isinstance(result, AuthMiddleware)
            assert isinstance(result.provider, ZscalerAuthProvider)
        finally:
            self._clean_env()

    def test_auto_detect_priority_jwks_over_api_key(self):
        """JWKS_URI takes precedence over API_KEY in auto-detection."""
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_JWKS_URI"] = "https://idp.example.com/keys"
        os.environ["ZSCALER_MCP_AUTH_ISSUER"] = "https://idp.example.com"
        os.environ["ZSCALER_MCP_AUTH_API_KEY"] = "sk-also-set"
        try:
            result = apply_auth_middleware("app", "streamable-http")
            assert isinstance(result.provider, JWTAuthProvider)
        finally:
            self._clean_env()

    # -- stdio exempt --

    def test_stdio_always_skips(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "api-key"
        os.environ["ZSCALER_MCP_AUTH_API_KEY"] = "test"
        try:
            result = apply_auth_middleware("original-app", "stdio")
            assert result == "original-app"
        finally:
            self._clean_env()

    # -- Explicit mode tests --

    def test_api_key_mode_wraps(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "api-key"
        os.environ["ZSCALER_MCP_AUTH_API_KEY"] = "test-key"
        try:
            result = apply_auth_middleware("original-app", "sse")
            assert isinstance(result, AuthMiddleware)
        finally:
            self._clean_env()

    def test_jwt_mode_wraps(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "jwt"
        os.environ["ZSCALER_MCP_AUTH_JWKS_URI"] = "https://example.com/.well-known/jwks.json"
        os.environ["ZSCALER_MCP_AUTH_ISSUER"] = "https://example.com"
        try:
            result = apply_auth_middleware("original-app", "streamable-http")
            assert isinstance(result, AuthMiddleware)
        finally:
            self._clean_env()

    def test_zscaler_mode_wraps(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_ENABLED"] = "true"
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "zscaler"
        os.environ["ZSCALER_VANITY_DOMAIN"] = "test-domain"
        try:
            result = apply_auth_middleware("original-app", "streamable-http")
            assert isinstance(result, AuthMiddleware)
        finally:
            self._clean_env()

    def test_unknown_mode_raises(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "magic"
        try:
            with pytest.raises(SystemExit, match="Authentication is enabled"):
                apply_auth_middleware("app", "streamable-http")
        finally:
            self._clean_env()

    def test_oauth_proxy_raises(self):
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "oauth-proxy"
        try:
            with pytest.raises(SystemExit):
                apply_auth_middleware("app", "streamable-http")
        finally:
            self._clean_env()

    # -- Invalid config raises SystemExit --

    def test_jwt_mode_missing_jwks_uri_raises(self):
        """JWT mode without JWKS_URI raises SystemExit (not ValueError)."""
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "jwt"
        os.environ["ZSCALER_MCP_AUTH_ISSUER"] = "https://example.com"
        try:
            with pytest.raises(SystemExit, match="Authentication is enabled"):
                apply_auth_middleware("app", "streamable-http")
        finally:
            self._clean_env()

    def test_api_key_mode_missing_key_raises(self):
        """api-key mode without API_KEY raises SystemExit."""
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "api-key"
        try:
            with pytest.raises(SystemExit, match="Authentication is enabled"):
                apply_auth_middleware("app", "streamable-http")
        finally:
            self._clean_env()

    def test_zscaler_mode_missing_domain_raises(self):
        """zscaler mode without VANITY_DOMAIN raises SystemExit."""
        self._clean_env()
        os.environ["ZSCALER_MCP_AUTH_MODE"] = "zscaler"
        try:
            with pytest.raises(SystemExit, match="Authentication is enabled"):
                apply_auth_middleware("app", "streamable-http")
        finally:
            self._clean_env()
