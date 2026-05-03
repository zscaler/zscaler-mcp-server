"""
Zscaler Integrations MCP Server - Main entry point

This module provides the main server class for the Zscaler Integrations MCP Server
and serves as the entry point for the application.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional, Set

import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from zscaler_mcp import services
from zscaler_mcp.common.logging import configure_logging, get_logger, log_security_warning


def _safe_toolset_for(tool_name: str) -> Optional[str]:
    """Return the toolset id for a tool name, or ``None`` if unmapped.

    Used by :meth:`ZscalerMCPServer.zscaler_enable_toolset` so an
    unmapped tool silently skips registration instead of raising.
    """
    from zscaler_mcp.common.toolsets import toolset_for_tool

    try:
        return toolset_for_tool(tool_name)
    except KeyError:
        return None

# Import version from package metadata
try:
    from importlib.metadata import version

    __version__ = version("zscaler-mcp")
except ImportError:
    # Fallback for Python < 3.8
    try:
        from importlib_metadata import version

        __version__ = version("zscaler-mcp")
    except ImportError:
        # Final fallback - read from pyproject.toml or use a default
        __version__ = "0.2.2"

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)


def _get_tls_config() -> dict:
    """Build TLS/SSL kwargs for uvicorn from environment variables.

    Env vars:
        ZSCALER_MCP_TLS_CERTFILE          - Path to PEM certificate file
        ZSCALER_MCP_TLS_KEYFILE           - Path to PEM private key file
        ZSCALER_MCP_TLS_KEYFILE_PASSWORD  - Password for encrypted key (optional)
        ZSCALER_MCP_TLS_CA_CERTS          - CA bundle for client cert validation (optional)

    Returns empty dict if TLS is not configured.
    Raises SystemExit if configuration is incomplete.
    """
    certfile = os.environ.get("ZSCALER_MCP_TLS_CERTFILE", "").strip()
    keyfile = os.environ.get("ZSCALER_MCP_TLS_KEYFILE", "").strip()

    if not certfile and not keyfile:
        return {}

    if bool(certfile) != bool(keyfile):
        raise SystemExit(
            "ERROR: Incomplete TLS configuration.\n"
            "Both ZSCALER_MCP_TLS_CERTFILE and ZSCALER_MCP_TLS_KEYFILE must be set.\n"
            f"  ZSCALER_MCP_TLS_CERTFILE = {'(set)' if certfile else '(missing)'}\n"
            f"  ZSCALER_MCP_TLS_KEYFILE  = {'(set)' if keyfile else '(missing)'}\n"
        )

    if not os.path.isfile(certfile):
        raise SystemExit(f"ERROR: TLS certificate file not found: {certfile}")
    if not os.path.isfile(keyfile):
        raise SystemExit(f"ERROR: TLS key file not found: {keyfile}")

    tls_kwargs: dict = {
        "ssl_certfile": certfile,
        "ssl_keyfile": keyfile,
    }

    password = os.environ.get("ZSCALER_MCP_TLS_KEYFILE_PASSWORD", "").strip()
    if password:
        tls_kwargs["ssl_keyfile_password"] = password

    ca_certs = os.environ.get("ZSCALER_MCP_TLS_CA_CERTS", "").strip()
    if ca_certs:
        if not os.path.isfile(ca_certs):
            raise SystemExit(f"ERROR: TLS CA certificate file not found: {ca_certs}")
        tls_kwargs["ssl_ca_certs"] = ca_certs

    return tls_kwargs


def _is_http_allowed() -> bool:
    """Check whether plaintext HTTP is explicitly permitted on non-localhost.

    Returns True only when the operator has consciously opted in via
    ZSCALER_MCP_ALLOW_HTTP=true.  All other values (missing, empty, "false")
    mean "HTTPS required".
    """
    return os.environ.get("ZSCALER_MCP_ALLOW_HTTP", "").strip().lower() in ("true", "1", "yes")


def _enforce_https_policy(host: str, port: int, tls_kwargs: dict) -> None:
    """Block startup when running plaintext HTTP on a non-localhost interface.

    The server defaults to HTTPS-required for remote deployments.  Operators
    must set ZSCALER_MCP_ALLOW_HTTP=true to opt in to plaintext HTTP.
    """
    is_localhost = host in ("127.0.0.1", "localhost", "::1")
    if tls_kwargs or is_localhost or _is_http_allowed():
        return

    raise SystemExit(
        "ERROR: HTTPS is required for non-localhost deployments.\n"
        f"The server is configured to listen on {host}:{port} without TLS.\n\n"
        "Options:\n"
        "  1. Provide TLS certificates (recommended):\n"
        "       ZSCALER_MCP_TLS_CERTFILE=/path/to/cert.pem\n"
        "       ZSCALER_MCP_TLS_KEYFILE=/path/to/key.pem\n\n"
        "  2. Terminate TLS at a reverse proxy (nginx, ALB, etc.) and\n"
        "     explicitly allow plaintext HTTP behind it:\n"
        "       ZSCALER_MCP_ALLOW_HTTP=true\n\n"
        "  3. If the MCP client and server share the same trusted L3 network\n"
        "     (e.g. traffic is already encrypted by ZPA or a VPN), you may\n"
        "     explicitly allow plaintext HTTP:\n"
        "       ZSCALER_MCP_ALLOW_HTTP=true\n"
    )


def _get_allowed_source_ips() -> list[str] | None:
    """Read ZSCALER_MCP_ALLOWED_SOURCE_IPS from the environment.

    Returns a list of allowed CIDR/IP strings, or None if the variable is
    not set (meaning "no application-level source-IP filtering — defer to
    upstream firewall / security groups").
    """
    raw = os.environ.get("ZSCALER_MCP_ALLOWED_SOURCE_IPS", "").strip()
    if not raw:
        return None
    return [s.strip() for s in raw.split(",") if s.strip()]


def _ip_matches(client_ip: str, allowed: list[str]) -> bool:
    """Check whether *client_ip* matches any entry in *allowed*.

    Supports:
        - exact IPv4/IPv6 addresses  ("10.0.0.5")
        - CIDR notation              ("10.0.0.0/24")
        - wildcard                   ("0.0.0.0/0" or "*")
    """
    import ipaddress

    if "*" in allowed or "0.0.0.0/0" in allowed:
        return True

    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in allowed:
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if addr == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue
    return False


class SourceIPMiddleware:
    """ASGI middleware that restricts access by client source IP.

    When ZSCALER_MCP_ALLOWED_SOURCE_IPS is set, only requests from those
    IPs / CIDRs are accepted.  Everything else gets 403.

    Health-check paths are exempt so load-balancer probes still work.
    """

    SKIP_PATHS = frozenset({"/health", "/healthz", "/ready"})

    def __init__(self, app, allowed_ips: list[str]):
        self.app = app
        self.allowed_ips = allowed_ips

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else ""

        if not _ip_matches(client_ip, self.allowed_ips):
            from starlette.responses import JSONResponse

            body = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": f"Forbidden: source IP {client_ip} is not in the allowed list",
                },
            }
            response = JSONResponse(body, status_code=403)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _log_tool_surface(server: "ZscalerMCPServer") -> None:
    """Log a tool-surface banner: toolsets, entitlement filter, audit logging.

    This block is companion to the security posture banner and surfaces
    the configuration that determines *which* tools the server will
    expose to clients. It deliberately avoids logging anything that
    identifies the tenant (no client_id, vanity domain, or customer ID)
    so the banner is safe to ship to centralised log stores.
    """
    w = 72
    bar = "=" * w

    try:
        from zscaler_mcp.common.toolsets import META_TOOLSET_ID, TOOLSETS

        total_registered = len(TOOLSETS.all_ids())
    except Exception:  # pragma: no cover - defensive
        META_TOOLSET_ID = "meta"
        total_registered = 0

    selected = server.selected_toolsets or set()
    active_count = len(selected)
    non_meta = sorted(s for s in selected if s != META_TOOLSET_ID)
    if not non_meta:
        toolset_detail = "(meta only)"
    elif len(non_meta) <= 4:
        toolset_detail = ", ".join(non_meta)
    else:
        toolset_detail = ", ".join(non_meta[:4]) + f", +{len(non_meta) - 4} more"

    state = server.entitlement_filter_state
    if state == "disabled":
        ent_line = "DISABLED (operator opt-out)"
        ent_detail = None
    elif state == "skipped":
        ent_line = "SKIPPED (filter not applied)"
        ent_detail = server.entitlement_filter_summary
    elif state == "error":
        ent_line = "ERROR (filter not applied)"
        ent_detail = server.entitlement_filter_summary
    else:
        kept = server.entitlement_kept_count
        removed = server.entitlement_removed_count
        if kept is None:
            ent_line = "ENABLED"
        elif removed:
            ent_line = f"ENABLED (kept {kept}, removed {removed})"
        else:
            ent_line = f"ENABLED (kept {kept}, removed 0)"
        if server.entitled_services:
            ent_detail = "Entitled services: " + ", ".join(server.entitled_services)
        else:
            ent_detail = None

    try:
        from zscaler_mcp.common.tool_helpers import is_tool_call_logging_enabled

        audit_status = "ENABLED" if is_tool_call_logging_enabled() else "DISABLED"
    except Exception:  # pragma: no cover - defensive
        audit_status = "UNKNOWN"

    try:
        from zscaler_mcp.common.sanitize import is_sanitization_enabled

        sanitize_status = "ENABLED" if is_sanitization_enabled() else "DISABLED (operator opt-out)"
    except Exception:  # pragma: no cover - defensive
        sanitize_status = "UNKNOWN"

    logger.info(bar)
    logger.info("  ZSCALER MCP SERVER — TOOL SURFACE")
    logger.info("")
    logger.info("  Toolsets:           %d active / %d registered", active_count, total_registered)
    logger.info("    Active:           %s", toolset_detail)
    logger.info("  Entitlement Filter: %s", ent_line)
    if ent_detail:
        logger.info("    %s", ent_detail)
    logger.info("  Output Sanitizer:   %s", sanitize_status)
    logger.info("  Audit Logging:      %s", audit_status)
    logger.info(bar)


def _log_security_posture(
    transport: str,
    scheme: str,
    host: str,
    port: int,
    tls_kwargs: dict,
    fastmcp_auth: object = None,
    server: "ZscalerMCPServer | None" = None,
) -> None:
    """Log a consolidated security posture banner at startup.

    When ``server`` is provided, an additional "TOOL SURFACE" block is
    emitted below the security posture summarising toolset selection,
    OneAPI entitlement filter outcome, and audit logging state. The
    block is omitted (no error) when ``server`` is ``None``.
    """
    w = 72
    bar = "=" * w

    tls_status = "ENABLED (encrypted)" if tls_kwargs else "DISABLED (plaintext)"
    if tls_kwargs:
        tls_detail = tls_kwargs.get("ssl_certfile", "")
        mtls = "Yes" if tls_kwargs.get("ssl_ca_certs") else "No"
    else:
        tls_detail = ""
        mtls = "N/A"

    if fastmcp_auth is not None:
        auth_status = "ENABLED"
        auth_mode = f"OIDCProxy ({type(fastmcp_auth).__name__}) — OAuth 2.1 + DCR"
    else:
        auth_disabled = os.environ.get("ZSCALER_MCP_AUTH_ENABLED", "").lower() in (
            "false",
            "0",
            "no",
        )
        if auth_disabled:
            auth_status = "DISABLED"
            auth_mode = "N/A"
        else:
            auth_mode = os.environ.get("ZSCALER_MCP_AUTH_MODE", "").strip().lower()
            if not auth_mode:
                if os.environ.get("ZSCALER_MCP_AUTH_JWKS_URI", "").strip():
                    auth_mode = "jwt (auto-detected)"
                elif os.environ.get("ZSCALER_MCP_AUTH_API_KEY", "").strip():
                    auth_mode = "api-key (auto-detected)"
                elif os.environ.get("ZSCALER_VANITY_DOMAIN", "").strip():
                    auth_mode = "zscaler (auto-detected)"
                else:
                    auth_mode = "jwt (default)"
            auth_status = "ENABLED"

    host_disabled = os.environ.get("ZSCALER_MCP_DISABLE_HOST_VALIDATION", "").lower() in (
        "true",
        "1",
        "yes",
    )
    allowed_hosts = os.environ.get("ZSCALER_MCP_ALLOWED_HOSTS", "").strip()
    if host_disabled:
        host_status = "DISABLED"
    elif allowed_hosts:
        host_status = f"ENABLED (allowlist: {allowed_hosts})"
    else:
        host_status = "ENABLED (localhost only)"

    confirmation_skip = os.environ.get("ZSCALER_MCP_SKIP_CONFIRMATIONS", "").lower() == "true"
    confirm_status = "DISABLED (skip)" if confirmation_skip else "ENABLED (HMAC-bound tokens)"

    is_localhost = host in ("127.0.0.1", "localhost", "::1")
    if tls_kwargs:
        http_policy = "N/A (TLS active)"
    elif is_localhost:
        http_policy = "ALLOWED (localhost)"
    elif _is_http_allowed():
        http_policy = "ALLOWED (explicit opt-in)"
    else:
        http_policy = "BLOCKED (default)"

    src_ips = _get_allowed_source_ips()
    if src_ips is None:
        src_ip_status = "DISABLED (defer to firewall/SG)"
    elif "*" in src_ips or "0.0.0.0/0" in src_ips:
        src_ip_status = "ALLOW ALL (0.0.0.0/0)"
    else:
        src_ip_status = f"ENABLED ({', '.join(src_ips)})"

    logger.info(bar)
    logger.info("  ZSCALER MCP SERVER — SECURITY POSTURE")
    logger.info("")
    logger.info("  Endpoint:       %s://%s:%d/mcp", scheme, host, port)
    logger.info("  Transport:      %s", transport)
    logger.info("")
    logger.info("  TLS Encryption: %s", tls_status)
    if tls_detail:
        logger.info("    Certificate:  %s", tls_detail)
        logger.info("    Mutual TLS:   %s", mtls)
    logger.info("  HTTP Policy:    %s", http_policy)
    logger.info("  Authentication: %s", auth_status)
    if auth_status != "DISABLED":
        logger.info("    Mode:         %s", auth_mode)
    logger.info("  Host Validation:%s", host_status)
    logger.info("  Source IP ACL:  %s", src_ip_status)
    logger.info("  Confirmations:  %s", confirm_status)
    logger.info(bar)

    if server is not None:
        _log_tool_surface(server)


def _validate_host_config(host: str) -> None:
    """Ensure host validation is configured when binding to a public interface.

    Called in run() to catch the edge case where __init__ received a different
    host than run() (e.g. programmatic use).
    """
    if host != "0.0.0.0":
        return
    disable = os.environ.get("ZSCALER_MCP_DISABLE_HOST_VALIDATION", "").strip().lower()
    allowed = os.environ.get("ZSCALER_MCP_ALLOWED_HOSTS", "").strip()
    if disable in ("true", "1", "yes") or allowed:
        return
    raise SystemExit(
        "ERROR: Cannot bind to 0.0.0.0 without host validation configuration.\n"
        "Set one of:\n"
        "  ZSCALER_MCP_ALLOWED_HOSTS=your-host:*,localhost:*  (recommended)\n"
        "  ZSCALER_MCP_DISABLE_HOST_VALIDATION=true           (disables protection)\n"
    )


def _get_transport_security(host: str | None = None) -> TransportSecuritySettings | None:
    """Build transport security settings for HTTP transports from environment.

    Host header validation is ENABLED by default (zero-trust posture).
    To disable, users must explicitly set ZSCALER_MCP_DISABLE_HOST_VALIDATION=true.

    Configuration options:

    - ZSCALER_MCP_ALLOWED_HOSTS=34.201.19.115:*,localhost:* : Comma-separated
      list of allowed Host values (recommended for production).

    - ZSCALER_MCP_DISABLE_HOST_VALIDATION=true : Disable Host header validation
      entirely (prints security warning; use only for dev/testing).

    When binding to 0.0.0.0 without ZSCALER_MCP_ALLOWED_HOSTS or an explicit
    disable, the server will refuse to start and log an error with instructions.

    Returns:
        TransportSecuritySettings or None (use FastMCP default for localhost).
    """
    disable = os.environ.get("ZSCALER_MCP_DISABLE_HOST_VALIDATION", "").strip().lower()
    if disable in ("true", "1", "yes"):
        log_security_warning(
            "Host Header Validation is DISABLED",
            [
                "The server is vulnerable to DNS rebinding attacks.",
                "This is NOT recommended for production deployments.",
                "",
                "To enable, set ZSCALER_MCP_ALLOWED_HOSTS with your expected hostnames.",
                "Remove ZSCALER_MCP_DISABLE_HOST_VALIDATION=true to re-enable.",
            ],
        )
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    allowed = os.environ.get("ZSCALER_MCP_ALLOWED_HOSTS", "").strip()
    if allowed:
        hosts = [h.strip() for h in allowed.split(",") if h.strip()]
        if hosts:
            logger.info("Host header allowlist: %s", hosts)
            tls_active = bool(_get_tls_config())
            if tls_active:
                origins = [f"https://{h}" for h in hosts]
            else:
                origins = [f"http://{h}" for h in hosts]
            return TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=hosts,
                allowed_origins=origins,
            )

    if host == "0.0.0.0":
        logger.error(
            "Binding to 0.0.0.0 requires explicit host validation configuration. "
            "Set ZSCALER_MCP_ALLOWED_HOSTS (recommended) or "
            "ZSCALER_MCP_DISABLE_HOST_VALIDATION=true to proceed."
        )
        raise SystemExit(
            "ERROR: Cannot bind to 0.0.0.0 without host validation configuration.\n"
            "Set one of:\n"
            "  ZSCALER_MCP_ALLOWED_HOSTS=your-host:*,localhost:*  (recommended)\n"
            "  ZSCALER_MCP_DISABLE_HOST_VALIDATION=true           (disables protection)\n"
        )

    return None


class ZscalerMCPServer:
    """Main server class for the Zscaler Integrations MCP Server."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        customer_id: Optional[str] = None,
        vanity_domain: Optional[str] = None,
        cloud: Optional[str] = None,
        debug: bool = False,
        enabled_services: Optional[Set[str]] = None,
        enabled_tools: Optional[Set[str]] = None,
        user_agent_comment: Optional[str] = None,
        enable_write_tools: bool = False,
        write_tools: Optional[Set[str]] = None,
        disabled_tools: Optional[Set[str]] = None,
        disabled_services: Optional[Set[str]] = None,
        toolsets: Optional[Set[str]] = None,
        host: Optional[str] = None,
        auth: Optional[object] = None,
        disable_entitlement_filter: bool = False,
    ):
        """Initialize the Zscaler Integrations MCP Server.

        Args:
            client_id: Zscaler OAuth client ID
            client_secret: Zscaler OAuth client secret
            customer_id: Zscaler customer ID
            vanity_domain: Zscaler vanity domain
            cloud: Zscaler cloud environment (e.g., 'beta', 'zscalertwo')
            debug: Enable debug logging
            enabled_services: Set of service names to enable (defaults to all services)
            enabled_tools: Set of tool names to enable (defaults to all tools)
            user_agent_comment: Additional information to include in the User-Agent comment section
            enable_write_tools: Enable write operations (create, update, delete). Default: False for safety.
            write_tools: Explicit allowlist of write tools to enable. Supports wildcards. Requires enable_write_tools=True.
            disabled_tools: Set of tool name patterns to exclude (supports wildcards via fnmatch).
            disabled_services: Set of service names to exclude from enabled services.
            toolsets: Set of toolset ids to enable (e.g. ``{"zia_url_filtering",
                "zpa_app_segments"}``). Special values ``"default"`` and ``"all"``
                are accepted in the input set and expanded against the catalog.
                When ``None``, every toolset whose owning service is currently
                enabled is selected (preserves today's behaviour).
                See :mod:`zscaler_mcp.common.toolsets`.
            host: HTTP bind host (e.g. 0.0.0.0). When 0.0.0.0, host header validation is auto-disabled.
            auth: A ``fastmcp.server.auth.AuthProvider`` instance (e.g.
                ``OIDCProxy``, ``OAuthProxy``, or a custom ``AuthProvider`` subclass)
                that provides MCP-spec-compliant OAuth 2.1 with Dynamic Client
                Registration. When supplied, the server delegates authentication
                to this provider instead of the env-var-based auth middleware
                (jwt / api-key / zscaler modes). Only applies to HTTP transports.

                Example::

                    from fastmcp.server.auth.oidc_proxy import OIDCProxy

                    auth = OIDCProxy(
                        config_url="https://accounts.google.com/.well-known/openid-configuration",
                        client_id="YOUR_CLIENT_ID",
                        client_secret="YOUR_CLIENT_SECRET",
                        base_url="http://localhost:8000",
                    )
                    server = ZscalerMCPServer(auth=auth)
                    server.run("streamable-http")
            disable_entitlement_filter: When ``True``, skip the OneAPI
                entitlement filter that trims ``selected_toolsets`` down
                to the products the configured OneAPI credentials are
                actually entitled to. Use this as an emergency override
                when the filter is misbehaving (e.g. unusual JWT
                payloads). Defaults to ``False``.
                Equivalent CLI flag: ``--no-entitlement-filter``.
                Equivalent env var: ``ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true``.
        """
        # Store configuration
        self.client_id = client_id
        self.client_secret = client_secret
        self.customer_id = customer_id
        self.vanity_domain = vanity_domain
        self.cloud = cloud
        self.debug = debug
        self.user_agent_comment = user_agent_comment

        self.enabled_services = enabled_services or set(services.get_service_names())
        self.enabled_tools = enabled_tools or set()
        self.enable_write_tools = enable_write_tools
        self.write_tools = write_tools  # Explicit allowlist for write tools
        self.disabled_tools = disabled_tools
        self.disabled_services = disabled_services

        if self.disabled_services:
            self.enabled_services -= self.disabled_services

        # Configure logging - use stderr for stdio transport to avoid interfering with MCP protocol
        configure_logging(debug=self.debug, use_stderr=True)
        logger = get_logger(__name__)

        # Resolve the toolset selection. Three layers:
        #   1. Explicit ``toolsets`` argument (CLI / env / programmatic).
        #      Supports the "default" and "all" keywords.
        #   2. Fall back to "every toolset whose owning service is in
        #      enabled_services" — preserves today's behaviour for users
        #      who don't pass --toolsets at all.
        #   3. The "meta" toolset is always selected (force-added by
        #      ToolsetCatalog.resolve()) so cross-service discovery tools
        #      stay loaded regardless.
        from zscaler_mcp.common.toolsets import (
            META_TOOLSET_ID,
            TOOLSETS,
            resolve_toolset_selection,
        )

        if toolsets:
            self.selected_toolsets, unknown = resolve_toolset_selection(toolsets)
            if unknown:
                logger.warning(
                    "Unknown toolset id(s) in --toolsets: %s. Known toolsets: %s",
                    ", ".join(sorted(unknown)),
                    ", ".join(TOOLSETS.all_ids()),
                )
        else:
            self.selected_toolsets = {
                ts.id
                for ts in TOOLSETS.values()
                if ts.service in self.enabled_services or ts.id == META_TOOLSET_ID
            }
        self._toolset_catalog = TOOLSETS

        # OneAPI entitlement filter — trim the selected toolsets down to
        # the products the configured OneAPI credentials are actually
        # entitled to. Cache-first / cold-fetch / non-fatal. The filter
        # is skipped entirely if:
        #   * disable_entitlement_filter is True, or
        #   * ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true in the env, or
        #   * any failure occurs (missing creds, network, decode, etc.).
        env_optout = os.getenv("ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER", "").lower() in (
            "true",
            "1",
            "yes",
        )
        self.disable_entitlement_filter = bool(disable_entitlement_filter or env_optout)
        # Track the filter outcome for the security posture banner. One of:
        #   "disabled"           — operator opted out (CLI flag / env var)
        #   "applied"            — filter ran and trimmed (or confirmed) the set
        #   "skipped: <reason>"  — filter ran but bailed (no creds, decode error, ...)
        #   "error: <Exception>" — defensive catch-all
        self.entitlement_filter_state: str = "disabled" if self.disable_entitlement_filter else "applied"
        self.entitlement_filter_summary: Optional[str] = None
        self.entitlement_kept_count: Optional[int] = None
        self.entitlement_removed_count: Optional[int] = None
        self.entitled_services: Optional[List[str]] = None

        if self.disable_entitlement_filter:
            logger.info(
                "OneAPI entitlement filter disabled by configuration; "
                "all selected toolsets will load."
            )
        else:
            try:
                from zscaler_mcp.common.entitlements import apply_entitlement_filter

                pre_filter_count = len(self.selected_toolsets)
                filtered, status = apply_entitlement_filter(
                    self.selected_toolsets,
                )
                self.entitlement_filter_summary = status
                if status and status.startswith("entitlement filter skipped"):
                    self.entitlement_filter_state = "skipped"
                if filtered is not None and filtered != self.selected_toolsets:
                    removed = sorted(self.selected_toolsets - filtered)
                    self.selected_toolsets = filtered
                    self.entitlement_kept_count = len(filtered)
                    self.entitlement_removed_count = len(removed)
                    logger.info(status)
                elif status:
                    # Filter ran but didn't change anything — could be
                    # "all entitled" or "skipped because <reason>".
                    if status.startswith("entitlement filter skipped"):
                        logger.warning(status)
                    else:
                        logger.info(status)
                        self.entitlement_kept_count = pre_filter_count
                        self.entitlement_removed_count = 0

                # Cache-only lookup of the entitled service codes for the
                # security posture banner. The token was just fetched (and
                # cached) by apply_entitlement_filter above, so this is
                # essentially free; on any failure we just leave the field
                # unset and the banner shows "(unavailable)".
                if self.entitlement_filter_state == "applied":
                    try:
                        from zscaler_mcp.common.entitlements import (
                            decode_oneapi_token,
                            extract_entitled_services,
                            obtain_oneapi_token,
                        )

                        token, _ = obtain_oneapi_token()
                        if token:
                            payload = decode_oneapi_token(token)
                            if payload:
                                self.entitled_services = sorted(
                                    extract_entitled_services(payload)
                                )
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.debug(
                            "Could not resolve entitled services for banner: %s", exc
                        )
            except Exception as exc:
                logger.warning(
                    "Entitlement filter raised %s; skipping (all selected "
                    "toolsets will load).",
                    exc.__class__.__name__,
                )
                self.entitlement_filter_state = "error"
                self.entitlement_filter_summary = (
                    f"entitlement filter error: {exc.__class__.__name__}"
                )

        # Log security posture
        logger.info("Initializing Zscaler Integrations MCP Server")
        if self.enable_write_tools:
            logger.warning("=" * 80)
            logger.warning("⚠️  WRITE TOOLS MODE ENABLED")
            if self.write_tools:
                logger.warning(
                    "⚠️  Explicit allowlist provided - only listed write tools will be registered"
                )
                logger.warning(f"⚠️  Allowed patterns: {', '.join(sorted(self.write_tools))}")
                logger.warning("⚠️  Server can CREATE, MODIFY, and DELETE Zscaler resources")
                logger.warning("⚠️  Ensure this is intentional and appropriate for your use case")
            else:
                logger.warning("⚠️  NO allowlist provided - 0 write tools will be registered")
                logger.warning("⚠️  Read-only tools will still be available")
                logger.warning("⚠️  To enable write operations, add: --write-tools 'pattern'")
            logger.warning("=" * 80)
        else:
            logger.info("=" * 80)
            logger.info("🔒 Server running in READ-ONLY mode (safe default)")
            logger.info("   Only list and get operations are available")
            logger.info(
                "   To enable write operations, use --enable-write-tools AND --write-tools flags"
            )
            logger.info("=" * 80)

        # Store fastmcp AuthProvider for library-level OAuth 2.1 / OIDC support
        self._fastmcp_auth = auth
        if auth is not None:
            auth_type = type(auth).__name__
            logger.info(
                "Library-level auth provider configured: %s "
                "(env-var auth middleware will be skipped for HTTP transports)",
                auth_type,
            )

        # Don't initialize the Zscaler client during server startup to avoid pickle issues
        # Clients will be created on-demand when tools are called
        self.zscaler_client = None
        logger.info("Client initialization deferred to tool execution")

        # Initialize the MCP server
        transport_security = _get_transport_security(host=host)
        self.server = FastMCP(
            name="Zscaler Integrations MCP Server",
            instructions=self._compose_server_instructions(),
            debug=self.debug,
            log_level="DEBUG" if self.debug else "INFO",
            transport_security=transport_security,
        )

        # Initialize and register services
        self.services = {}
        available_services = services.get_available_services()
        for service_name in self.enabled_services:
            if service_name in available_services:
                service_class = available_services[service_name]
                # Pass None as client - tools will create their own clients on-demand
                self.services[service_name] = service_class(None)
                logger.debug("Initialized service: %s", service_name)

        # Register tools and resources from services
        tool_count = self._register_tools()
        tool_word = "tool" if tool_count == 1 else "tools"

        resource_count = self._register_resources()
        resource_word = "resource" if resource_count == 1 else "resources"

        # Count services and tools with proper grammar
        service_count = len(self.services)
        service_word = "service" if service_count == 1 else "services"

        logger.info(
            "Initialized %d %s with %d %s and %d %s",
            service_count,
            service_word,
            tool_count,
            tool_word,
            resource_count,
            resource_word,
        )

    def _register_tools(self) -> int:
        """Register tools from all services.

        Returns:
            int: Number of tools registered
        """
        from zscaler_mcp.common.tool_helpers import _wrap_with_audit

        # Register core tools directly. These belong to the ``meta``
        # toolset and are never filtered out — the agent always needs
        # connectivity checks and discovery.
        self.server.add_tool(
            _wrap_with_audit(self.zscaler_check_connectivity, "zscaler_check_connectivity"),
            name="zscaler_check_connectivity",
            description="Check connectivity to the Zscaler API.",
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        self.server.add_tool(
            _wrap_with_audit(self.get_available_services, "zscaler_get_available_services"),
            name="zscaler_get_available_services",
            description=(
                "Service-level overview of what is loaded in this "
                "session: which Zscaler services are callable, which "
                "are present but have zero callable tools because the "
                "OneAPI credentials are not entitled to them, and "
                "which were excluded by configuration. For tool-level "
                "discovery, prefer zscaler_list_toolsets. Treat the "
                "result as authoritative."
            ),
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        self.server.add_tool(
            _wrap_with_audit(self.zscaler_list_toolsets, "zscaler_list_toolsets"),
            name="zscaler_list_toolsets",
            description=(
                "PRIMARY tool-discovery entry point. Call this FIRST "
                "for any user request that needs to find a Zscaler "
                "tool. Returns the toolsets this server organises tools "
                "into (one per resource family per service, e.g. "
                "'zia_url_filtering', 'zpa_segment_groups'). Each row "
                "tells you whether the group is currently loaded, how "
                "many tools it contains, and whether it can be enabled "
                "in this session. Supports name / description / service "
                "substring filters so you can scope the result. Treat "
                "'can_enable: false' as authoritative — the OneAPI "
                "credentials cannot access that product, do not retry."
            ),
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        self.server.add_tool(
            _wrap_with_audit(self.zscaler_get_toolset_tools, "zscaler_get_toolset_tools"),
            name="zscaler_get_toolset_tools",
            description=(
                "Drill into a specific toolset to see its tools and "
                "whether each one can be called right now. Use after "
                "zscaler_list_toolsets has identified the relevant "
                "toolset. Each result row has 'available' and (when "
                "false) 'unavailable_reason'. Treat 'available: false' "
                "as authoritative and report the situation to the user "
                "instead of attempting to call the tool. Supports name "
                "/ description substring filters to narrow the result."
            ),
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        self.server.add_tool(
            _wrap_with_audit(self.zscaler_enable_toolset, "zscaler_enable_toolset"),
            name="zscaler_enable_toolset",
            description=(
                "Activate a toolset that was registered but not loaded "
                "at startup, so its tools become callable for the rest "
                "of the session. Refuses with status 'not_entitled' if "
                "the toolset belongs to a product the configured OneAPI "
                "credentials cannot access — in that case, report the "
                "result to the user and do not retry."
            ),
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        tool_count = 5  # 2 core meta tools + 3 toolset discovery tools

        # Register tools from services
        for service in self.services.values():
            try:
                # Register tools with write mode flag and allowlist
                if self.enabled_tools:
                    service.register_tools(
                        self.server,
                        enabled_tools=self.enabled_tools,
                        enable_write_tools=self.enable_write_tools,
                        write_tools=self.write_tools,
                        disabled_tools=self.disabled_tools,
                        selected_toolsets=self.selected_toolsets,
                    )
                else:
                    service.register_tools(
                        self.server,
                        enable_write_tools=self.enable_write_tools,
                        write_tools=self.write_tools,
                        disabled_tools=self.disabled_tools,
                        selected_toolsets=self.selected_toolsets,
                    )

                # Count tools (read + write)
                if hasattr(service, "read_tools"):
                    tool_count += len(service.read_tools)
                if hasattr(service, "write_tools") and self.enable_write_tools:
                    tool_count += len(service.write_tools)
                elif hasattr(service, "tools"):
                    # Fallback for services not yet migrated
                    tool_count += len(service.tools)
            except Exception as e:
                logger.warning(f"Failed to register tools for service: {e}")
                # Still count the tools even if registration fails
                if hasattr(service, "read_tools"):
                    tool_count += len(service.read_tools)
                if hasattr(service, "write_tools"):
                    tool_count += len(service.write_tools)
                elif hasattr(service, "tools"):
                    tool_count += len(service.tools)

        return tool_count

    def _register_resources(self) -> int:
        """Register resources from all services.

        Returns:
            int: Number of resources registered
        """
        # Register resources from services
        for service in self.services.values():
            # Check if the service has a register_resources method
            if hasattr(service, "register_resources") and callable(service.register_resources):
                service.register_resources(self.server)

        # Count resources from services
        resource_count = 0
        for service in self.services.values():
            if hasattr(service, "resources"):
                resource_count += len(service.resources)
        return resource_count

    def zscaler_check_connectivity(self) -> Dict[str, bool]:
        """Check connectivity to the Zscaler API.

        Returns:
            Dict[str, bool]: Connectivity status
        """
        try:
            # Try to make a simple API call to test connectivity
            # This is a placeholder - you might want to implement a specific test
            return {"connected": True}
        except Exception as e:
            logger.error("Connectivity check failed: %s", e)
            return {"connected": False}

    # ------------------------------------------------------------------
    # Toolset support
    # ------------------------------------------------------------------

    def _compose_server_instructions(self) -> str:
        """Build the MCP ``instructions`` string from the active toolsets.

        Composes a base preamble + one snippet per enabled toolset whose
        metadata defines an ``instructions`` callable. Mirrors GitHub's
        ``generateInstructions`` pattern so per-toolset guidance reaches
        the agent only when those tools are loaded.
        """
        from zscaler_mcp.common.toolsets import TOOLSETS

        base = (
            "This server exposes Zscaler tools across ZIA, ZPA, ZDX, "
            "ZCC, ZTW, ZIdentity, EASM, Z-Insights, and ZMS. Tools "
            "are organised into toolsets — one logical grouping per "
            "resource family per service.\n\n"
            "Tool discovery flow (use this for any user request that "
            "needs to find a Zscaler tool):\n"
            "  1. Call zscaler_list_toolsets first. Pass "
            "name_contains, description_contains, or service to "
            "scope the result (e.g. name_contains='segment' to find "
            "the ZPA segment-group toolset).\n"
            "  2. If a row has can_enable: false, the OneAPI "
            "credentials in this session cannot access that "
            "product. Stop and report this to the user — do not "
            "call zscaler_enable_toolset, do not retry, do not "
            "look for workarounds.\n"
            "  3. Otherwise call zscaler_get_toolset_tools(toolset="
            "<id>) to see the specific tools and confirm "
            "availability per tool.\n"
            "  4. If a tool's available flag is false, treat the "
            "reason as authoritative and report it to the user.\n\n"
            "For a session-level overview of which services are "
            "callable, call zscaler_get_available_services."
        )

        snippets: List[str] = [base]
        seen: Set[str] = set()
        for tsid in sorted(self.selected_toolsets):
            ts = TOOLSETS.get(tsid)
            if ts is None or ts.instructions is None:
                continue
            try:
                snippet = ts.instructions(TOOLSETS)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to render instructions for toolset %s: %s", tsid, exc
                )
                continue
            snippet = (snippet or "").strip()
            if not snippet or snippet in seen:
                continue
            seen.add(snippet)
            snippets.append(snippet)

        return "\n\n".join(snippets)

    def zscaler_list_toolsets(
        self,
        name_contains: Optional[str] = None,
        description_contains: Optional[str] = None,
        service: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        """List Zscaler toolsets — the primary entry point for tool discovery.

        Call this FIRST for any user request that needs to find a
        Zscaler tool. Toolsets are logical groupings of related tools
        (one per resource family per service, e.g. ``zia_url_filtering``
        for URL filtering rules, ``zpa_segment_groups`` for ZPA segment
        groups). Each row tells you whether the group is currently
        loaded, how many tools it contains, and whether you can enable
        it in this session.

        Args:
            name_contains: Optional case-insensitive substring filter on
                the toolset id (e.g. ``"segment"`` finds
                ``zpa_segment_groups``).
            description_contains: Optional case-insensitive substring
                filter on the toolset description (e.g. ``"firewall"``
                finds every firewall-related toolset across services).
            service: Optional exact-match filter on the owning service
                code (``zia``, ``zpa``, ``zdx``, ``zcc``, ``ztw``,
                ``zid``, ``zeasm``, ``zins``, ``zms``, ``meta``).

        Returns:
            List of dicts with keys ``id``, ``service``, ``description``,
            ``default``, ``currently_enabled``, ``tool_count``,
            ``can_enable`` and (when ``can_enable`` is False)
            ``unavailable_reason``. Returns ``[{"status":
            "no_results", ...}]`` when filters match nothing.

            ``can_enable`` is ``False`` when the OneAPI credentials are
            not entitled to the toolset's product — calling
            ``zscaler_enable_toolset`` would be refused. Treat this as
            authoritative and report it to the user instead of retrying.

        Typical flow: call this first to find the right toolset, then
        ``zscaler_get_toolset_tools(toolset=<id>)`` to drill into the
        specific tools it contains.
        """
        from zscaler_mcp.common.toolsets import TOOLSETS, toolset_for_tool

        counts: Dict[str, int] = {}
        for svc in self.services.values():
            for tool_def in list(getattr(svc, "read_tools", [])) + list(
                getattr(svc, "write_tools", [])
            ):
                try:
                    tsid = toolset_for_tool(tool_def["name"])
                except KeyError:
                    continue
                counts[tsid] = counts.get(tsid, 0) + 1

        ent_state = getattr(self, "entitlement_filter_state", None)
        entitled = getattr(self, "entitled_services", None)

        rows: List[Dict[str, object]] = []
        for tsid in TOOLSETS.all_ids():
            ts = TOOLSETS.get(tsid)
            if ts is None:
                continue
            row: Dict[str, object] = {
                "id": ts.id,
                "service": ts.service,
                "description": ts.description,
                "default": ts.default,
                "currently_enabled": tsid in self.selected_toolsets,
                "tool_count": counts.get(tsid, 0),
                "can_enable": True,
            }
            if (
                ent_state == "applied"
                and entitled is not None
                and ts.service not in entitled
                and ts.service != "meta"
            ):
                row["can_enable"] = False
                row["unavailable_reason"] = (
                    "OneAPI credentials are not entitled to this product"
                )
            rows.append(row)

        if service:
            svc_lower = service.lower()
            rows = [r for r in rows if r["service"] == svc_lower]

        if name_contains:
            needle = name_contains.lower()
            rows = [r for r in rows if needle in r["id"].lower()]

        if description_contains:
            needle = description_contains.lower()
            rows = [r for r in rows if needle in str(r["description"]).lower()]

        if not rows:
            return [
                {
                    "status": "no_results",
                    "message": (
                        "No toolset matched the filters. Call "
                        "zscaler_list_toolsets with no arguments to see "
                        "the full catalog."
                    ),
                }
            ]
        return rows

    def zscaler_get_toolset_tools(
        self,
        toolset: str,
        name_contains: Optional[str] = None,
        description_contains: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        """List the tools that belong to a given toolset, with availability info.

        Use this after ``zscaler_list_toolsets`` to inspect what a
        toolset contains and confirm a specific tool is callable.

        Args:
            toolset: A toolset id (e.g. ``"zia_url_filtering"``). See
                ``zscaler_list_toolsets`` for the full set of valid ids.
            name_contains: Optional case-insensitive substring filter
                on tool name (e.g. ``"create"`` to narrow to write
                tools).
            description_contains: Optional case-insensitive substring
                filter on tool description.

        Returns:
            List of dicts with keys ``name``, ``description``,
            ``type`` (``"read"`` / ``"write"``), ``available``, and
            (when ``available`` is False) ``unavailable_reason``.
            Returns ``[{"error": "..."}]`` for unknown toolset ids.

            Treat ``available: false`` results as authoritative — the
            tool exists in the catalog but cannot be called as
            configured (typically because the OneAPI credentials are
            not entitled to that product, the toolset is not enabled
            in this session, or write tools are disabled). Report the
            situation to the user instead of retrying.
        """
        from zscaler_mcp.common.toolsets import TOOLSETS, toolset_for_tool

        if not TOOLSETS.has(toolset):
            return [{
                "error": (
                    f"Unknown toolset id: {toolset!r}. Call zscaler_list_toolsets "
                    "to see the valid ids."
                ),
            }]

        rows: List[Dict[str, object]] = []
        for svc in self.services.values():
            for kind_attr, kind_label in (
                ("read_tools", "read"),
                ("write_tools", "write"),
            ):
                for tool_def in getattr(svc, kind_attr, []):
                    try:
                        if toolset_for_tool(tool_def["name"]) != toolset:
                            continue
                    except KeyError:
                        continue
                    available, reason = self._tool_availability(
                        tool_def["name"], kind_label
                    )
                    row: Dict[str, object] = {
                        "name": tool_def["name"],
                        "description": tool_def["description"],
                        "type": kind_label,
                        "available": available,
                    }
                    if not available:
                        row["unavailable_reason"] = reason
                    rows.append(row)

        if name_contains:
            needle = name_contains.lower()
            rows = [r for r in rows if needle in str(r["name"]).lower()]

        if description_contains:
            needle = description_contains.lower()
            rows = [r for r in rows if needle in str(r["description"]).lower()]

        return sorted(rows, key=lambda r: str(r["name"]))

    def zscaler_enable_toolset(self, toolset: str) -> Dict[str, object]:
        """Mark a toolset as enabled at runtime and register its tools.

        After this call, the toolset's tools become available for the
        rest of the session. Existing tools and previously-enabled
        toolsets are NOT re-registered (they remain available).

        Args:
            toolset: A toolset id (e.g. ``"zia_url_filtering"``).

        Returns:
            ``{"toolset": <id>, "newly_registered": <count>, "status": "..."}``.
        """
        from zscaler_mcp.common.toolsets import TOOLSETS
        from zscaler_mcp.common.tool_helpers import (
            register_read_tools,
            register_write_tools,
        )

        if not TOOLSETS.has(toolset):
            return {
                "toolset": toolset,
                "newly_registered": 0,
                "status": "error",
                "error": (
                    f"Unknown toolset id: {toolset!r}. "
                    "Call zscaler_list_toolsets to see valid ids."
                ),
            }

        if toolset in self.selected_toolsets:
            return {
                "toolset": toolset,
                "newly_registered": 0,
                "status": "already_enabled",
            }

        # Refuse to enable a toolset whose product the OneAPI
        # credentials are not entitled to. Tools would fail at call
        # time anyway and the agent would loop. Be authoritative here.
        ts_meta = TOOLSETS.get(toolset)
        ent_state = getattr(self, "entitlement_filter_state", None)
        entitled = getattr(self, "entitled_services", None)
        if (
            ent_state == "applied"
            and entitled is not None
            and ts_meta is not None
            and ts_meta.service not in entitled
        ):
            return {
                "toolset": toolset,
                "newly_registered": 0,
                "status": "not_entitled",
                "error": (
                    f"Toolset {toolset!r} belongs to service "
                    f"{ts_meta.service!r}, which the configured OneAPI "
                    "credentials are not entitled to. Inform the user "
                    "that the credentials in use cannot access this "
                    f"product (entitled products: {', '.join(entitled)}). "
                    "Do not retry — switching credentials at the "
                    "MCP-client level requires restarting the server "
                    "with different ZSCALER_CLIENT_ID / "
                    "ZSCALER_CLIENT_SECRET values."
                ),
            }

        # Find the per-service tool dicts that belong to this toolset and
        # register only those. We hand register_*_tools a *single-toolset*
        # selected_toolsets so its existing precedence logic kicks in
        # naturally for the disabled/exclude/enabled-tools filters.
        single = {toolset}
        registered = 0
        for service in self.services.values():
            read = [
                t for t in getattr(service, "read_tools", [])
                if _safe_toolset_for(t["name"]) == toolset
            ]
            write = [
                t for t in getattr(service, "write_tools", [])
                if _safe_toolset_for(t["name"]) == toolset
            ]
            if read:
                registered += register_read_tools(
                    self.server, read,
                    enabled_tools=self.enabled_tools or None,
                    disabled_tools=self.disabled_tools,
                    selected_toolsets=single,
                )
            if write:
                registered += register_write_tools(
                    self.server, write,
                    enabled_tools=self.enabled_tools or None,
                    enable_write_tools=self.enable_write_tools,
                    write_tools=self.write_tools,
                    disabled_tools=self.disabled_tools,
                    selected_toolsets=single,
                )

        self.selected_toolsets.add(toolset)
        # FastMCP doesn't expose a public hook to emit
        # notifications/tools/list_changed; many clients re-list tools on
        # the next request anyway. Document the limitation rather than
        # touch private state.
        return {
            "toolset": toolset,
            "newly_registered": registered,
            "status": "enabled",
        }

    def get_available_services(self) -> Dict[str, object]:
        """Get information about available and unavailable services and tools.

        Returns a dict with services that are loaded and callable (with
        an accurate count of currently-registered tools), any services
        that are present but currently have zero callable tools because
        the OneAPI credentials are not entitled to them, services
        excluded by configuration, and any disabled tool patterns. The
        AI agent should treat the returned counts as authoritative.
        """
        import fnmatch as _fnmatch

        from zscaler_mcp.common.toolsets import META_TOOLSET_ID, TOOLSETS, toolset_for_tool

        all_names = set(services.get_service_names())

        # Count tools that are actually callable in this session — i.e.
        # the tool's toolset is in self.selected_toolsets *and* it
        # passes the per-tool registration filters. Anything stripped
        # by the entitlement filter, --disabled-tools, or read-only
        # mode is excluded so the agent gets the truth, not the
        # configured maximum.
        active_count_by_service: Dict[str, int] = {}
        for svc_name, svc in self.services.items():
            count = 0
            for kind in ("read_tools", "write_tools"):
                for tool_def in getattr(svc, kind, []):
                    name = tool_def["name"]
                    try:
                        tsid = toolset_for_tool(name)
                    except KeyError:
                        tsid = None
                    if tsid and tsid not in self.selected_toolsets:
                        continue
                    if kind == "write_tools":
                        if not self.enable_write_tools:
                            continue
                        if self.write_tools and not any(
                            _fnmatch.fnmatch(name, pat) for pat in self.write_tools
                        ):
                            continue
                    if self.disabled_tools and any(
                        _fnmatch.fnmatch(name, pat) for pat in self.disabled_tools
                    ):
                        continue
                    count += 1
            active_count_by_service[svc_name] = count

        enabled = {
            name: {"tool_count": active_count_by_service.get(name, 0)}
            for name in sorted(self.enabled_services)
            if active_count_by_service.get(name, 0) > 0
        }

        # A service that is configured-on but has zero active tools is
        # almost always the entitlement filter at work (or every toolset
        # got stripped some other way). Surface it explicitly so the
        # agent doesn't fall back to "let me search harder".
        unavailable_due_to_entitlement = sorted(
            name for name in self.enabled_services
            if active_count_by_service.get(name, 0) == 0
        )

        disabled_svc = sorted(all_names - self.enabled_services)

        result: Dict[str, object] = {"enabled_services": enabled}

        notes = []
        if unavailable_due_to_entitlement:
            result["unavailable_services"] = unavailable_due_to_entitlement
            ent_state = getattr(self, "entitlement_filter_state", None)
            entitled = getattr(self, "entitled_services", None) or []
            if ent_state == "applied" and entitled:
                notes.append(
                    "Services in 'unavailable_services' are present but have "
                    "zero callable tools in this session because the OneAPI "
                    "credentials are only entitled to: "
                    f"{', '.join(entitled)}. Inform the user that the "
                    "credentials in use are not entitled to those services. "
                    "Do NOT attempt to enable a toolset for an unavailable "
                    "service — it will be refused."
                )
            else:
                notes.append(
                    "Services in 'unavailable_services' have no callable "
                    "tools in this session (toolset selection or other "
                    "filtering excluded them). Inform the user the service "
                    "is not available rather than searching for workarounds."
                )

        if disabled_svc:
            result["disabled_services"] = disabled_svc
            notes.append(
                "Services in 'disabled_services' have been explicitly "
                "excluded by the server administrator. Their tools are "
                "not registered and cannot be called."
            )

        if self.disabled_tools:
            result["disabled_tool_patterns"] = sorted(self.disabled_tools)
            notes.append(
                "Tool patterns in 'disabled_tool_patterns' have been "
                "blocked by the administrator. Any tool whose name "
                "matches a pattern (fnmatch wildcards) is excluded."
            )

        # Tell the agent how many toolsets are active so it doesn't
        # get its hopes up from raw catalog totals.
        result["active_toolsets"] = sorted(
            t for t in self.selected_toolsets if t != META_TOOLSET_ID
        )
        result["total_toolsets_in_catalog"] = len(TOOLSETS.all_ids())

        if notes:
            result["note"] = " ".join(notes)
        return result

    def _tool_availability(self, name: str, kind: str) -> tuple[bool, Optional[str]]:
        """Decide whether a registered tool can actually be called this session.

        Returns ``(available, reason)``. ``reason`` is ``None`` when
        ``available`` is ``True``; otherwise it is a short, user-facing
        sentence explaining why the tool is not callable.

        Used by ``zscaler_get_toolset_tools`` to surface entitlement /
        toolset / write / disabled-tools state on each result row so
        the agent gets one authoritative answer instead of probing.
        """
        import fnmatch as _fnmatch

        from zscaler_mcp.common.toolsets import toolset_for_tool

        try:
            tsid = toolset_for_tool(name)
        except KeyError:
            tsid = None

        if tsid and tsid not in self.selected_toolsets:
            ent_state = getattr(self, "entitlement_filter_state", None)
            entitled = getattr(self, "entitled_services", None)
            if ent_state == "applied" and entitled is not None:
                svc_for_tool = name.split("_", 1)[0] if "_" in name else None
                if svc_for_tool and svc_for_tool not in entitled:
                    return (
                        False,
                        "OneAPI credentials are not entitled to this product",
                    )
            return (
                False,
                f"Toolset '{tsid}' is not enabled in this session",
            )

        if kind == "write":
            if not self.enable_write_tools:
                return False, "Write tools are disabled (server is read-only)"
            if self.write_tools and not any(
                _fnmatch.fnmatch(name, pat) for pat in self.write_tools
            ):
                return False, "Write tool is not in the configured allowlist"

        if self.disabled_tools and any(
            _fnmatch.fnmatch(name, pat) for pat in self.disabled_tools
        ):
            return False, "Tool has been disabled by the administrator"

        return True, None

    def _build_fastmcp_auth_app(self, transport: str):
        """Build an ASGI app with a fastmcp AuthProvider handling authentication.

        When the caller supplies a ``fastmcp.server.auth.AuthProvider`` (e.g.
        ``OIDCProxy``) via the ``auth=`` constructor parameter, this method
        constructs the HTTP app with OAuth routes, auth middleware, and the
        ``RequireAuthMiddleware`` wrapper — all provided by the auth provider.

        This bypasses the env-var-based auth layer (``apply_auth_middleware``)
        and delegates authentication entirely to the fastmcp provider.
        """
        from contextlib import asynccontextmanager

        from fastmcp.server.auth.middleware import RequireAuthMiddleware
        from mcp.server.auth.routes import build_resource_metadata_url
        from mcp.server.fastmcp.server import StreamableHTTPASGIApp
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route

        auth = self._fastmcp_auth

        if transport == "streamable-http":
            if self.server._session_manager is None:
                self.server._session_manager = StreamableHTTPSessionManager(
                    app=self.server._mcp_server,
                    json_response=self.server.settings.json_response,
                    stateless=self.server.settings.stateless_http,
                    security_settings=self.server.settings.transport_security,
                )

            mcp_asgi = StreamableHTTPASGIApp(self.server._session_manager)
            mcp_path = self.server.settings.streamable_http_path

            auth_middleware = auth.get_middleware()
            auth_routes = auth.get_routes(mcp_path=mcp_path)

            resource_url = auth._get_resource_url(mcp_path)
            resource_metadata_url = (
                build_resource_metadata_url(resource_url) if resource_url else None
            )

            routes = list(auth_routes)
            routes.append(
                Route(
                    mcp_path,
                    endpoint=RequireAuthMiddleware(
                        mcp_asgi,
                        auth.required_scopes,
                        resource_metadata_url,
                    ),
                )
            )

            session_mgr = self.server._session_manager

            @asynccontextmanager
            async def lifespan(app):
                async with session_mgr.run():
                    yield

            return Starlette(
                debug=self.debug,
                routes=routes,
                middleware=auth_middleware,
                lifespan=lifespan,
            )

        else:
            from mcp.server.sse import SseServerTransport
            from starlette.responses import Response

            sse_path = self.server.settings.sse_path
            message_path = self.server._normalize_path(
                self.server.settings.mount_path,
                self.server.settings.message_path,
            )

            sse = SseServerTransport(
                message_path,
                security_settings=self.server.settings.transport_security,
            )

            mcp_server = self.server._mcp_server

            async def handle_sse(scope, receive, send):
                async with sse.connect_sse(scope, receive, send) as streams:
                    await mcp_server.run(
                        streams[0],
                        streams[1],
                        mcp_server.create_initialization_options(),
                    )
                return Response()

            auth_middleware = auth.get_middleware()
            auth_routes = auth.get_routes(mcp_path=sse_path)

            resource_url = auth._get_resource_url(sse_path)
            resource_metadata_url = (
                build_resource_metadata_url(resource_url) if resource_url else None
            )

            routes = list(auth_routes)
            routes.append(
                Route(
                    sse_path,
                    endpoint=RequireAuthMiddleware(
                        handle_sse,
                        auth.required_scopes,
                        resource_metadata_url,
                    ),
                    methods=["GET"],
                )
            )
            routes.append(
                Mount(
                    message_path,
                    app=RequireAuthMiddleware(
                        sse.handle_post_message,
                        auth.required_scopes,
                        resource_metadata_url,
                    ),
                )
            )

            return Starlette(
                debug=self.debug,
                routes=routes,
                middleware=auth_middleware,
            )

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        """Run the MCP server.

        Args:
            transport: Transport protocol to use ("stdio", "sse", or "streamable-http")
            host: Host to bind to for HTTP transports (default: 127.0.0.1)
            port: Port to listen on for HTTP transports (default: 8000)
        """
        from zscaler_mcp.auth import apply_auth_middleware

        if transport in ("streamable-http", "sse"):
            _validate_host_config(host)

            tls_kwargs = _get_tls_config()
            scheme = "https" if tls_kwargs else "http"

            _enforce_https_policy(host, port, tls_kwargs)

            if not tls_kwargs and host not in ("127.0.0.1", "localhost", "::1"):
                log_security_warning(
                    "Running HTTP without TLS (ZSCALER_MCP_ALLOW_HTTP=true)",
                    [
                        f"The server is listening on {host}:{port} without encryption.",
                        "All traffic (including auth tokens) will be sent in plaintext.",
                        "",
                        "Ensure traffic is encrypted by an overlay (ZPA, VPN) or",
                        "terminated at a reverse proxy (nginx, ALB, etc.).",
                    ],
                )

            if self._fastmcp_auth is not None:
                logger.info(
                    "Using library-level auth provider (%s) — env-var auth middleware skipped",
                    type(self._fastmcp_auth).__name__,
                )
                app = self._build_fastmcp_auth_app(transport)
            else:
                if transport == "streamable-http":
                    app = self.server.streamable_http_app()
                else:
                    app = self.server.sse_app()

                app = apply_auth_middleware(app, transport)

            allowed_ips = _get_allowed_source_ips()
            if allowed_ips is not None:
                logger.info("Source IP ACL active: %s", allowed_ips)
                app = SourceIPMiddleware(app, allowed_ips)

            _log_security_posture(
                transport, scheme, host, port, tls_kwargs,
                fastmcp_auth=self._fastmcp_auth,
                server=self,
            )

            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info" if not self.debug else "debug",
                **tls_kwargs,
            )
        else:
            self.server.run(transport)


def list_available_tools(selected_services=None, enabled_tools=None):
    """Print all available tool metadata names and descriptions, optionally filtered by services and tools."""
    from zscaler_mcp import services as svc_mod

    available_services = svc_mod.get_available_services()
    if selected_services:
        available_services = {k: v for k, v in available_services.items() if k in selected_services}
    logger.info("Available tools:")
    for service_name, service_class in available_services.items():
        service = service_class(None)
        # Get tool metadata from the service's register_tools method
        if hasattr(service, "tools") and hasattr(service, "register_tools"):
            # Create a mock server to capture the tool metadata
            class MockServer:
                def __init__(self):
                    self.tools = []

                def add_tool(self, tool, name=None, description=None, annotations=None):
                    self.tools.append(
                        {
                            "tool": tool,
                            "name": name or tool.__name__,
                            "description": description or (tool.__doc__ or ""),
                            "annotations": annotations,
                        }
                    )

            mock_server = MockServer()
            service.register_tools(mock_server, enabled_tools=enabled_tools)

            for tool_info in mock_server.tools:
                logger.info(f"  [{service_name}] {tool_info['name']}: {tool_info['description']}")


def generate_auth_token(fmt: str = "basic"):
    """Generate an auth token and print ready-to-use MCP client config snippets."""
    import base64

    client_id = os.environ.get("ZSCALER_CLIENT_ID", "")
    client_secret = os.environ.get("ZSCALER_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Error: ZSCALER_CLIENT_ID and ZSCALER_CLIENT_SECRET must be set.")
        print("Set them in your .env file or as environment variables.")
        sys.exit(1)

    if fmt == "basic":
        raw = f"{client_id}:{client_secret}"
        token = base64.b64encode(raw.encode()).decode()
        header_value = f"Basic {token}"
    else:
        header_value = f"Bearer {client_secret}"

    print()
    print("=" * 70)
    print("  Zscaler MCP Server — Auth Token Generator")
    print("=" * 70)
    print()
    print(f"  Mode:   {'zscaler (Basic Auth)' if fmt == 'basic' else 'api-key (Bearer)'}")
    print(f"  Header: Authorization: {header_value}")
    print()
    print("--- Cursor / MCP clients with header support ---")
    print()
    print("  {")
    print('    "mcpServers": {')
    print('      "zscaler-mcp-server": {')
    print('        "url": "http://localhost:8000/mcp",')
    print('        "headers": {')
    print(f'          "Authorization": "{header_value}"')
    print("        }")
    print("      }")
    print("    }")
    print("  }")
    print()
    if fmt == "basic":
        print("--- Alternative: raw credential headers (no Base64 needed) ---")
        print()
        print("  {")
        print('    "mcpServers": {')
        print('      "zscaler-mcp-server": {')
        print('        "url": "http://localhost:8000/mcp",')
        print('        "headers": {')
        print(f'          "X-Zscaler-Client-ID": "{client_id}",')
        print(f'          "X-Zscaler-Client-Secret": "{client_secret}"')
        print("        }")
        print("      }")
        print("    }")
        print("  }")
        print()
    print("--- Claude Desktop (mcp-remote bridge) ---")
    print()
    print("  {")
    print('    "mcpServers": {')
    print('      "zscaler-mcp-server": {')
    print('        "command": "npx",')
    print('        "args": [')
    print('          "-y",')
    print('          "mcp-remote",')
    print('          "http://localhost:8000/mcp",')
    print('          "--header",')
    print(f'          "Authorization: {header_value}"')
    print("        ]")
    print("      }")
    print("    }")
    print("  }")
    print()
    print("=" * 70)


def parse_services_list(services_string):
    """Parse and validate comma-separated service list.

    Args:
        services_string: Comma-separated string of service names

    Returns:
        List of validated service names (returns all available services if empty string)

    Raises:
        argparse.ArgumentTypeError: If any service names are invalid
    """
    # Get available services
    available_services = services.get_service_names()

    # If empty string, return all available services (default behavior)
    if not services_string:
        return available_services

    # Split by comma and clean up whitespace
    service_list = [s.strip() for s in services_string.split(",") if s.strip()]

    # Validate against available services
    invalid_services = [s for s in service_list if s not in available_services]
    if invalid_services:
        raise argparse.ArgumentTypeError(
            f"Invalid services: {', '.join(invalid_services)}. "
            f"Available services: {', '.join(available_services)}"
        )

    return service_list


def parse_tools_list(tools_string):
    """Parse and validate comma-separated tool list.

    Args:
        tools_string: Comma-separated string of tool names

    Returns:
        List of validated tool names (returns empty list if empty string)

    Raises:
        argparse.ArgumentTypeError: If any tool names are invalid
    """
    # If empty string, return empty list (no tools selected)
    if not tools_string:
        return []

    # Split by comma and clean up whitespace
    tool_list = [t.strip() for t in tools_string.split(",") if t.strip()]

    # Get all available tools from all services for validation
    available_services = services.get_available_services()
    all_available_tools = []

    for service_name, service_class in available_services.items():
        service_instance = service_class(None)  # Create instance to get tools

        # Create a mock server to capture the tool metadata names
        class MockServer:
            def __init__(self):
                self.tools = []

            def add_tool(self, tool, name=None, description=None, annotations=None):
                self.tools.append(
                    {
                        "tool": tool,
                        "name": name or tool.__name__,
                        "description": description or (tool.__doc__ or ""),
                        "annotations": annotations,
                    }
                )

        mock_server = MockServer()
        service_instance.register_tools(mock_server)

        for tool_info in mock_server.tools:
            all_available_tools.append(tool_info["name"])

    # Validate against available tools
    invalid_tools = [t for t in tool_list if t not in all_available_tools]
    if invalid_tools:
        raise argparse.ArgumentTypeError(
            f"Invalid tools: {', '.join(invalid_tools)}. "
            f"Available tools: {', '.join(all_available_tools)}"
        )

    return tool_list


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Zscaler Integrations MCP Server")

    # Transport options
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("ZSCALER_MCP_TRANSPORT", "stdio"),
        help="Transport protocol to use (default: stdio, env: ZSCALER_MCP_TRANSPORT)",
    )

    # Service selection
    available_services = services.get_service_names()

    parser.add_argument(
        "--services",
        "-s",
        type=parse_services_list,
        default=parse_services_list(os.environ.get("ZSCALER_MCP_SERVICES", "")),
        metavar="SERVICE1,SERVICE2,...",
        help=f"Comma-separated list of services to enable. Available: [{', '.join(available_services)}] "
        f"(default: all services, env: ZSCALER_MCP_SERVICES)",
    )

    parser.add_argument(
        "--disabled-services",
        default=os.environ.get("ZSCALER_MCP_DISABLED_SERVICES"),
        metavar="SERVICE1,SERVICE2,...",
        help="Comma-separated list of services to exclude "
        "(e.g., 'zcc,zdx' disables ZCC and ZDX services). "
        "(env: ZSCALER_MCP_DISABLED_SERVICES)",
    )

    # Tool selection
    parser.add_argument(
        "--tools",
        type=parse_tools_list,
        default=parse_tools_list(os.environ.get("ZSCALER_MCP_TOOLS", "")),
        metavar="TOOL1,TOOL2,...",
        help="Comma-separated list of specific tools to enable (if not specified, all tools from selected services are enabled, env: ZSCALER_MCP_TOOLS)",
    )

    parser.add_argument(
        "--disabled-tools",
        default=os.environ.get("ZSCALER_MCP_DISABLED_TOOLS"),
        metavar="TOOL1,TOOL2,...",
        help="Comma-separated list of tools to exclude. Supports wildcards "
        "(e.g., 'zcc_*' excludes all ZCC tools, 'zia_list_devices' excludes one tool). "
        "(env: ZSCALER_MCP_DISABLED_TOOLS)",
    )

    # Toolset selection
    parser.add_argument(
        "--toolsets",
        default=os.environ.get("ZSCALER_MCP_TOOLSETS"),
        metavar="TOOLSET1,TOOLSET2,...",
        help=(
            "Comma-separated list of toolsets to enable (e.g. "
            "'zia_url_filtering,zpa_app_segments'). Special values: "
            "'default' expands to the toolsets marked default-on; "
            "'all' enables every toolset. When unspecified, every toolset "
            "belonging to a currently-enabled service is loaded "
            "(preserves today's behaviour). The 'meta' toolset is always "
            "loaded. (env: ZSCALER_MCP_TOOLSETS)"
        ),
    )

    parser.add_argument(
        "--no-entitlement-filter",
        action="store_true",
        default=os.environ.get("ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER", "").lower()
        in ("true", "1", "yes"),
        help=(
            "Skip the OneAPI entitlement filter that trims toolsets down to "
            "the products the configured ZSCALER_CLIENT_ID is entitled to. "
            "Use as an emergency override when the filter misbehaves. "
            "(env: ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER)"
        ),
    )

    # Debug mode
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        default=os.environ.get("ZSCALER_MCP_DEBUG", "").lower() == "true",
        help="Enable debug logging (env: ZSCALER_MCP_DEBUG)",
    )

    # Write tools enablement (NEW)
    parser.add_argument(
        "--enable-write-tools",
        action="store_true",
        default=os.environ.get("ZSCALER_MCP_WRITE_ENABLED", "").lower() == "true",
        help="Enable write operations (create, update, delete). "
        "By default, only read-only operations are available for safety. "
        "(env: ZSCALER_MCP_WRITE_ENABLED)",
    )

    parser.add_argument(
        "--write-tools",
        default=os.environ.get("ZSCALER_MCP_WRITE_TOOLS"),
        help="Comma-separated list of write tools to explicitly allow. "
        "Supports wildcards (e.g., 'zpa_create_*,zpa_delete_*'). "
        "Requires --enable-write-tools to be set. "
        "(env: ZSCALER_MCP_WRITE_TOOLS)",
    )

    # Zscaler API configuration
    parser.add_argument(
        "--client-id",
        default=os.environ.get("ZSCALER_CLIENT_ID"),
        help="Zscaler OAuth client ID (env: ZSCALER_CLIENT_ID)",
    )

    parser.add_argument(
        "--client-secret",
        default=os.environ.get("ZSCALER_CLIENT_SECRET"),
        help="Zscaler OAuth client secret (env: ZSCALER_CLIENT_SECRET)",
    )

    parser.add_argument(
        "--customer-id",
        default=os.environ.get("ZSCALER_CUSTOMER_ID"),
        help="Zscaler customer ID (env: ZSCALER_CUSTOMER_ID)",
    )

    parser.add_argument(
        "--vanity-domain",
        default=os.environ.get("ZSCALER_VANITY_DOMAIN"),
        help="Zscaler vanity domain (env: ZSCALER_VANITY_DOMAIN)",
    )

    parser.add_argument(
        "--cloud",
        default=os.environ.get("ZSCALER_CLOUD"),
        help="Zscaler cloud environment (env: ZSCALER_CLOUD)",
    )

    # HTTP transport configuration
    parser.add_argument(
        "--host",
        default=os.environ.get("ZSCALER_MCP_HOST", "127.0.0.1"),
        help="Host to bind to for HTTP transports (default: 127.0.0.1, env: ZSCALER_MCP_HOST)",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.environ.get("ZSCALER_MCP_PORT", "8000")),
        help="Port to listen on for HTTP transports (default: 8000, env: ZSCALER_MCP_PORT)",
    )

    parser.add_argument(
        "--user-agent-comment",
        default=os.environ.get("ZSCALER_MCP_USER_AGENT_COMMENT"),
        help="Additional information to include in the User-Agent comment section (env: ZSCALER_MCP_USER_AGENT_COMMENT)",
    )

    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tool names and descriptions, then exit.",
    )

    parser.add_argument(
        "--generate-auth-token",
        nargs="?",
        const="basic",
        choices=["basic", "bearer"],
        metavar="FORMAT",
        help="Generate an auth token from ZSCALER_CLIENT_ID and ZSCALER_CLIENT_SECRET "
        "and print MCP client config snippets, then exit. "
        "Format: 'basic' (default) for Zscaler auth mode, 'bearer' for api-key mode.",
    )

    parser.add_argument(
        "--log-tool-calls",
        action="store_true",
        default=os.environ.get("ZSCALER_MCP_LOG_TOOL_CALLS", "").lower() == "true",
        help="Enable audit logging for every tool invocation. "
        "Logs tool name, sanitized arguments, duration, and result summary. "
        "(env: ZSCALER_MCP_LOG_TOOL_CALLS)",
    )

    parser.add_argument(
        "--generate-docs",
        action="store_true",
        help="Regenerate the auto-managed regions of the project's "
        "Markdown docs (docs/guides/supported-tools.md, README.md, "
        "docs/guides/toolsets.md) from the live tool inventory, then "
        "exit. Run this whenever you add, rename, or remove a tool.",
    )

    parser.add_argument(
        "--check-docs",
        action="store_true",
        help="Check whether the auto-managed Markdown regions are in "
        "sync with the live tool inventory. Exits 0 if everything is "
        "current, 1 (with a list of stale files) if --generate-docs "
        "needs to be run. Designed for CI.",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"Zscaler MCP Server version {__version__}",
        help="Show version information and exit.",
    )

    return parser.parse_args()


def _check_env_file_security() -> None:
    """Log an advisory if credentials are loaded from a plaintext .env file.

    This is perfectly fine for local development — .env is the standard way
    to configure MCP servers. The warning simply reminds operators to use
    a secrets backend (Docker secrets, Kubernetes secrets, AWS Secrets Manager,
    HashiCorp Vault, etc.) when deploying to shared or production environments.
    """
    secret_keys = ("ZSCALER_CLIENT_SECRET", "ZSCALER_MCP_AUTH_API_KEY", "ZSCALER_PRIVATE_KEY")
    env_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    ]

    for env_path in env_paths:
        try:
            if not os.path.isfile(env_path):
                continue
            with open(env_path, "r") as f:
                content = f.read()
            found = [
                k
                for k in secret_keys
                if k in content
                and not all(
                    line.strip().startswith("#") for line in content.splitlines() if k in line
                )
            ]
            if found:
                log_security_warning(
                    "Credentials detected in plaintext .env file",
                    [
                        f"File: {env_path}",
                        f"Keys: {', '.join(found)}",
                        "",
                        "This is fine for local development, but for production consider:",
                        "  - Docker: use 'docker run -e' or Docker Secrets",
                        "  - Kubernetes: use Kubernetes Secrets or external-secrets",
                        "  - AWS: use Secrets Manager (ZSCALER_SECRET_NAME)",
                        "  - Enterprise: use HashiCorp Vault or similar",
                        "",
                        "Ensure .env is in .gitignore and never committed to source control.",
                    ],
                )
                return
        except OSError:
            continue


def main():
    """Main entry point for the Zscaler Integrations MCP Server."""
    # Load environment variables - try project root (editable install) then CWD
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_pkg_dir)
    load_dotenv(os.path.join(_project_root, ".env"))
    load_dotenv()  # CWD override

    _check_env_file_security()

    # Cloud secret managers — fetch credentials before server init
    from zscaler_mcp.cloud import gcp_secrets

    if gcp_secrets.is_enabled():
        gcp_secrets.load_secrets()

    # Parse command line arguments (includes environment variable defaults)
    args = parse_args()

    if getattr(args, "log_tool_calls", False):
        from zscaler_mcp.common.tool_helpers import enable_tool_call_logging

        enable_tool_call_logging()

    if getattr(args, "list_tools", False):
        list_available_tools(
            selected_services=args.services,
            enabled_tools=set(args.tools) if args.tools else None,
        )
        sys.exit(0)

    if getattr(args, "generate_auth_token", None):
        generate_auth_token(args.generate_auth_token)
        sys.exit(0)

    if getattr(args, "generate_docs", False):
        from zscaler_mcp.common import docgen

        written = docgen.generate_docs()
        if not written:
            print("All auto-managed doc regions are already up to date.")
        else:
            print("Updated auto-managed regions in:")
            for p in written:
                try:
                    rel = p.relative_to(docgen.REPO_ROOT)
                except ValueError:
                    rel = p
                print(f"  {rel}")
        sys.exit(0)

    if getattr(args, "check_docs", False):
        from zscaler_mcp.common import docgen

        stale = docgen.check_docs()
        if not stale:
            print("Docs are in sync with the live tool inventory.")
            sys.exit(0)
        print("The following files have stale auto-managed regions:")
        for p in stale:
            try:
                rel = p.relative_to(docgen.REPO_ROOT)
            except ValueError:
                rel = p
            print(f"  {rel}")
        print()
        print("Run `zscaler-mcp --generate-docs` to refresh them.")
        sys.exit(1)

    try:
        # Parse write_tools into a set
        write_tools = None
        if args.write_tools:
            write_tools = set(t.strip() for t in args.write_tools.split(","))

        disabled_tools = None
        if args.disabled_tools:
            disabled_tools = set(t.strip() for t in args.disabled_tools.split(",") if t.strip())

        disabled_services = None
        if args.disabled_services:
            disabled_services = set(s.strip() for s in args.disabled_services.split(",") if s.strip())

        toolsets = None
        if getattr(args, "toolsets", None):
            toolsets = set(t.strip() for t in args.toolsets.split(",") if t.strip())

        # Create and run the server
        server = ZscalerMCPServer(
            client_id=args.client_id,
            client_secret=args.client_secret,
            customer_id=args.customer_id,
            vanity_domain=args.vanity_domain,
            cloud=args.cloud,
            debug=args.debug,
            enabled_services=set(args.services),
            enabled_tools=set(args.tools),
            user_agent_comment=args.user_agent_comment,
            enable_write_tools=args.enable_write_tools,
            write_tools=write_tools,
            disabled_tools=disabled_tools,
            disabled_services=disabled_services,
            toolsets=toolsets,
            disable_entitlement_filter=getattr(args, "no_entitlement_filter", False),
            host=args.host,
        )
        logger.info("Starting server with %s transport", args.transport)
        server.run(args.transport, host=args.host, port=args.port)
    except RuntimeError as e:
        logger.error("Runtime error: %s", e)
        sys.exit(1)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        # Catch any other exceptions to ensure graceful shutdown
        logger.error("Unexpected error running server: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
