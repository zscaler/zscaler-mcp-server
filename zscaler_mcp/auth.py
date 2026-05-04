"""
MCP-level authentication for the Zscaler MCP Server.

Authentication is ENABLED by default for HTTP transports (zero-trust posture).
To disable, set ZSCALER_MCP_AUTH_ENABLED=false (prints security warning).

Supports multiple authentication modes configured via environment variables:

    ZSCALER_MCP_AUTH_MODE=jwt|zscaler|api-key|oauth-proxy

When no explicit mode is set, auto-detection selects the best available:
    1. ZSCALER_MCP_AUTH_JWKS_URI set  -> jwt mode
    2. ZSCALER_MCP_AUTH_API_KEY set   -> api-key mode
    3. ZSCALER_VANITY_DOMAIN set      -> zscaler mode

Modes:
    jwt         - Validate JWTs from external IdP via JWKS
                  (Okta, PingOne, Azure AD, Auth0, Keycloak, AWS Cognito, etc.)
    zscaler     - Validate Zscaler OneAPI credentials via /token endpoint
    api-key     - Simple shared secret comparison
    oauth-proxy - Full MCP-spec OAuth 2.1 proxy with DCR (Phase 2)

Auth only applies to HTTP-based transports (SSE and streamable-http).
The stdio transport is always unauthenticated (inherits OS-level process security).
"""

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
# Process-wide registry of ZscalerAuthProvider instances.
#
# The entitlement filter (zscaler_mcp.common.entitlements) consults this
# registry at server startup to look up an already-cached OneAPI bearer
# token before issuing its own /oauth2/v1/token call. This avoids
# duplicating the call the auth middleware already made when the user
# authenticates via Zscaler mode.
# ---------------------------------------------------------------------------

_zscaler_providers: list = []
_zscaler_providers_lock = threading.Lock()


def _register_zscaler_provider(provider: "ZscalerAuthProvider") -> None:
    with _zscaler_providers_lock:
        _zscaler_providers.append(provider)


def get_registered_zscaler_providers() -> list:
    """Return a snapshot of every registered :class:`ZscalerAuthProvider`.

    Used by :mod:`zscaler_mcp.common.entitlements` to discover any
    already-cached bearer token. Returning a copy keeps the internal
    list private from callers.
    """
    with _zscaler_providers_lock:
        return list(_zscaler_providers)


# ---------------------------------------------------------------------------
# Reusable OneAPI token-fetch helper.
#
# Centralized so both ZscalerAuthProvider (per-request validation) and
# the entitlement filter (one-shot at startup) hit the same code path.
# ---------------------------------------------------------------------------


def _build_token_url(vanity_domain: str, cloud: str = "production") -> str:
    """Return the ZIdentity ``/oauth2/v1/token`` URL for a given vanity/cloud.

    Mirrors the URL builder used by :class:`ZscalerAuthProvider` so that
    cache-lookup keys and direct fetch URLs stay in lock-step.
    """
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

    Performs a synchronous POST to ZIdentity's ``/oauth2/v1/token``
    endpoint and returns ``(access_token, error_message)``. Exactly one
    of the two return values is non-``None``.

    This is intentionally a free function (not a method) so callers
    that don't need a full :class:`ZscalerAuthProvider` lifecycle (e.g.
    the entitlement filter at server startup) can use it directly.
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

    Each provider implements a single authenticate() method that validates
    the Authorization header from an incoming HTTP request.
    """

    @abstractmethod
    async def authenticate(self, authorization: str) -> Tuple[bool, Optional[str]]:
        """Validate an Authorization header value.

        Args:
            authorization: The full Authorization header value
                           (e.g., "Bearer xxx" or "Basic xxx").

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None on success.
        """
        ...

    @property
    def scheme(self) -> str:
        """The HTTP auth scheme advertised in WWW-Authenticate on 401."""
        return "Bearer"


# ---------------------------------------------------------------------------
# API Key Provider
# ---------------------------------------------------------------------------


class APIKeyAuthProvider(AuthProvider):
    """Validates requests against a pre-shared API key.

    Configuration:
        ZSCALER_MCP_AUTH_MODE=api-key
        ZSCALER_MCP_AUTH_API_KEY=sk-your-secret-key-here

    The MCP client sends:
        Authorization: Bearer sk-your-secret-key-here

    The server compares using constant-time comparison to prevent
    timing attacks. No external calls, no IdP, no token expiry.
    """

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
    """Validates JWTs from an external IdP using cached JWKS public keys.

    Configuration:
        ZSCALER_MCP_AUTH_MODE=jwt
        ZSCALER_MCP_AUTH_JWKS_URI=https://your-idp.com/.well-known/jwks.json
        ZSCALER_MCP_AUTH_ISSUER=https://your-idp.com
        ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
        ZSCALER_MCP_AUTH_ALGORITHMS=RS256,ES256   (optional, default: RS256,ES256)

    Compatible JWKS endpoints:
        Okta       https://{domain}.okta.com/oauth2/default/v1/keys
        PingOne    https://auth.pingone.com/{envId}/as/jwks
        Azure AD   https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys
        Auth0      https://{domain}.auth0.com/.well-known/jwks.json
        Keycloak   https://{host}/realms/{realm}/protocol/openid-connect/certs
        Cognito    https://cognito-idp.{region}.amazonaws.com/{pool}/.well-known/jwks.json
        Google     https://www.googleapis.com/oauth2/v3/certs

    The MCP client sends:
        Authorization: Bearer eyJhbGciOiJSUzI1NiIs...

    The server fetches the IdP's public keys once (JWKS) and validates
    token signatures locally. No per-request calls to the IdP.
    """

    # Re-fetch JWKS keys every hour (handles key rotation at the IdP)
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
                options={
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
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
    """Validates Zscaler OneAPI credentials against the /token endpoint.

    Configuration:
        ZSCALER_MCP_AUTH_MODE=zscaler
        ZSCALER_VANITY_DOMAIN=customer.zscloud.net
        ZSCALER_CLOUD=production               (optional, default: production)

    The MCP client sends:
        Authorization: Basic base64(client_id:client_secret)

    The server decodes the credentials and validates them by calling
    Zscaler's /oauth2/v1/token endpoint. Successful validations are
    cached for the token's lifetime (typically 1 hour) to avoid
    repeated calls to Zscaler on every MCP request.

    Important: Zscaler OneAPI does NOT publish a JWKS endpoint, so
    local token verification is not possible. The server must call
    the /token endpoint to validate credentials (once per cache period).
    """

    # Refresh cache 60 seconds before actual token expiry
    CACHE_EXPIRY_BUFFER_SECONDS = 60

    def __init__(
        self,
        vanity_domain: str,
        cloud: str = "production",
    ):
        if not vanity_domain or not vanity_domain.strip():
            raise ValueError("ZSCALER_VANITY_DOMAIN is required for Zscaler auth mode.")

        self._vanity_domain = vanity_domain.strip()
        self._cloud = cloud.lower().strip() if cloud else "production"
        self._token_url = self._build_token_url()

        # Thread-safe cache: sha256(credentials) -> (valid_until_ts, access_token)
        self._cache: Dict[str, Tuple[float, str]] = {}
        self._cache_lock = threading.Lock()

        # Register this provider so other components (entitlement filter)
        # can look up cached tokens without making redundant /token calls.
        _register_zscaler_provider(self)

        logger.info(
            "Zscaler OneAPI auth provider initialized (domain=%s, cloud=%s, token_url=%s)",
            self._vanity_domain,
            self._cloud,
            self._token_url,
        )

    @property
    def vanity_domain(self) -> str:
        """The configured vanity domain (read-only public accessor)."""
        return self._vanity_domain

    @property
    def cloud(self) -> str:
        """The configured cloud environment (read-only public accessor)."""
        return self._cloud

    def get_cached_token(self, client_id: str, client_secret: str) -> Optional[str]:
        """Return the cached bearer token for the given creds, or ``None``.

        Used by the entitlement filter to avoid a redundant ``/token`` call
        in ``zscaler`` MCP-auth mode where the auth middleware has already
        validated and cached a token for these credentials.

        Returns the token string if a non-expired entry exists, otherwise
        ``None`` (without removing the entry — read-only).
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

    def _build_token_url(self) -> str:
        if self._cloud == "production":
            return f"https://{self._vanity_domain}.zslogin.net/oauth2/v1/token"
        return f"https://{self._vanity_domain}.zslogin{self._cloud}.net/oauth2/v1/token"

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
        """Call Zscaler's /oauth2/v1/token to validate credentials.

        Delegates the actual HTTP exchange to :func:`fetch_oneapi_token`
        (the same helper the entitlement filter uses) and then caches
        the token for subsequent MCP requests.
        """
        access_token, error = fetch_oneapi_token(
            client_id=client_id,
            client_secret=client_secret,
            vanity_domain=self._vanity_domain,
            cloud=self._cloud,
        )
        if error or not access_token:
            return False, error or "Authentication failed"

        # Token TTL isn't returned by fetch_oneapi_token (we keep its
        # surface minimal). Use the conservative default of 1 hour minus
        # the buffer — the next MCP request will simply re-validate if
        # the real TTL was shorter.
        cred_hash = self._credential_hash(client_id, client_secret)
        valid_until = time.time() + 3600 - self.CACHE_EXPIRY_BUFFER_SECONDS

        with self._cache_lock:
            self._cache[cred_hash] = (valid_until, access_token)

        logger.debug(
            "Zscaler credentials validated (client_id=%s...)",
            client_id[:8],
        )
        return True, None

    def _extract_credentials_from_headers(self, headers_list: list) -> Optional[Tuple[str, str]]:
        """Extract credentials from X-Zscaler-Client-ID / X-Zscaler-Client-Secret headers."""
        client_id = ""
        client_secret = ""
        for key, value in headers_list:
            lower_key = key.lower() if isinstance(key, str) else key
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

        # Method 1: X-Zscaler-Client-ID + X-Zscaler-Client-Secret headers (no encoding needed)
        if headers_list:
            creds = self._extract_credentials_from_headers(headers_list)
            if creds:
                client_id, client_secret = creds

        # Method 2: Authorization: Basic base64(client_id:client_secret)
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
        cached = self._check_cache(cred_hash)
        if cached is True:
            return True, None

        return self._validate_against_zscaler(client_id, client_secret)


# ---------------------------------------------------------------------------
# OAuth Proxy Auth Provider (Phase 2)
# ---------------------------------------------------------------------------


class OAuthProxyAuthProvider(AuthProvider):
    """Full MCP-spec OAuth 2.1 proxy with Dynamic Client Registration.

    Provides MCP-spec-compliant OAuth endpoints:
        /.well-known/oauth-protected-resource   Resource metadata
        /.well-known/oauth-authorization-server  Auth server metadata
        /register                                Dynamic Client Registration
        /authorize                               Proxied to external IdP
        /token                                   Proxied to external IdP

    This bridges the gap between MCP clients (which expect DCR) and
    enterprise IdPs (which require manual app registration).

    **Recommended alternative:** Instead of using ``ZSCALER_MCP_AUTH_MODE=oauth-proxy``
    (this env-var-based stub), pass a ``fastmcp.server.auth.AuthProvider`` directly
    to the ``ZscalerMCPServer`` constructor via the ``auth=`` parameter::

        from fastmcp.server.auth.oidc_proxy import OIDCProxy

        auth = OIDCProxy(
            config_url="https://accounts.google.com/.well-known/openid-configuration",
            client_id="YOUR_CLIENT_ID",
            client_secret="YOUR_CLIENT_SECRET",
            base_url="http://localhost:8000",
        )
        server = ZscalerMCPServer(auth=auth)

    The ``auth=`` parameter provides full MCP-spec OAuth 2.1 with DCR using
    the fastmcp library and is production-ready.

    Status: This env-var stub is deprecated in favour of ``auth=``.
    """

    def __init__(self, **kwargs: Any):
        raise NotImplementedError(
            "The 'oauth-proxy' env-var mode is not implemented. "
            "Use the auth= parameter on ZscalerMCPServer instead:\n\n"
            "  from fastmcp.server.auth.oidc_proxy import OIDCProxy\n"
            "  auth = OIDCProxy(config_url=..., client_id=..., client_secret=..., base_url=...)\n"
            "  server = ZscalerMCPServer(auth=auth)\n\n"
            "Available env-var modes: 'jwt', 'zscaler', 'api-key'."
        )

    async def authenticate(self, authorization: str) -> Tuple[bool, Optional[str]]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# ASGI Auth Middleware
# ---------------------------------------------------------------------------


class AuthMiddleware:
    """ASGI middleware that validates the Authorization header.

    Works with both SSE and streamable-http transports. Operates at the
    ASGI level before any application logic runs, so it's compatible with
    streaming responses.

    Certain paths bypass authentication (health checks, OAuth metadata
    endpoints for Phase 2).
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

    Authentication is ENABLED by default for HTTP transports (zero-trust).
    To disable, users must explicitly set ZSCALER_MCP_AUTH_ENABLED=false.

    When auth is enabled but no explicit mode is configured, the server
    auto-detects the best available mode:
        1. ZSCALER_MCP_AUTH_JWKS_URI set  -> jwt mode
        2. ZSCALER_MCP_AUTH_API_KEY set   -> api-key mode
        3. ZSCALER_VANITY_DOMAIN set      -> zscaler mode (Layer 2 creds as Layer 1)
        4. None of the above              -> returns config with mode for caller to handle

    Returns None only if auth is explicitly disabled.
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
        # JWT mode
        "jwks_uri": os.getenv("ZSCALER_MCP_AUTH_JWKS_URI", ""),
        "issuer": os.getenv("ZSCALER_MCP_AUTH_ISSUER", ""),
        "audience": os.getenv("ZSCALER_MCP_AUTH_AUDIENCE", "zscaler-mcp-server"),
        "algorithms": os.getenv("ZSCALER_MCP_AUTH_ALGORITHMS", "RS256,ES256"),
        # API key mode
        "api_key": os.getenv("ZSCALER_MCP_AUTH_API_KEY", ""),
        # Zscaler mode (reuses existing ZSCALER_VANITY_DOMAIN / ZSCALER_CLOUD)
        "vanity_domain": os.getenv("ZSCALER_VANITY_DOMAIN", ""),
        "cloud": os.getenv("ZSCALER_CLOUD", "production"),
        # OAuth proxy mode (Phase 2)
        "authorization_url": os.getenv("ZSCALER_MCP_AUTH_AUTHORIZATION_URL", ""),
        "token_url": os.getenv("ZSCALER_MCP_AUTH_TOKEN_URL", ""),
        "oauth_client_id": os.getenv("ZSCALER_MCP_AUTH_OAUTH_CLIENT_ID", ""),
        "oauth_client_secret": os.getenv("ZSCALER_MCP_AUTH_OAUTH_CLIENT_SECRET", ""),
        "base_url": os.getenv("ZSCALER_MCP_AUTH_BASE_URL", ""),
    }


def _create_provider(config: Dict[str, str]) -> AuthProvider:
    """Instantiate an auth provider from the configuration dict."""
    mode = config["mode"]

    if mode == "api-key":
        return APIKeyAuthProvider(api_key=config["api_key"])

    elif mode == "jwt":
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

    elif mode == "zscaler":
        return ZscalerAuthProvider(
            vanity_domain=config["vanity_domain"],
            cloud=config["cloud"],
        )

    elif mode == "oauth-proxy":
        return OAuthProxyAuthProvider()

    else:
        raise ValueError(
            f"Unknown auth mode: '{mode}'. Supported: jwt, zscaler, api-key, oauth-proxy"
        )


def apply_auth_middleware(app: Any, transport: str) -> Any:
    """Wrap an ASGI app with authentication middleware.

    Authentication is ENABLED by default for HTTP transports (zero-trust).
    Users must explicitly set ZSCALER_MCP_AUTH_ENABLED=false to disable.

    This is the main entry point called from server.py / web_server.py.
    It reads the auth configuration from environment variables, creates
    the appropriate provider, and wraps the ASGI app.

    Args:
        app: The ASGI application (from FastMCP's streamable_http_app()
             or sse_app()).
        transport: The transport type ("stdio", "sse", "streamable-http").

    Returns:
        The original app if auth is explicitly disabled or transport is stdio.
        The wrapped app with AuthMiddleware if auth is enabled.
    """
    if transport == "stdio":
        return app

    config = _read_auth_config()
    if config is None:
        return app

    mode = config["mode"]

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
