"""MCP-level authentication for the v2 Zscaler MCP server.

Ported from v1 (``zscaler_mcp/auth.py``). The provider set, the credential
caching, and the ASGI middleware are framework-agnostic, so this is a faithful
port — only the package imports change. v2 keeps v1's posture exactly:

* Authentication is ENABLED by default for HTTP transports (zero-trust).
  Disable only with ``ZSCALER_MCP_AUTH_ENABLED=false`` (prints a warning).
* Modes: ``jwt`` (external IdP via JWKS), ``zscaler`` (OneAPI creds validated
  against ``/oauth2/v1/token``), ``api-key`` (shared secret), ``oauth-proxy``
  (stub — use a library-level provider instead).
* stdio transport is always unauthenticated (inherits OS process security).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from zscaler_mcp.common.logging import log_security_warning

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Process-wide registry of live ZscalerAuthProvider instances.
#
# The entitlement filter (``zscaler_mcp.security.entitlements``) consults this to
# reuse a bearer token the auth middleware already validated + cached in
# ``zscaler`` MCP-auth mode — avoiding a redundant ``/oauth2/v1/token`` call.
# Ported from v1 ``zscaler_mcp/auth.py``.
# ---------------------------------------------------------------------------

_zscaler_providers: list = []
_zscaler_providers_lock = threading.Lock()


def _register_zscaler_provider(provider: "ZscalerAuthProvider") -> None:
    with _zscaler_providers_lock:
        _zscaler_providers.append(provider)


def get_registered_zscaler_providers() -> list:
    """Return a snapshot of every registered :class:`ZscalerAuthProvider`.

    Returning a copy keeps the internal list private from callers.
    """
    with _zscaler_providers_lock:
        return list(_zscaler_providers)


# ---------------------------------------------------------------------------
# Reusable OneAPI token-fetch helper
# ---------------------------------------------------------------------------


def _build_token_url(vanity_domain: str, cloud: str = "production") -> str:
    """Return the ZIdentity ``/oauth2/v1/token`` URL for a vanity/cloud."""
    cloud = (cloud or "production").lower().strip()
    if cloud == "production":
        return f"https://{vanity_domain}.zslogin.net/oauth2/v1/token"
    return f"https://{vanity_domain}.zslogin{cloud}.net/oauth2/v1/token"


def fetch_oneapi_token(
    client_id: str,
    client_secret: str,
    vanity_domain: str,
    cloud: str = "production",
    *,
    timeout: float = 30.0,
) -> Tuple[Optional[str], Optional[str]]:
    """Exchange OneAPI credentials for a bearer token.

    Returns ``(access_token, error_message)`` — exactly one is non-``None``.
    """
    import requests as http_requests

    if not client_id or not client_secret or not vanity_domain:
        return None, "Missing required OneAPI credentials"

    token_url = _build_token_url(vanity_domain, cloud)
    form_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": "https://api.zscaler.com",
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        resp = http_requests.post(token_url, data=form_data, headers=headers, timeout=timeout)
    except http_requests.Timeout:
        return None, "OneAPI /token request timed out"
    except http_requests.ConnectionError as exc:
        logger.debug("Cannot reach OneAPI auth endpoint %s: %s", token_url, exc)
        return None, f"Cannot reach OneAPI auth endpoint ({exc.__class__.__name__})"
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("OneAPI /token request failed: %s", exc)
        return None, f"OneAPI /token request failed: {exc}"

    if resp.status_code == 200:
        try:
            data = resp.json()
        except ValueError:
            return None, "Invalid JSON response from OneAPI /token"
        token = data.get("access_token", "")
        if not token:
            return None, "OneAPI /token response did not include access_token"
        return token, None

    if resp.status_code in (400, 401, 403):
        return None, "Invalid OneAPI credentials"

    return None, f"OneAPI /token returned HTTP {resp.status_code}"


# ---------------------------------------------------------------------------
# Auth Provider Interface
# ---------------------------------------------------------------------------


class AuthProvider(ABC):
    """Base class for authentication providers.

    Each provider validates the ``Authorization`` header from an incoming
    HTTP request via a single :meth:`authenticate` method.
    """

    @abstractmethod
    async def authenticate(self, authorization: str) -> Tuple[bool, Optional[str]]:
        """Validate an ``Authorization`` header value.

        Returns ``(is_valid, error_message)``; ``error_message`` is ``None``
        on success.
        """
        ...

    @property
    def scheme(self) -> str:
        """The HTTP auth scheme advertised in ``WWW-Authenticate`` on 401."""
        return "Bearer"


# ---------------------------------------------------------------------------
# API Key Provider
# ---------------------------------------------------------------------------


class APIKeyAuthProvider(AuthProvider):
    """Validate requests against a pre-shared API key (constant-time compare)."""

    def __init__(self, api_key: str):
        if not api_key or not api_key.strip():
            raise ValueError(
                "ZSCALER_MCP_AUTH_API_KEY must be set and non-empty when using api-key auth mode."
            )
        self._api_key = api_key.strip()
        key_preview = hashlib.sha256(self._api_key.encode()).hexdigest()[:8]
        logger.info("API key auth provider initialized (key fingerprint: %s)", key_preview)

    async def authenticate(self, authorization: str) -> Tuple[bool, Optional[str]]:
        if not authorization:
            return False, "Missing Authorization header"

        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return False, "Expected: Authorization: Bearer <api-key>"

        token = parts[1].strip()
        if hmac.compare_digest(token, self._api_key):
            return True, None

        return False, "Invalid API key"


# ---------------------------------------------------------------------------
# JWT Auth Provider (External IdP via JWKS)
# ---------------------------------------------------------------------------


class JWTAuthProvider(AuthProvider):
    """Validate JWTs from an external IdP using cached JWKS public keys.

    Compatible with Okta, PingOne, Azure AD / Entra ID, Auth0, Keycloak,
    Cognito, Google, etc. JWKS keys are fetched once and cached for an hour
    (handles IdP key rotation); token signatures are then validated locally.
    """

    JWKS_CACHE_LIFESPAN = 3600

    def __init__(
        self,
        jwks_uri: str,
        issuer: str,
        audience: str = "zscaler-mcp-server",
        algorithms: Optional[list] = None,
    ):
        if not jwks_uri or not jwks_uri.strip():
            raise ValueError("ZSCALER_MCP_AUTH_JWKS_URI must be a valid URL.")
        if not issuer or not issuer.strip():
            raise ValueError("ZSCALER_MCP_AUTH_ISSUER must be set.")

        try:
            import jwt as pyjwt
            from jwt import PyJWKClient
        except ImportError:
            raise ImportError(
                "PyJWT is required for JWT auth mode. "
                "Install with: pip install 'PyJWT[crypto]>=2.8.0'"
            )

        self._jwt = pyjwt
        self._jwks_uri = jwks_uri.strip()
        self._issuer = issuer.strip()
        self._audience = audience
        self._algorithms = algorithms or ["RS256", "ES256"]

        try:
            self._jwks_client = PyJWKClient(
                uri=self._jwks_uri,
                cache_keys=True,
                lifespan=self.JWKS_CACHE_LIFESPAN,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize JWKS client for {jwks_uri}: {e}")

        logger.info(
            "JWT auth provider initialized (issuer=%s, audience=%s, jwks=%s)",
            issuer,
            audience,
            jwks_uri,
        )

    async def authenticate(self, authorization: str) -> Tuple[bool, Optional[str]]:
        if not authorization:
            return False, "Missing Authorization header"

        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return False, "Expected: Authorization: Bearer <jwt-token>"

        token = parts[1].strip()

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            self._jwt.decode(
                token,
                signing_key.key,
                algorithms=self._algorithms,
                issuer=self._issuer,
                audience=self._audience,
                options={"verify_exp": True, "verify_iss": True, "verify_aud": True},
            )
            return True, None
        except self._jwt.ExpiredSignatureError:
            return False, "Token has expired"
        except self._jwt.InvalidIssuerError:
            return False, f"Invalid token issuer (expected {self._issuer})"
        except self._jwt.InvalidAudienceError:
            return False, f"Invalid token audience (expected {self._audience})"
        except self._jwt.PyJWKClientError as e:
            logger.error("JWKS key retrieval failed: %s", e)
            return False, f"Failed to retrieve signing key from JWKS endpoint: {e}"
        except self._jwt.DecodeError as e:
            return False, f"Token decode error: {e}"
        except Exception as e:
            logger.error("JWT validation error: %s", e)
            return False, f"Authentication failed: {e}"


# ---------------------------------------------------------------------------
# Zscaler OneAPI Auth Provider
# ---------------------------------------------------------------------------


class ZscalerAuthProvider(AuthProvider):
    """Validate Zscaler OneAPI credentials against the ``/token`` endpoint.

    The client sends either ``Authorization: Basic base64(client_id:secret)``
    or the ``X-Zscaler-Client-ID`` / ``X-Zscaler-Client-Secret`` header pair.
    Successful validations are cached for the token lifetime (~1h) to avoid a
    round-trip to Zscaler on every MCP request. Zscaler OneAPI publishes no
    JWKS endpoint, so local verification isn't possible — hence the cache.
    """

    CACHE_EXPIRY_BUFFER_SECONDS = 60

    def __init__(self, vanity_domain: str, cloud: str = "production"):
        if not vanity_domain or not vanity_domain.strip():
            raise ValueError("ZSCALER_VANITY_DOMAIN is required for Zscaler auth mode.")

        self._vanity_domain = vanity_domain.strip()
        self._cloud = cloud.lower().strip() if cloud else "production"
        self._token_url = _build_token_url(self._vanity_domain, self._cloud)

        self._cache: Dict[str, Tuple[float, str]] = {}
        self._cache_lock = threading.Lock()

        # Register so the entitlement filter can reuse a cached token.
        _register_zscaler_provider(self)

        logger.info(
            "Zscaler OneAPI auth provider initialized (domain=%s, cloud=%s, token_url=%s)",
            self._vanity_domain,
            self._cloud,
            self._token_url,
        )

    @property
    def vanity_domain(self) -> str:
        return self._vanity_domain

    @property
    def cloud(self) -> str:
        return self._cloud

    def get_cached_token(self, client_id: str, client_secret: str) -> Optional[str]:
        """Return the cached bearer token for the given creds, or ``None``.

        Used by the entitlement filter to avoid a redundant ``/token`` call in
        ``zscaler`` MCP-auth mode where the middleware already validated and
        cached a token for these credentials. Read-only: does not evict expired
        entries.
        """
        cred_hash = self._credential_hash(client_id, client_secret)
        with self._cache_lock:
            entry = self._cache.get(cred_hash)
            if entry is None:
                return None
            valid_until, access_token = entry
            if time.time() < valid_until:
                return access_token
            return None

    @property
    def scheme(self) -> str:
        return "Basic"

    @staticmethod
    def _credential_hash(client_id: str, client_secret: str) -> str:
        raw = f"{client_id}:{client_secret}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _check_cache(self, cred_hash: str) -> Optional[bool]:
        with self._cache_lock:
            entry = self._cache.get(cred_hash)
            if entry is None:
                return None
            valid_until, _ = entry
            if time.time() < valid_until:
                return True
            del self._cache[cred_hash]
            return None

    def _validate_against_zscaler(
        self, client_id: str, client_secret: str
    ) -> Tuple[bool, Optional[str]]:
        access_token, error = fetch_oneapi_token(
            client_id=client_id,
            client_secret=client_secret,
            vanity_domain=self._vanity_domain,
            cloud=self._cloud,
        )
        if error or not access_token:
            return False, error or "Authentication failed"

        cred_hash = self._credential_hash(client_id, client_secret)
        valid_until = time.time() + 3600 - self.CACHE_EXPIRY_BUFFER_SECONDS
        with self._cache_lock:
            self._cache[cred_hash] = (valid_until, access_token)

        logger.debug("Zscaler credentials validated (client_id=%s...)", client_id[:8])
        return True, None

    def _extract_credentials_from_headers(self, headers_list: list) -> Optional[Tuple[str, str]]:
        client_id = ""
        client_secret = ""
        for key, value in headers_list:
            lower_key = key.lower() if isinstance(key, (bytes, str)) else key
            if lower_key == b"x-zscaler-client-id":
                client_id = value.decode("utf-8") if isinstance(value, bytes) else value
            elif lower_key == b"x-zscaler-client-secret":
                client_secret = value.decode("utf-8") if isinstance(value, bytes) else value
        if client_id and client_secret:
            return client_id.strip(), client_secret.strip()
        return None

    async def authenticate(
        self, authorization: str, headers_list: Optional[list] = None
    ) -> Tuple[bool, Optional[str]]:
        client_id = None
        client_secret = None

        if headers_list:
            creds = self._extract_credentials_from_headers(headers_list)
            if creds:
                client_id, client_secret = creds

        if client_id is None and authorization:
            parts = authorization.split(" ", 1)
            if len(parts) == 2 and parts[0].lower() == "basic":
                try:
                    decoded = base64.b64decode(parts[1].strip()).decode("utf-8")
                    if ":" in decoded:
                        client_id, client_secret = decoded.split(":", 1)
                except Exception:
                    return False, "Invalid Base64 encoding in Basic auth header"

        if not client_id or not client_secret:
            return False, (
                "Zscaler auth mode requires credentials. Use either:\n"
                "  1. Headers: X-Zscaler-Client-ID + X-Zscaler-Client-Secret\n"
                "  2. Header: Authorization: Basic base64(client_id:client_secret)"
            )

        cred_hash = self._credential_hash(client_id, client_secret)
        if self._check_cache(cred_hash) is True:
            return True, None

        return self._validate_against_zscaler(client_id, client_secret)


# ---------------------------------------------------------------------------
# OIDC (OAuth 2.1 against an external IdP) — env-var driven builder
# ---------------------------------------------------------------------------
#
# The server is a **resource server**, not an authorization server. It publishes
# OAuth 2.0 Protected Resource Metadata (RFC 9728) at
# ``/.well-known/oauth-protected-resource`` naming the IdP as its authorization
# server, and verifies the bearer tokens the IdP issues. The client discovers the
# IdP from that document and runs the OAuth flow directly against it; no OAuth
# endpoint is served from this process.
#
# This replaces the earlier approach of borrowing ``fastmcp``'s ``OIDCProxy``. A
# proxy existed to make the MCP server impersonate an authorization server so a
# client could run Dynamic Client Registration against *it* and have that mapped
# onto one pre-registered upstream app — a workaround for IdPs (Entra ID among
# them) that do not offer open DCR. RFC 9728 removes the need: the client is
# pointed at the real IdP. `mcp` 2.x implements the resource-server side
# (``create_protected_resource_routes``, mounted whenever ``resource_server_url``
# is set), so nothing has to be proxied, reimplemented, or installed separately.
#
# Consequences worth knowing, both good:
#   * ``fastmcp`` is not a dependency of any auth mode, so nothing asks the
#     operator to install a prerelease.
#   * No client secret is needed here. Verifying a signature requires the IdP's
#     public keys, not a credential of ours — one less secret in the deployment.


# Sentinel returned by the env-var factory to mean "auth is handled by the SDK's
# resource-server plumbing, not by AuthMiddleware". The settings are built lazily
# by :func:`build_oidc_auth_kwargs` so importing this module never requires the
# OIDC config to be present.
OIDC_SENTINEL = "__oidc__"

#: Retained spelling of the sentinel. The mode was called ``oidcproxy`` before it
#: stopped being a proxy, and the old name still resolves (see ``_OIDC_MODES``).
OIDCPROXY_SENTINEL = OIDC_SENTINEL

#: Accepted spellings of ``ZSCALER_MCP_AUTH_MODE`` for this mode. ``oidc`` is the
#: name now that nothing is proxied; the two older spellings keep working because
#: they are sitting in deployed ``.env`` files and a silent "unknown auth mode"
#: exit would be a hostile way to rename a setting.
_OIDC_MODES = ("oidc", "oidcproxy", "oauth-proxy")


class _JWKSTokenVerifier:
    """Adapts :class:`JWTAuthProvider` to the SDK's ``TokenVerifier`` protocol.

    Composition rather than a second implementation: the signature, issuer,
    audience and expiry checks are the ones the ``jwt`` auth mode has always used,
    so the two modes cannot drift apart in what they consider a valid token. Only
    the shape of the answer differs — the SDK wants an ``AccessToken`` describing
    the principal, where the middleware wanted a bool.
    """

    def __init__(self, provider: "JWTAuthProvider", *, required_scopes: Optional[list] = None):
        self._provider = provider
        self._required_scopes = required_scopes or []

    async def verify_token(self, token: str) -> Any:
        from mcp.server.auth.provider import AccessToken

        ok, error = await self._provider.authenticate(f"Bearer {token}")
        if not ok:
            # Debug, not warning: an expired token on a long-lived client session is
            # routine, and the SDK turns the None into the 401 the client acts on.
            logger.debug("OIDC token rejected: %s", error)
            return None

        # Decoded a second time, without verification, purely to read the claims —
        # `authenticate` verified them and returns only a bool. Safe because the
        # signature has already been checked above; a failure to parse here would
        # have failed there first.
        claims = self._provider._jwt.decode(token, options={"verify_signature": False})
        scopes = claims.get("scp") or claims.get("scope") or ""
        if isinstance(scopes, str):
            scopes = scopes.split()

        return AccessToken(
            token=token,
            client_id=str(claims.get("azp") or claims.get("appid") or claims.get("aud") or ""),
            scopes=list(scopes),
            expires_at=claims.get("exp"),
            subject=claims.get("sub"),
            claims=claims,
        )


def _discover_oidc_endpoints(config_url: str) -> Dict[str, str]:
    """Read ``issuer`` and ``jwks_uri`` from the IdP's OpenID configuration.

    Fetched rather than derived from the config URL by string surgery: the issuer
    in the document is the value tokens are validated against, and for several
    IdPs it is not a prefix of the discovery URL (Entra ID serves
    ``.../v2.0/.well-known/openid-configuration`` but issues ``iss:
    https://login.microsoftonline.com/<tenant>/v2.0``). Guessing would produce a
    server that rejects every token with a confusing issuer mismatch.

    A startup fetch is consistent with the ``jwt`` mode, which already builds its
    JWKS client at construction; both fail fast on a misconfigured IdP rather than
    on the first request.
    """
    import httpx2 as httpx

    try:
        response = httpx.get(config_url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        document = response.json()
    except Exception as exc:
        raise RuntimeError(
            f"Could not read the IdP's OpenID configuration from {config_url}: {exc}. "
            "Check OIDCPROXY_CONFIG_URL and that this host can reach the IdP."
        ) from exc

    missing = [key for key in ("issuer", "jwks_uri") if not document.get(key)]
    if missing:
        raise RuntimeError(
            f"The OpenID configuration at {config_url} is missing {', '.join(missing)}, "
            "so tokens could not be validated against it."
        )
    return {"issuer": document["issuer"], "jwks_uri": document["jwks_uri"]}


def build_oidc_auth_kwargs(base_url: Optional[str] = None) -> Dict[str, Any]:
    """Build ``MCPServer`` kwargs that make this server an OAuth protected resource.

    Required env vars::

        OIDCPROXY_CONFIG_URL      # IdP OpenID configuration URL
        OIDCPROXY_BASE_URL        # public base URL of THIS server (or pass base_url)

    Optional::

        OIDCPROXY_AUDIENCE        # expected token audience; defaults to
                                  # OIDCPROXY_CLIENT_ID (Entra ID puts the client
                                  # id in `aud`)
        OIDCPROXY_CLIENT_ID       # the app registration's client id
        OIDCPROXY_REQUIRED_SCOPES # comma-separated scopes a token must carry

    ``OIDCPROXY_CLIENT_SECRET`` is no longer read. Nothing here initiates an OAuth
    exchange, so there is no client credential to present; if it is still set, it
    is ignored and can be removed from the deployment.

    Returns the ``auth`` / ``token_verifier`` pair for the constructor. Never sets
    ``auth_server_provider`` — this process serves no OAuth endpoints, and the SDK
    would then mount ``/authorize``, ``/token`` and ``/register`` routes it cannot
    honour.

    Raises:
        ValueError: required configuration is missing, so the server refuses to
            start half-configured rather than serving metadata clients cannot use.
        RuntimeError: the IdP's discovery document could not be read.
    """
    from mcp.server.auth.settings import AuthSettings

    config_url = os.getenv("OIDCPROXY_CONFIG_URL", "").strip()
    client_id = os.getenv("OIDCPROXY_CLIENT_ID", "").strip()
    base = (base_url or os.getenv("OIDCPROXY_BASE_URL", "")).strip()
    audience = os.getenv("OIDCPROXY_AUDIENCE", "").strip() or client_id or None
    required_scopes_raw = os.getenv("OIDCPROXY_REQUIRED_SCOPES", "").strip()
    required_scopes = (
        [s.strip() for s in required_scopes_raw.split(",") if s.strip()]
        if required_scopes_raw
        else None
    )

    missing = [
        name
        for name, val in (
            ("OIDCPROXY_CONFIG_URL", config_url),
            ("OIDCPROXY_BASE_URL", base),
        )
        if not val
    ]
    if missing:
        raise ValueError(
            "oidc auth mode requires: "
            + ", ".join(missing)
            + ". OIDCPROXY_BASE_URL is this server's public URL, which clients use "
            "as the OAuth resource identifier."
        )
    if not audience:
        raise ValueError(
            "oidc auth mode requires OIDCPROXY_AUDIENCE (or OIDCPROXY_CLIENT_ID to "
            "default it). Without an expected audience, a token issued by the same "
            "IdP for any other application would be accepted here."
        )

    endpoints = _discover_oidc_endpoints(config_url)
    verifier = _JWKSTokenVerifier(
        JWTAuthProvider(
            jwks_uri=endpoints["jwks_uri"],
            issuer=endpoints["issuer"],
            audience=audience,
        ),
        required_scopes=required_scopes,
    )

    settings: Dict[str, Any] = {
        # The IdP is the authorization server; we only advertise it.
        "issuer_url": endpoints["issuer"],
        "resource_server_url": base,
    }
    if required_scopes:
        settings["required_scopes"] = required_scopes

    logger.info(
        "OIDC auth configured as a protected resource (issuer=%s, resource=%s, audience=%s)",
        endpoints["issuer"],
        base,
        audience,
    )
    if os.getenv("OIDCPROXY_CLIENT_SECRET", "").strip():
        logger.info(
            "OIDCPROXY_CLIENT_SECRET is set but no longer used — token verification "
            "needs the IdP's public keys, not a client credential. It can be removed."
        )

    return {"auth": AuthSettings(**settings), "token_verifier": verifier}


# ---------------------------------------------------------------------------
# ASGI Auth Middleware
# ---------------------------------------------------------------------------


class AuthMiddleware:
    """ASGI middleware that validates the ``Authorization`` header.

    Works with SSE and streamable-http transports. Operates at the ASGI level
    before any application logic, so it's compatible with streaming responses.
    Health-check and OAuth-metadata paths bypass authentication.
    """

    SKIP_PATHS = frozenset(
        {
            "/health",
            "/healthz",
            "/ready",
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-protected-resource/mcp",
            "/.well-known/oauth-authorization-server",
            "/.well-known/openid-configuration",
            "/register",
        }
    )

    def __init__(self, app: Any, provider: AuthProvider):
        self.app = app
        self.provider = provider

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        headers_list = scope.get("headers", [])
        auth_value = ""
        for key, value in headers_list:
            if key == b"authorization":
                auth_value = value.decode("utf-8", errors="replace")
                break

        if isinstance(self.provider, ZscalerAuthProvider):
            is_valid, error = await self.provider.authenticate(auth_value, headers_list)
        else:
            is_valid, error = await self.provider.authenticate(auth_value)

        if not is_valid:
            from starlette.responses import JSONResponse

            body = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": f"Unauthorized: {error or 'Authentication required'}",
                },
            }
            response = JSONResponse(
                body,
                status_code=401,
                headers={"WWW-Authenticate": self.provider.scheme},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Configuration & Factory
# ---------------------------------------------------------------------------


def _read_auth_config() -> Optional[Dict[str, str]]:
    """Read auth configuration from environment variables.

    Authentication is ENABLED by default for HTTP transports. Returns ``None``
    only when explicitly disabled. When enabled without an explicit mode, the
    best available mode is auto-detected (jwt > api-key > zscaler).
    """
    enabled = os.getenv("ZSCALER_MCP_AUTH_ENABLED", "").lower()

    if enabled in ("false", "0", "no"):
        log_security_warning(
            "MCP Client Authentication is DISABLED",
            [
                "The server will accept ALL requests without authentication.",
                "This is NOT recommended for production or network-accessible deployments.",
                "",
                "To enable authentication, set one of:",
                "  ZSCALER_MCP_AUTH_MODE=jwt     (+ JWKS_URI, ISSUER, AUDIENCE)",
                "  ZSCALER_MCP_AUTH_MODE=api-key (+ API_KEY)",
                "  ZSCALER_MCP_AUTH_MODE=zscaler (uses Zscaler API credentials)",
                "",
                "Remove ZSCALER_MCP_AUTH_ENABLED=false to re-enable.",
            ],
        )
        return None

    explicit_mode = os.getenv("ZSCALER_MCP_AUTH_MODE", "").strip().lower()

    # Explicit 'none' is an alias for disabling auth (parity with v1's mode set).
    if explicit_mode == "none":
        log_security_warning(
            "MCP Client Authentication is DISABLED (mode=none)",
            [
                "The server will accept ALL requests without authentication.",
                "This is NOT recommended for production or network-accessible deployments.",
                "Set ZSCALER_MCP_AUTH_MODE to jwt / api-key / zscaler / oidc to enable.",
            ],
        )
        return None

    if not explicit_mode:
        if os.getenv("ZSCALER_MCP_AUTH_JWKS_URI", "").strip():
            explicit_mode = "jwt"
        elif os.getenv("ZSCALER_MCP_AUTH_API_KEY", "").strip():
            explicit_mode = "api-key"
        elif os.getenv("ZSCALER_VANITY_DOMAIN", "").strip():
            explicit_mode = "zscaler"
        else:
            explicit_mode = "jwt"

    return {
        "mode": explicit_mode,
        "jwks_uri": os.getenv("ZSCALER_MCP_AUTH_JWKS_URI", ""),
        "issuer": os.getenv("ZSCALER_MCP_AUTH_ISSUER", ""),
        "audience": os.getenv("ZSCALER_MCP_AUTH_AUDIENCE", "zscaler-mcp-server"),
        "algorithms": os.getenv("ZSCALER_MCP_AUTH_ALGORITHMS", "RS256,ES256"),
        "api_key": os.getenv("ZSCALER_MCP_AUTH_API_KEY", ""),
        "vanity_domain": os.getenv("ZSCALER_VANITY_DOMAIN", ""),
        "cloud": os.getenv("ZSCALER_CLOUD", "production"),
    }


def _create_provider(config: Dict[str, str]) -> AuthProvider:
    """Instantiate an auth provider from the configuration dict."""
    mode = config["mode"]

    if mode == "api-key":
        return APIKeyAuthProvider(api_key=config["api_key"])

    if mode == "jwt":
        if not config["jwks_uri"]:
            raise ValueError("ZSCALER_MCP_AUTH_JWKS_URI is required for JWT auth mode.")
        if not config["issuer"]:
            raise ValueError("ZSCALER_MCP_AUTH_ISSUER is required for JWT auth mode.")
        algorithms = [a.strip() for a in config["algorithms"].split(",") if a.strip()]
        return JWTAuthProvider(
            jwks_uri=config["jwks_uri"],
            issuer=config["issuer"],
            audience=config["audience"],
            algorithms=algorithms,
        )

    if mode == "zscaler":
        return ZscalerAuthProvider(
            vanity_domain=config["vanity_domain"],
            cloud=config["cloud"],
        )

    raise ValueError(f"Unknown auth mode: '{mode}'. Supported: none, jwt, zscaler, api-key, oidc")


def resolve_oidc_auth() -> Optional[Dict[str, Any]]:
    """``MCPServer`` auth kwargs for the OIDC mode, or ``None`` for every other mode.

    ``None`` means "auth belongs to :func:`apply_auth_middleware` at the ASGI
    layer" — the case for ``jwt`` / ``api-key`` / ``zscaler`` and for auth being
    disabled. Only the OIDC mode needs configuration on the constructor, because
    only it publishes protected-resource metadata the SDK has to mount.

    Raises ``SystemExit`` if the mode is selected but misconfigured, so a server
    that cannot authenticate anyone never reaches the listening socket.
    """
    config = _read_auth_config()
    if config is None:  # auth explicitly disabled
        return None
    if config["mode"] not in _OIDC_MODES:
        return None
    try:
        return build_oidc_auth_kwargs()
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(
            f"ERROR: oidc auth mode is selected but misconfigured.\n  Error: {exc}\n"
        ) from exc


def apply_auth_middleware(app: Any, transport: str) -> Any:
    """Wrap an ASGI app with authentication middleware.

    No-op for stdio. Returns the original app if auth is explicitly disabled.
    Raises ``SystemExit`` if auth is enabled (default) but misconfigured —
    refusing to start an unauthenticated server by accident.
    """
    if transport == "stdio":
        return app

    config = _read_auth_config()
    if config is None:
        return app

    mode = config["mode"]

    # OIDC is wired on the MCPServer constructor instead (protected-resource
    # metadata plus the SDK's own bearer middleware), so there is nothing to wrap.
    if mode in _OIDC_MODES:
        logger.info("Auth mode '%s' — handled by the SDK's resource-server plumbing.", mode)
        return app

    try:
        provider = _create_provider(config)
    except (ValueError, RuntimeError, ImportError) as exc:
        logger.error(
            "Failed to initialize auth provider (mode=%s): %s. "
            "Configure valid auth credentials or set ZSCALER_MCP_AUTH_ENABLED=false "
            "to disable authentication (not recommended).",
            mode,
            exc,
        )
        raise SystemExit(
            f"ERROR: Authentication is enabled (default) but configuration is invalid.\n"
            f"  Mode: {mode}\n"
            f"  Error: {exc}\n\n"
            f"Either:\n"
            f"  1. Configure valid auth settings for the '{mode}' mode, or\n"
            f"  2. Set ZSCALER_MCP_AUTH_ENABLED=false to disable (not recommended)\n"
        ) from exc

    logger.info("=" * 70)
    logger.info("MCP CLIENT AUTHENTICATION ENABLED")
    logger.info("   Mode: %s", mode)
    logger.info("   Transport: %s", transport)
    if mode == "jwt":
        logger.info("   JWKS URI: %s", config["jwks_uri"])
        logger.info("   Issuer: %s", config["issuer"])
        logger.info("   Audience: %s", config["audience"])
    elif mode == "zscaler":
        logger.info("   Vanity Domain: %s", config["vanity_domain"])
        logger.info("   Cloud: %s", config["cloud"])
    elif mode == "api-key":
        logger.info("   Key configured: yes")
    logger.info("=" * 70)

    return AuthMiddleware(app, provider)
