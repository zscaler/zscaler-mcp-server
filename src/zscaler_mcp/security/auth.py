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
# OIDCProxy (library-level OAuth 2.1 + DCR) — env-var driven builder
# ---------------------------------------------------------------------------
#
# Unlike v1 (which left the env-var ``oauth-proxy`` mode as a NotImplementedError
# stub and required the operator to construct ``OIDCProxy`` in Python and pass it
# via ``auth=``), v2 supports BOTH:
#
#   1. Programmatic: pass a ``fastmcp.server.auth.AuthProvider`` to
#      ``build_server(auth=...)`` / the server constructor. Highest precedence.
#   2. Env-var: ``ZSCALER_MCP_AUTH_MODE=oidcproxy`` (alias ``oauth-proxy``) builds
#      a ``fastmcp.server.auth.oidc_proxy.OIDCProxy`` from ``OIDCPROXY_*`` env vars.
#
# Both converge on the same thing: a fastmcp ``AuthProvider`` handed to
# ``FastMCP(auth=...)``, which wires the OAuth metadata routes, the DCR
# ``/register`` endpoint, and ``RequireAuthMiddleware`` natively. The env-var
# auth middleware (``AuthMiddleware``) is bypassed entirely in this mode.


# Sentinel returned by the env-var factory to mean "auth is handled by a
# fastmcp library provider, not by AuthMiddleware". The actual provider is
# built lazily by :func:`build_oidcproxy_provider` so importing this module
# never requires the OIDC config to be present.
OIDCPROXY_SENTINEL = "__oidcproxy__"


def build_oidcproxy_provider(base_url: Optional[str] = None) -> Any:
    """Construct a fastmcp ``OIDCProxy`` from ``OIDCPROXY_*`` environment vars.

    Required env vars::

        OIDCPROXY_CONFIG_URL      # IdP OpenID configuration URL
        OIDCPROXY_CLIENT_ID       # OAuth client id registered at the IdP
        OIDCPROXY_CLIENT_SECRET   # OAuth client secret
        OIDCPROXY_BASE_URL        # public base URL of THIS server (or pass base_url)

    Optional::

        OIDCPROXY_AUDIENCE        # token audience (Entra ID: set to client_id)
        OIDCPROXY_REQUIRED_SCOPES # comma-separated required scopes

    Raises ``ValueError`` with an actionable message if required config is
    missing, so the server refuses to start half-configured.
    """
    try:
        from fastmcp.server.auth.oidc_proxy import OIDCProxy
    except ImportError as exc:  # pragma: no cover - fastmcp always installed
        raise ImportError(
            "fastmcp is required for oidcproxy auth mode. Install with: pip install fastmcp"
        ) from exc

    config_url = os.getenv("OIDCPROXY_CONFIG_URL", "").strip()
    client_id = os.getenv("OIDCPROXY_CLIENT_ID", "").strip()
    client_secret = os.getenv("OIDCPROXY_CLIENT_SECRET", "").strip()
    base = (base_url or os.getenv("OIDCPROXY_BASE_URL", "")).strip()
    audience = os.getenv("OIDCPROXY_AUDIENCE", "").strip() or None
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
            ("OIDCPROXY_CLIENT_ID", client_id),
            ("OIDCPROXY_CLIENT_SECRET", client_secret),
            ("OIDCPROXY_BASE_URL", base),
        )
        if not val
    ]
    if missing:
        raise ValueError(
            "oidcproxy auth mode requires: " + ", ".join(missing) + ". "
            "Set these env vars or pass a fastmcp AuthProvider via auth= instead."
        )

    kwargs: Dict[str, Any] = {
        "config_url": config_url,
        "client_id": client_id,
        "client_secret": client_secret,
        "base_url": base,
    }
    if audience:
        kwargs["audience"] = audience
    if required_scopes:
        kwargs["required_scopes"] = required_scopes

    logger.info(
        "OIDCProxy auth provider initialized (config_url=%s, base_url=%s, audience=%s)",
        config_url,
        base,
        audience or "(default)",
    )
    return OIDCProxy(**kwargs)


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
                "Set ZSCALER_MCP_AUTH_MODE to jwt / api-key / zscaler / oidcproxy to enable.",
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

    raise ValueError(
        f"Unknown auth mode: '{mode}'. Supported: none, jwt, zscaler, api-key, oidcproxy"
    )


def resolve_fastmcp_auth() -> Any:
    """If env-var auth mode is ``oidcproxy``, build + return a fastmcp provider.

    Returns the fastmcp ``AuthProvider`` instance for the ``oidcproxy`` /
    ``oauth-proxy`` env-var mode (to be passed to ``FastMCP(auth=...)``), or
    ``None`` for every other mode (where ``apply_auth_middleware`` handles auth
    at the ASGI layer instead). ``None`` is also returned when auth is disabled.

    Raises ``SystemExit`` if oidcproxy mode is selected but misconfigured.
    """
    config = _read_auth_config()
    if config is None:  # auth explicitly disabled
        return None
    mode = config["mode"]
    if mode not in ("oidcproxy", "oauth-proxy"):
        return None
    try:
        return build_oidcproxy_provider()
    except (ValueError, ImportError) as exc:
        raise SystemExit(
            f"ERROR: oidcproxy auth mode is selected but misconfigured.\n  Error: {exc}\n"
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

    # oidcproxy is handled natively by FastMCP(auth=...) — the OAuth routes and
    # RequireAuthMiddleware are wired into the app there, not here.
    if mode in ("oidcproxy", "oauth-proxy"):
        logger.info("Auth mode 'oidcproxy' — handled by the fastmcp auth provider (auth=).")
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
