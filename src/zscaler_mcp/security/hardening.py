"""HTTP transport hardening + source-IP ACL middlewares.

Ported from v1 (``zscaler_mcp/server.py`` + ``zscaler_mcp/auth.py``). All four
hardening middlewares and the source-IP ACL are pure ASGI pre-processors —
framework-agnostic — so they carry over verbatim:

* :class:`SourceIPMiddleware` — 403 unless the client IP is on the allowlist.
* :class:`StripTrailingSlashMiddleware` — ``POST /mcp/`` → ``POST /mcp``.
* :class:`NormalizeContentTypeMiddleware` — ``application/json-rpc`` → ``application/json``.
* :class:`RejectNonSSEGetMiddleware` — FastMCP's 406-on-GET → a clean 405.
* :class:`HealthCheckMiddleware` — unconditional 200 on ``GET /health``.

Compliant clients (Claude Desktop, Cursor) pass through untouched; non-strict
clients (Gemini CLI, Bedrock AgentCore Harness, custom agents) get silently
corrected.
"""

from __future__ import annotations

import ipaddress
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source IP ACL
# ---------------------------------------------------------------------------


def _ip_matches(client_ip: str, allowed: list[str]) -> bool:
    """Return True if *client_ip* matches any entry in *allowed*.

    Supports exact addresses, CIDR notation, and the ``*`` / ``0.0.0.0/0``
    wildcard.
    """
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
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def get_allowed_source_ips() -> Optional[list[str]]:
    """Parse ``ZSCALER_MCP_ALLOWED_SOURCE_IPS`` into a list, or ``None``."""
    raw = os.getenv("ZSCALER_MCP_ALLOWED_SOURCE_IPS", "").strip()
    if not raw:
        return None
    entries = [e.strip() for e in raw.split(",") if e.strip()]
    return entries or None


class SourceIPMiddleware:
    """ASGI middleware that restricts access by client source IP.

    When configured, only requests from the allowed IPs / CIDRs are accepted;
    everything else gets a 403. Health-check paths are exempt so LB probes work.
    """

    SKIP_PATHS = frozenset({"/health", "/healthz", "/ready"})

    def __init__(self, app: Any, allowed_ips: list[str]):
        self.app = app
        self.allowed_ips = allowed_ips

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
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


# ---------------------------------------------------------------------------
# Host header validation (DNS-rebinding protection)
# ---------------------------------------------------------------------------


def get_allowed_hosts() -> Optional[list[str]]:
    """Parse ``ZSCALER_MCP_ALLOWED_HOSTS`` into a list, or ``None``.

    Entries may be exact (``example.com:443``), port-wildcarded
    (``example.com:*``), bare host (``example.com``), or the ``*`` catch-all.
    """
    raw = os.getenv("ZSCALER_MCP_ALLOWED_HOSTS", "").strip()
    if not raw:
        return None
    entries = [e.strip() for e in raw.split(",") if e.strip()]
    return entries or None


def host_validation_disabled() -> bool:
    """True when ``ZSCALER_MCP_DISABLE_HOST_VALIDATION`` opts out of Host checks."""
    return os.getenv("ZSCALER_MCP_DISABLE_HOST_VALIDATION", "").strip().lower() in (
        "true",
        "1",
        "yes",
    )


def _split_host_port(value: str) -> tuple[str, str]:
    """Split a ``host[:port]`` value, leaving IPv6 literals (``[::1]:80``) intact."""
    value = value.strip().lower()
    if value.startswith("["):  # bracketed IPv6 literal
        host, sep, port = value.rpartition("]:")
        if sep:
            return host + "]", port
        return value, ""
    if value.count(":") == 1:
        host, _, port = value.rpartition(":")
        return host, port
    return value, ""


def _host_matches(host_header: str, allowed: list[str]) -> bool:
    """Match a request ``Host`` header against the configured allowlist.

    Supports ``*`` (any host), ``host:*`` (any port), exact ``host:port``, and
    bare ``host`` (any port). Empty Host headers are rejected when an allowlist
    is configured.
    """
    host_header = host_header.strip().lower()
    if not host_header:
        return False
    h_host, h_port = _split_host_port(host_header)
    for entry in allowed:
        e = entry.strip().lower()
        if not e:
            continue
        if e == "*" or e == host_header:
            return True
        e_host, e_port = _split_host_port(e)
        if ":" in e:
            if e_port == "*" and e_host == h_host:
                return True
            if e_host == h_host and e_port == h_port:
                return True
        elif e == h_host:
            return True
    return False


class HostValidationMiddleware:
    """ASGI middleware that rejects requests whose ``Host`` header is not allowed.

    Zero-trust DNS-rebinding protection: only active when
    ``ZSCALER_MCP_ALLOWED_HOSTS`` is configured (and not disabled via
    ``ZSCALER_MCP_DISABLE_HOST_VALIDATION``). Health-check paths bypass the
    check so load-balancer probes keep working.
    """

    SKIP_PATHS = frozenset({"/health", "/healthz", "/ready"})

    def __init__(self, app: Any, allowed_hosts: list[str]):
        self.app = app
        self.allowed_hosts = allowed_hosts

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("path", "") in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        host = ""
        for name, value in scope.get("headers", []):
            if name == b"host":
                try:
                    host = value.decode("latin-1")
                except UnicodeDecodeError:
                    host = ""
                break

        if not _host_matches(host, self.allowed_hosts):
            from starlette.responses import JSONResponse

            body = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": (
                        f"Misdirected request: Host header '{host}' is not in the "
                        "allowed list (possible DNS rebinding attempt)"
                    ),
                },
            }
            # 421 Misdirected Request — the same status the MCP SDK's transport
            # security returns for a rejected Host.
            response = JSONResponse(body, status_code=421)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def validate_host_binding(host: str) -> None:
    """Refuse to bind a public interface without explicit Host validation config.

    Mirrors v1: binding to ``0.0.0.0`` requires either an
    ``ZSCALER_MCP_ALLOWED_HOSTS`` allowlist (recommended) or an explicit
    ``ZSCALER_MCP_DISABLE_HOST_VALIDATION=true`` opt-out. Anything else exits.
    """
    if host != "0.0.0.0":
        return
    if host_validation_disabled() or get_allowed_hosts() is not None:
        return
    raise SystemExit(
        "ERROR: Cannot bind to 0.0.0.0 without host validation configuration.\n"
        "Set one of:\n"
        "  ZSCALER_MCP_ALLOWED_HOSTS=your-host:*,localhost:*  (recommended)\n"
        "  ZSCALER_MCP_DISABLE_HOST_VALIDATION=true           (disables protection)\n"
    )


# ---------------------------------------------------------------------------
# Transport hardening middlewares
# ---------------------------------------------------------------------------


class StripTrailingSlashMiddleware:
    """Strip trailing slashes from HTTP request paths (``/mcp/`` → ``/mcp``)."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path != "/" and path.endswith("/"):
                scope["path"] = path.rstrip("/")
                raw_path = scope.get("raw_path")
                if isinstance(raw_path, bytes):
                    scope["raw_path"] = raw_path.rstrip(b"/") or b"/"
        await self.app(scope, receive, send)


class HealthCheckMiddleware:
    """Respond 200 OK to ``GET``/``HEAD`` on the health path, bypassing all layers."""

    def __init__(self, app: Any, path: str = "/health"):
        self.app = app
        self._path = path

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if (
            scope.get("type") == "http"
            and scope.get("method") in ("GET", "HEAD")
            and scope.get("path") == self._path
        ):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"cache-control", b"no-store"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"status":"ok"}' if scope["method"] == "GET" else b"",
                }
            )
            return
        await self.app(scope, receive, send)


class RejectNonSSEGetMiddleware:
    """Convert FastMCP's 406-on-GET into a clean 405 for non-SSE GET clients."""

    def __init__(self, app: Any, mcp_path: str = "/mcp"):
        self.app = app
        self._mcp_path = mcp_path

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if (
            scope.get("type") == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == self._mcp_path
        ):
            accept = b""
            for name, value in scope.get("headers", []):
                if name == b"accept":
                    accept = value
                    break
            try:
                accept_str = accept.decode("latin-1").lower()
            except UnicodeDecodeError:
                accept_str = ""
            if "text/event-stream" not in accept_str:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 405,
                        "headers": [
                            (b"content-type", b"text/plain; charset=utf-8"),
                            (b"allow", b"POST"),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": (
                            b"Method Not Allowed: this endpoint is POST-only. "
                            b"To receive server-initiated messages over SSE, "
                            b"reissue the GET with Accept: text/event-stream."
                        ),
                    }
                )
                return
        await self.app(scope, receive, send)


class NormalizeContentTypeMiddleware:
    """Normalise ``application/json-rpc`` to ``application/json``."""

    _JSON_RPC = "application/json-rpc"

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            headers = scope.get("headers")
            if headers:
                rewritten = []
                changed = False
                for name, value in headers:
                    if name == b"content-type":
                        try:
                            decoded = value.decode("utf-8")
                        except UnicodeDecodeError:
                            rewritten.append((name, value))
                            continue
                        if decoded.lower().startswith(self._JSON_RPC):
                            rest = decoded[len(self._JSON_RPC) :]
                            new_value = f"application/json{rest}".encode("utf-8")
                            rewritten.append((name, new_value))
                            changed = True
                            continue
                    rewritten.append((name, value))
                if changed:
                    scope["headers"] = rewritten
        await self.app(scope, receive, send)


def apply_transport_hardening(
    app: Any,
    transport: str,
    mcp_path: str = "/mcp",
    health_path: str = "/health",
) -> Any:
    """Wrap an ASGI app with the HTTP transport-hardening middlewares.

    No-op for stdio. The GET→405 middleware is layered only for
    streamable-http (SSE *requires* GET). Health check is outermost so probes
    bypass auth / source-IP / MCP entirely.
    """
    if transport == "stdio":
        return app
    inner = app
    if transport == "streamable-http":
        inner = RejectNonSSEGetMiddleware(inner, mcp_path=mcp_path)
    inner = StripTrailingSlashMiddleware(NormalizeContentTypeMiddleware(inner))

    # Host header validation (DNS-rebinding protection). ENABLED by default when
    # an allowlist is configured; explicitly disable via
    # ZSCALER_MCP_DISABLE_HOST_VALIDATION=true.
    if host_validation_disabled():
        from zscaler_mcp.common.logging import log_security_warning

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
    else:
        allowed_hosts = get_allowed_hosts()
        if allowed_hosts:
            logger.info("Host header allowlist active: %s", allowed_hosts)
            inner = HostValidationMiddleware(inner, allowed_hosts)

    return HealthCheckMiddleware(inner, path=health_path)
