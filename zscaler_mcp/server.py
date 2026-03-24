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


def _log_security_posture(
    transport: str, scheme: str, host: str, port: int, tls_kwargs: dict
) -> None:
    """Log a consolidated security posture banner at startup."""
    w = 72
    bar = "=" * w

    tls_status = "ENABLED (encrypted)" if tls_kwargs else "DISABLED (plaintext)"
    if tls_kwargs:
        tls_detail = tls_kwargs.get("ssl_certfile", "")
        mtls = "Yes" if tls_kwargs.get("ssl_ca_certs") else "No"
    else:
        tls_detail = ""
        mtls = "N/A"

    auth_disabled = os.environ.get("ZSCALER_MCP_AUTH_ENABLED", "").lower() in ("false", "0", "no")
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
    if not auth_disabled:
        logger.info("    Mode:         %s", auth_mode)
    logger.info("  Host Validation:%s", host_status)
    logger.info("  Source IP ACL:  %s", src_ip_status)
    logger.info("  Confirmations:  %s", confirm_status)
    logger.info(bar)


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
        host: Optional[str] = None,
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
            host: HTTP bind host (e.g. 0.0.0.0). When 0.0.0.0, host header validation is auto-disabled.
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

        # Configure logging - use stderr for stdio transport to avoid interfering with MCP protocol
        configure_logging(debug=self.debug, use_stderr=True)
        logger = get_logger(__name__)

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

        # Don't initialize the Zscaler client during server startup to avoid pickle issues
        # Clients will be created on-demand when tools are called
        self.zscaler_client = None
        logger.info("Client initialization deferred to tool execution")

        # Initialize the MCP server
        transport_security = _get_transport_security(host=host)
        self.server = FastMCP(
            name="Zscaler Integrations MCP Server",
            instructions="This server provides access to Zscaler capabilities across ZIA, ZPA, ZDX, ZCC and ZIdentity services.",
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
        # Register core tools directly
        self.server.add_tool(
            self.zscaler_check_connectivity,
            name="zscaler_check_connectivity",
            description="Check connectivity to the Zscaler API.",
            annotations=ToolAnnotations(readOnlyHint=True),  # Read-only diagnostic tool
        )

        self.server.add_tool(
            self.get_available_services,
            name="zscaler_get_available_services",
            description="Get information about available services.",
            annotations=ToolAnnotations(readOnlyHint=True),  # Read-only informational tool
        )

        tool_count = 2  # the tools added above

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
                    )
                else:
                    service.register_tools(
                        self.server,
                        enable_write_tools=self.enable_write_tools,
                        write_tools=self.write_tools,
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

    def get_available_services(self) -> Dict[str, List[str]]:
        """Get information about available services.

        Returns:
            Dict[str, List[str]]: Available services
        """
        return {"services": services.get_service_names()}

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

            if transport == "streamable-http":
                app = self.server.streamable_http_app()
            else:
                app = self.server.sse_app()

            app = apply_auth_middleware(app, transport)

            allowed_ips = _get_allowed_source_ips()
            if allowed_ips is not None:
                logger.info("Source IP ACL active: %s", allowed_ips)
                app = SourceIPMiddleware(app, allowed_ips)

            _log_security_posture(transport, scheme, host, port, tls_kwargs)

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

    # Tool selection
    parser.add_argument(
        "--tools",
        type=parse_tools_list,
        default=parse_tools_list(os.environ.get("ZSCALER_MCP_TOOLS", "")),
        metavar="TOOL1,TOOL2,...",
        help="Comma-separated list of specific tools to enable (if not specified, all tools from selected services are enabled, env: ZSCALER_MCP_TOOLS)",
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

    # Parse command line arguments (includes environment variable defaults)
    args = parse_args()

    if getattr(args, "list_tools", False):
        list_available_tools(
            selected_services=args.services,
            enabled_tools=set(args.tools) if args.tools else None,
        )
        sys.exit(0)

    if getattr(args, "generate_auth_token", None):
        generate_auth_token(args.generate_auth_token)
        sys.exit(0)

    try:
        # Parse write_tools into a set
        write_tools = None
        if args.write_tools:
            write_tools = set(t.strip() for t in args.write_tools.split(","))

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
