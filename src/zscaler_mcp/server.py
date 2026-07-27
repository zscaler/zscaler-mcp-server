"""v2 MCP server entry point — FastMCP-backed, full v1 security parity.

Tools are not listed here. They register themselves via the ``@tool`` decorator
at their own definition site; the server calls :func:`discover_tools` to import
the ``tools/`` tree (firing the decorators) and then selects the visible subset
via :meth:`Registry.select` — the same filtering precedence v1 applies, but as a
query over self-declared records (DESIGN.md §6).

Each tool advertises BOTH a flat ``inputSchema`` (from the input model) and an
``outputSchema`` (from the curated view), so the shape the agent sees and the
shape the server advertises can never drift.

The security layer is carried forward from v1 verbatim in behaviour:

* **MCP client auth** (HTTP only, on by default) — jwt / api-key / zscaler /
  oauth-proxy stub, via :func:`apply_auth_middleware`.
* **Source-IP ACL** — :class:`SourceIPMiddleware`.
* **Transport hardening** — trailing-slash / content-type / GET-405 / health.
* **HMAC confirmation for destructive ops** — wrapped onto delete tools in the
  bridge (v1 parity: only delete/bulk-delete confirm; create/update are gated by
  the ``--write-tools`` allowlist alone).
* **Output sanitization + audit logging** — wrapped onto every tool in the bridge.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Iterable

from dotenv import load_dotenv
from fastmcp import FastMCP

from zscaler_mcp import __version__
from zscaler_mcp.common.logging import configure_logging, log_security_warning
from zscaler_mcp.prompts import PROMPT_REGISTRY, build_function_prompt, discover_prompts
from zscaler_mcp.registry import REGISTRY, build_function_tool, discover_tools
from zscaler_mcp.security import (
    SourceIPMiddleware,
    apply_auth_middleware,
    apply_entitlement_filter,
    apply_transport_hardening,
    get_allowed_source_ips,
    resolve_fastmcp_auth,
    validate_host_binding,
)

logger = logging.getLogger("zscaler_mcp")

DEFAULT_MCP_PATH = "/mcp"


def _warn_unknown_toolsets(selection: Iterable[str] | None, flag: str) -> None:
    """Warn about toolset ids that match nothing in the registry.

    Toolset ids are exact (no globbing), so a typo would otherwise be silent —
    and for ``--toolsets`` it is silent in the worst possible way: the selection
    matches nothing and the server starts with ZERO tools. Warn and continue,
    which is the documented contract, rather than failing the boot.
    """
    if not selection:
        return
    known = REGISTRY.toolsets()
    unknown = sorted(set(selection) - known)
    if not unknown:
        return
    logger.warning(
        "%s: unknown toolset id(s) %s — ignored. Known toolsets: %s",
        flag,
        ", ".join(repr(u) for u in unknown),
        ", ".join(sorted(known)),
    )


def _resolve_entitled_services(disable_entitlement_filter: bool) -> set[str] | None:
    """Return the set of OneAPI-entitled service codes, or ``None`` to skip.

    ``None`` means "apply no entitlement downscoping" — either the operator
    disabled the filter, or the filter ran but couldn't make a confident
    decision (missing creds, network/decode failure, empty service-info). In
    every skip case the tool surface is left untouched and a single line is
    logged, exactly like v1's non-fatal behaviour.
    """
    if disable_entitlement_filter:
        logger.info("OneAPI entitlement filter disabled by configuration.")
        return None

    available = REGISTRY.services()
    try:
        allowed, status = apply_entitlement_filter(available)
    except Exception as exc:  # pragma: no cover - defensive, filter is non-fatal
        logger.warning("OneAPI entitlement filter error (skipped): %s", exc)
        return None

    if allowed is None:
        logger.warning("OneAPI %s", status)
        return None

    logger.info("OneAPI %s", status)
    return allowed


def build_server(
    *,
    enabled_services: Iterable[str] | None = None,
    disabled_services: Iterable[str] | None = None,
    enabled_toolsets: Iterable[str] | None = None,
    disabled_toolsets: Iterable[str] | None = None,
    enable_write: bool = False,
    write_allowlist: Iterable[str] | None = None,
    disabled_patterns: Iterable[str] | None = None,
    disable_entitlement_filter: bool = False,
    fastmcp_auth: object | None = None,
) -> FastMCP:
    """Discover tools, apply the filter selection, and wire up the FastMCP server.

    The filter arguments mirror v1's knobs (toolsets / entitlement / write
    allowlist / disabled patterns) and are resolved once here via the registry
    query. Each selected spec is bridged onto a FastMCP ``FunctionTool`` that
    carries the flat input schema, the curated output schema, and the security wrap.

    Args:
        disable_entitlement_filter: When True, skip the OneAPI product
            entitlement downscope (env opt-out: ``ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER``).
        fastmcp_auth: An optional ``fastmcp.server.auth.AuthProvider`` (e.g.
            ``OIDCProxy``). When given, it is passed to ``FastMCP(auth=...)`` and
            FastMCP wires the OAuth routes + RequireAuthMiddleware natively. The
            env-var ``AuthMiddleware`` path is bypassed for this server.
    """
    discover_tools()

    _warn_unknown_toolsets(enabled_toolsets, "--toolsets")
    _warn_unknown_toolsets(disabled_toolsets, "--disabled-toolsets")

    entitled_services = _resolve_entitled_services(disable_entitlement_filter)

    selected = REGISTRY.select(
        enabled_services=enabled_services,
        disabled_services=disabled_services,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
        entitled_services=entitled_services,
        enable_write=enable_write,
        write_allowlist=write_allowlist,
        disabled_patterns=disabled_patterns,
    )

    server = FastMCP("zscaler-mcp", auth=fastmcp_auth) if fastmcp_auth else FastMCP("zscaler-mcp")
    for spec in selected:
        server.add_tool(build_function_tool(spec))

    names = sorted(spec.name for spec in selected)
    logger.info(
        "zscaler-mcp registered %d tool(s): %s",
        len(names),
        ", ".join(names) or "(none)",
    )

    # MCP Prompts (user-invokable playbooks). Discovered like tools, but gated to
    # the services that actually survived tool filtering — a ZDX prompt is only
    # offered when ZDX tools are loaded, so the prompt menu never advertises a
    # workflow the agent has no tools to execute.
    discover_prompts()
    visible_services = {spec.service for spec in selected}
    prompt_specs = PROMPT_REGISTRY.select(visible_services=visible_services)
    for prompt_spec in prompt_specs:
        server.add_prompt(build_function_prompt(prompt_spec))

    if prompt_specs:
        logger.info(
            "zscaler-mcp registered %d prompt(s): %s",
            len(prompt_specs),
            ", ".join(sorted(p.name for p in prompt_specs)),
        )

    return server


# ---------------------------------------------------------------------------
# Transport runners
# ---------------------------------------------------------------------------


def _tls_kwargs_from_env() -> dict:
    """Build TLS/SSL kwargs for uvicorn from environment variables (v1 parity).

    Env vars:
        ZSCALER_MCP_TLS_CERTFILE          - Path to PEM certificate file
        ZSCALER_MCP_TLS_KEYFILE           - Path to PEM private key file
        ZSCALER_MCP_TLS_KEYFILE_PASSWORD  - Password for encrypted key (optional)
        ZSCALER_MCP_TLS_CA_CERTS          - CA bundle for client cert validation (optional)

    Returns an empty dict when TLS is not configured. Raises ``SystemExit`` when
    the configuration is incomplete or a referenced file is missing.
    """
    certfile = os.getenv("ZSCALER_MCP_TLS_CERTFILE", "").strip()
    keyfile = os.getenv("ZSCALER_MCP_TLS_KEYFILE", "").strip()

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

    tls_kwargs: dict = {"ssl_certfile": certfile, "ssl_keyfile": keyfile}

    password = os.getenv("ZSCALER_MCP_TLS_KEYFILE_PASSWORD", "").strip()
    if password:
        tls_kwargs["ssl_keyfile_password"] = password

    ca_certs = os.getenv("ZSCALER_MCP_TLS_CA_CERTS", "").strip()
    if ca_certs:
        if not os.path.isfile(ca_certs):
            raise SystemExit(f"ERROR: TLS CA certificate file not found: {ca_certs}")
        tls_kwargs["ssl_ca_certs"] = ca_certs

    return tls_kwargs


def _run_http(
    server: FastMCP,
    *,
    transport: str,
    host: str,
    port: int,
    debug: bool,
) -> None:
    """Run an HTTP transport (streamable-http / sse) with the full middleware stack.

    Mirrors v1's ``ZscalerMCPServer.run`` wiring order:
    auth (innermost app wrap) → source-IP ACL → transport hardening (outermost).
    """
    import uvicorn

    # TLS: when certs are configured, uvicorn terminates HTTPS in-process and the
    # plaintext-HTTP policy is satisfied without ZSCALER_MCP_ALLOW_HTTP.
    tls_kwargs = _tls_kwargs_from_env()
    scheme = "https" if tls_kwargs else "http"

    allow_http = os.getenv("ZSCALER_MCP_ALLOW_HTTP", "").lower() in ("true", "1", "yes")
    is_localhost = host in ("127.0.0.1", "localhost", "::1")
    if not tls_kwargs and not is_localhost and not allow_http:
        log_security_warning(
            "Refusing to bind a non-localhost address over plaintext HTTP",
            [
                f"The server was asked to listen on {host}:{port} without TLS.",
                "Provide TLS certs (ZSCALER_MCP_TLS_CERTFILE / ZSCALER_MCP_TLS_KEYFILE),",
                "or set ZSCALER_MCP_ALLOW_HTTP=true to allow plaintext (only if TLS is",
                "terminated by an overlay/reverse proxy), or bind to 127.0.0.1.",
            ],
        )
        raise SystemExit(
            "ERROR: plaintext HTTP on a non-localhost bind requires TLS certs "
            "or ZSCALER_MCP_ALLOW_HTTP=true"
        )

    # Refuse to bind a public interface without explicit Host validation config.
    validate_host_binding(host)

    fastmcp_transport = "http" if transport == "streamable-http" else "sse"
    app = server.http_app(path=DEFAULT_MCP_PATH, transport=fastmcp_transport)

    # 1. Auth middleware (innermost wrap around the MCP app).
    app = apply_auth_middleware(app, transport)

    # 2. Source-IP ACL.
    allowed_ips = get_allowed_source_ips()
    if allowed_ips is not None:
        logger.info("Source IP ACL active: %s", allowed_ips)
        app = SourceIPMiddleware(app, allowed_ips)

    # 3. Transport hardening (outermost: health/host-validation/slash/content-type/GET-405).
    app = apply_transport_hardening(app, transport, mcp_path=DEFAULT_MCP_PATH)

    logger.info(
        "Starting %s transport on %s://%s:%d (path=%s, tls=%s)",
        transport,
        scheme,
        host,
        port,
        DEFAULT_MCP_PATH,
        "on" if tls_kwargs else "off",
    )
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug" if debug else "info",
        **tls_kwargs,
    )


# ---------------------------------------------------------------------------
# .env resolution + startup advisories
# ---------------------------------------------------------------------------


def _resolve_dotenv_path(explicit: str | None = None) -> str | None:
    """Resolve which ``.env`` file to load, honoring CLI/env overrides.

    Search order (v1 parity, adjusted for v2's ``src/`` layout):
        1. Explicit ``--dotenv-path`` / ``ZSCALER_MCP_DOTENV_PATH`` if set
        2. ``<project_root>/.env`` (editable install; project root is two
           levels up from this module under ``src/zscaler_mcp/``)
        3. ``<cwd>/.env``

    Returns the absolute path of the file actually loaded, or ``None`` if no
    ``.env`` was found (the server still runs — every knob has an env-var
    fallback). The returned value is recorded in the PID file so
    ``zscaler-mcp reload`` / ``restart`` re-read the same source.
    """
    candidate = explicit or os.environ.get("ZSCALER_MCP_DOTENV_PATH", "").strip()
    if candidate:
        candidate = os.path.abspath(os.path.expanduser(candidate))
        if os.path.isfile(candidate):
            load_dotenv(candidate, override=True)
            return candidate
        logger.warning("dotenv path %s does not exist — falling back to defaults", candidate)

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(pkg_dir))
    project_env = os.path.join(project_root, ".env")
    cwd_env = os.path.abspath(os.path.join(os.getcwd(), ".env"))

    loaded_from: str | None = None
    if os.path.isfile(project_env):
        load_dotenv(project_env)
        loaded_from = project_env
    if os.path.isfile(cwd_env) and cwd_env != project_env:
        load_dotenv(cwd_env, override=True)
        loaded_from = cwd_env
    return loaded_from


def _check_env_file_security() -> None:
    """Log an advisory if credentials are loaded from a plaintext ``.env`` file.

    Fine for local dev — ``.env`` is the standard way to configure MCP servers.
    The advisory reminds operators to use a secrets backend (Docker/K8s secrets,
    AWS Secrets Manager, Vault, …) for shared/production environments.
    """
    secret_keys = ("ZSCALER_CLIENT_SECRET", "ZSCALER_MCP_AUTH_API_KEY", "ZSCALER_PRIVATE_KEY")
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(pkg_dir))
    env_paths = [os.path.join(os.getcwd(), ".env"), os.path.join(project_root, ".env")]

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


def list_available_tools(
    *,
    enabled_services: Iterable[str] | None = None,
    disabled_services: Iterable[str] | None = None,
) -> None:
    """Print every registered tool (name, action, service) and exit-friendly.

    Reads the registry populated by import-time decorators — no SDK/credentials
    needed. Honors the same service filters as the serve path so ``--list-tools
    --services zpa`` shows only what would actually be registered.
    """
    discover_tools()
    specs = REGISTRY.select(
        enabled_services=enabled_services,
        disabled_services=disabled_services,
        enable_write=True,  # show write tools too, tagged, so the list is complete
    )
    by_service: dict[str, list] = {}
    for spec in specs:
        by_service.setdefault(spec.service, []).append(spec)

    total = len(specs)
    print(
        f"Zscaler MCP Server v{__version__} — {total} tool(s) across {len(by_service)} service(s)"
    )
    for service in sorted(by_service):
        rows = sorted(by_service[service], key=lambda s: s.name)
        print(f"\n{service} ({len(rows)}):")
        for spec in rows:
            tag = "" if spec.action == "read" else f" [{spec.action}]"
            summary = (spec.description or "").strip().splitlines()[0] if spec.description else ""
            print(f"  {spec.name}{tag} — {summary}")


def generate_auth_token(fmt: str = "basic") -> None:
    """Generate an auth token and print ready-to-use MCP client config snippets."""
    import base64

    client_id = os.environ.get("ZSCALER_CLIENT_ID", "")
    client_secret = os.environ.get("ZSCALER_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Error: ZSCALER_CLIENT_ID and ZSCALER_CLIENT_SECRET must be set.")
        print("Set them in your .env file or as environment variables.")
        raise SystemExit(1)

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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


def _resolve_toolsets(value: str | None) -> list[str] | None:
    """Resolve the ``--toolsets`` selection, honoring v1's keyword semantics.

    v1 treats ``all`` and ``default`` as special keywords meaning "every
    toolset", NOT as literal toolset ids. v2 mirrors that: either keyword (or an
    empty value) resolves to ``None`` so the registry applies no toolset filter.
    Any other value is treated as an explicit comma-separated id list.
    """
    items = _parse_csv(value)
    if items is None:
        return None
    if any(kw in items for kw in ("all", "default")):
        return None
    return items


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zscaler-mcp",
        description="Zscaler MCP server — typed tool inputs, verbatim Zscaler API records out.",
    )
    p.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=os.getenv("ZSCALER_MCP_TRANSPORT", "stdio"),
        help="Transport mode (default: stdio, or ZSCALER_MCP_TRANSPORT).",
    )
    p.add_argument(
        "--host",
        default=os.getenv("ZSCALER_MCP_HOST", "127.0.0.1"),
        help="Bind address for HTTP transports (default: 127.0.0.1).",
    )
    p.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ZSCALER_MCP_PORT", "8000")),
        help="Listen port for HTTP transports (default: 8000).",
    )
    p.add_argument(
        "--services",
        "-s",
        default=os.getenv("ZSCALER_MCP_SERVICES", ""),
        metavar="SERVICE1,SERVICE2,...",
        help=(
            "Comma-separated services to enable (e.g. 'zia,zpa,zdx'). "
            "Default: all services (env: ZSCALER_MCP_SERVICES)."
        ),
    )
    p.add_argument(
        "--disabled-services",
        default=os.getenv("ZSCALER_MCP_DISABLED_SERVICES", ""),
        metavar="SERVICE1,SERVICE2,...",
        help=(
            "Comma-separated services to exclude (e.g. 'zcc,zdx'). "
            "(env: ZSCALER_MCP_DISABLED_SERVICES)."
        ),
    )
    p.add_argument(
        "--toolsets",
        default=os.getenv("ZSCALER_MCP_TOOLSETS", ""),
        help="Comma-separated toolset ids to enable (default: all).",
    )
    p.add_argument(
        "--disabled-toolsets",
        default=os.getenv("ZSCALER_MCP_DISABLED_TOOLSETS", ""),
        metavar="TOOLSET1,TOOLSET2,...",
        help=(
            "Comma-separated toolset ids to exclude (e.g. 'zia_ssl_inspection,zia_admin'). "
            "The blocklist complement to --toolsets: load everything except these. "
            "Exact ids only (no wildcards); wins over --toolsets when both name a "
            "toolset (env: ZSCALER_MCP_DISABLED_TOOLSETS)."
        ),
    )
    p.add_argument(
        "--enable-write-tools",
        action="store_true",
        default=os.getenv("ZSCALER_MCP_WRITE_ENABLED", "").lower() in ("true", "1", "yes"),
        help=(
            "Enable write operations (create/update/delete). Off by default for safety. "
            "Combine with --write-tools to narrow the allowlist "
            "(env: ZSCALER_MCP_WRITE_ENABLED)."
        ),
    )
    p.add_argument(
        "--write-tools",
        default=os.getenv("ZSCALER_MCP_WRITE_TOOLS", ""),
        help=(
            "Enable + allowlist write tools (fnmatch patterns, e.g. 'zpa_create_*'). "
            "Write tools are disabled unless this or --enable-write-tools is set."
        ),
    )
    p.add_argument(
        "--disabled-tools",
        default=os.getenv("ZSCALER_MCP_DISABLED_TOOLS", ""),
        help="Comma-separated tool-name patterns to exclude (fnmatch).",
    )
    p.add_argument(
        "--no-entitlement-filter",
        action="store_true",
        default=os.getenv("ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER", "").lower()
        in ("true", "1", "yes"),
        help=(
            "Skip the OneAPI entitlement filter that downscopes tools to the "
            "products the configured ZSCALER_CLIENT_ID is entitled to. The "
            "filter is non-fatal and self-skips on any failure; use this only "
            "as an emergency override."
        ),
    )
    p.add_argument(
        "--log-tool-calls",
        action="store_true",
        default=os.getenv("ZSCALER_MCP_LOG_TOOL_CALLS", "").lower() == "true",
        help="Enable per-tool-call audit logging.",
    )
    p.add_argument(
        "--generate-docs",
        action="store_true",
        help=(
            "Regenerate the auto-generated Markdown regions (supported-tools, "
            "README service summary, toolset catalog) from the live tool "
            "inventory, then exit. Run after adding/renaming/removing a tool."
        ),
    )
    p.add_argument(
        "--check-docs",
        action="store_true",
        help=(
            "Exit 0 if every auto-generated region is in sync with the live "
            "tool inventory, else exit 1 with the list of stale files. For CI."
        ),
    )
    p.add_argument(
        "--user-agent-comment",
        default=os.getenv("ZSCALER_MCP_USER_AGENT_COMMENT", ""),
        help=(
            "Suffix appended to the SDK's outbound User-Agent header "
            "(env: ZSCALER_MCP_USER_AGENT_COMMENT)."
        ),
    )
    p.add_argument(
        "--list-tools",
        action="store_true",
        help="List all registered tool names + descriptions, then exit.",
    )
    p.add_argument(
        "--generate-auth-token",
        nargs="?",
        const="basic",
        choices=["basic", "bearer"],
        metavar="FORMAT",
        help=(
            "Generate an auth token from ZSCALER_CLIENT_ID/SECRET and print MCP "
            "client config snippets, then exit. 'basic' (default) for zscaler "
            "auth mode, 'bearer' for api-key mode."
        ),
    )
    p.add_argument(
        "--dotenv-path",
        default=os.getenv("ZSCALER_MCP_DOTENV_PATH", ""),
        metavar="PATH",
        help=(
            "Explicit path to the .env file to load, overriding the default "
            "search. Recorded in the PID file so reload/restart re-read the "
            "same source. (env: ZSCALER_MCP_DOTENV_PATH)."
        ),
    )
    p.add_argument(
        "--pid-file",
        default=os.getenv("ZSCALER_MCP_PID_FILE", ""),
        metavar="PATH",
        help=(
            "Override the PID file location used by the lifecycle subcommands. "
            "Defaults to /var/run/zscaler-mcp.pid (or /tmp fallback). Set per "
            "instance when running multiple servers. (env: ZSCALER_MCP_PID_FILE)."
        ),
    )
    p.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"Zscaler MCP Server version {__version__}",
        help="Show version information and exit.",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("ZSCALER_MCP_DEBUG", "").lower() == "true",
        help="Enable verbose debug logging.",
    )

    # Lifecycle subcommands (reload / restart / status / stop / update). Added
    # last so all top-level options remain valid for the default serve path
    # (no subcommand). The chosen subcommand lands in args.command (None when
    # the bare `zscaler-mcp` serve path is used).
    from zscaler_mcp import lifecycle

    lifecycle.register_subparsers(p)

    return p


def main() -> None:
    # First-pass .env load BEFORE parse_args() so every CLI flag's env-var
    # default is already resolved. The exact path is recomputed (and recorded
    # in the PID file) after parsing so an explicit --dotenv-path wins.
    _resolve_dotenv_path()
    _check_env_file_security()

    # Optionally hydrate credentials from GCP Secret Manager BEFORE anything
    # reads them (opt-in via ZSCALER_MCP_GCP_SECRET_MANAGER=true). No-op
    # otherwise; the google-cloud dep is only imported when enabled.
    from zscaler_mcp.cloud import load_secrets

    load_secrets()

    args = build_parser().parse_args()

    # Lifecycle subcommands (reload/restart/status/stop/update) short-circuit
    # before any server setup. args.command is set by lifecycle.register_subparsers
    # and is None on the default serve path.
    command = getattr(args, "command", None)
    if isinstance(command, str) and command:
        from zscaler_mcp import lifecycle

        if args.pid_file:
            os.environ["ZSCALER_MCP_PID_FILE"] = args.pid_file
        raise SystemExit(lifecycle.dispatch(command, args))

    # Doc generation short-circuits before any server/credential wiring — the
    # generator reads the tool registry (populated by import-time decorators),
    # not the live SDK. Mirrors v1's --generate-docs / --check-docs.
    if args.generate_docs:
        from zscaler_mcp.common import docgen

        written = docgen.generate_docs()
        if written:
            print(f"Regenerated {len(written)} file(s):")
            for path in written:
                try:
                    rel = path.relative_to(docgen.REPO_ROOT)
                except ValueError:
                    rel = path
                print(f"  {rel}")
        else:
            print("Docs already in sync — nothing to regenerate.")
        raise SystemExit(0)

    if args.check_docs:
        from zscaler_mcp.common import docgen

        stale = docgen.check_docs()
        if stale:
            print("Stale auto-generated files (run `zscaler-mcp --generate-docs`):")
            for path in stale:
                try:
                    rel = path.relative_to(docgen.REPO_ROOT)
                except ValueError:
                    rel = path
                print(f"  {rel}")
            raise SystemExit(1)
        print("Docs are in sync with the live tool inventory.")
        raise SystemExit(0)

    # Re-resolve .env with the explicit CLI flag honoured; the returned path is
    # recorded in the PID file so lifecycle handlers re-read the same source.
    final_dotenv_path = _resolve_dotenv_path(args.dotenv_path or None)

    # Surface the user-agent comment to the lazily-created SDK client via env.
    if args.user_agent_comment:
        os.environ["ZSCALER_MCP_USER_AGENT_COMMENT"] = args.user_agent_comment

    enabled_services = _parse_csv(args.services)
    disabled_services = _parse_csv(args.disabled_services)

    if args.list_tools:
        list_available_tools(
            enabled_services=enabled_services,
            disabled_services=disabled_services,
        )
        raise SystemExit(0)

    if args.generate_auth_token:
        generate_auth_token(args.generate_auth_token)
        raise SystemExit(0)

    if args.log_tool_calls:
        os.environ["ZSCALER_MCP_LOG_TOOL_CALLS"] = "true"
        from zscaler_mcp.security import enable_tool_call_logging

        enable_tool_call_logging()

    # stdio must log to stderr so stdout stays a clean JSON-RPC stream.
    configure_logging(debug=args.debug, name="zscaler_mcp", use_stderr=(args.transport == "stdio"))

    # Write tools are enabled when an allowlist is given, --enable-write-tools is
    # passed, OR ZSCALER_MCP_WRITE_ENABLED=true (parity with v1's two-knob model:
    # --enable-write-tools flips the master switch; --write-tools narrows scope).
    write_allowlist = _parse_csv(args.write_tools)
    write_enabled = write_allowlist is not None or args.enable_write_tools

    # oidcproxy env-var mode → build a fastmcp auth provider FastMCP wires
    # natively. Every other mode returns None (handled by AuthMiddleware at the
    # ASGI layer). stdio never authenticates.
    fastmcp_auth = None
    if args.transport != "stdio":
        fastmcp_auth = resolve_fastmcp_auth()

    server = build_server(
        enabled_services=enabled_services,
        disabled_services=disabled_services,
        enabled_toolsets=_resolve_toolsets(args.toolsets),
        disabled_toolsets=_parse_csv(args.disabled_toolsets),
        enable_write=write_enabled,
        write_allowlist=write_allowlist,
        disabled_patterns=_parse_csv(args.disabled_tools),
        disable_entitlement_filter=args.no_entitlement_filter,
        fastmcp_auth=fastmcp_auth,
    )

    # Process lifecycle: write the PID file and install the SIGHUP (reload) /
    # SIGUSR2 (restart) handlers so the lifecycle subcommands work against this
    # PID. Done after build (so a misconfigured server leaves no stale PID file)
    # but before run(). atexit-removed on clean shutdown. Best-effort: a
    # non-writable PID path only disables the lifecycle subcommands, never the
    # server itself.
    import atexit
    import time as _time

    from zscaler_mcp import lifecycle

    if args.pid_file:
        os.environ["ZSCALER_MCP_PID_FILE"] = args.pid_file
    pid_file_path = lifecycle.default_pid_file_path()
    lifecycle_state = lifecycle.LifecycleState(
        pid=os.getpid(),
        started_at=_time.time(),
        transport=args.transport,
        host=args.host,
        port=args.port,
        dotenv_path=final_dotenv_path,
        argv=list(sys.argv),
        python_executable=sys.executable,
        version=__version__,
    )
    try:
        lifecycle.write_pid_file(lifecycle_state, pid_file_path)
        logger.info("Wrote PID file: %s (pid=%d)", pid_file_path, lifecycle_state.pid)
    except OSError as exc:
        logger.warning(
            "Could not write PID file %s: %s — lifecycle subcommands "
            "(reload/restart/status/stop) will not work for this instance.",
            pid_file_path,
            exc,
        )
    atexit.register(lifecycle.remove_pid_file, pid_file_path)
    lifecycle.install_serve_handlers(lifecycle_state, final_dotenv_path)

    logger.info(
        "zscaler-mcp starting (transport=%s) — agent-first response shaping enabled",
        args.transport,
    )

    if args.transport == "stdio":
        server.run("stdio")
    else:
        _run_http(
            server,
            transport=args.transport,
            host=args.host,
            port=args.port,
            debug=args.debug,
        )


if __name__ == "__main__":
    main()
