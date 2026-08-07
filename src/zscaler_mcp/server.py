"""v2 MCP server entry point — MCPServer-backed, full v1 security parity.

Tools are not listed here. They register themselves via the ``@tool`` decorator
at their own definition site; the server calls :func:`discover_tools` to import
the ``tools/`` tree (firing the decorators) and then selects the visible subset
via :meth:`Registry.select` — the same filtering precedence v1 applies, but as a
query over self-declared records (DESIGN.md §6).

Each tool advertises BOTH a flat ``inputSchema`` (from the input model) and an
``outputSchema`` (from the curated view), so the shape the agent sees and the
shape the server advertises can never drift.

The security layer is carried forward from v1 verbatim in behaviour:

* **MCP client auth** (HTTP only, on by default) — jwt / api-key / zscaler via
  :func:`apply_auth_middleware`, or oidc via :func:`resolve_oidc_auth`, which
  configures the SDK's own resource-server enforcement instead.
* **Source-IP ACL** — :class:`SourceIPMiddleware`.
* **Transport hardening** — trailing-slash / content-type / GET-405 / health.
* **HMAC confirmation for destructive ops** — wrapped onto delete tools in the
  bridge (v1 parity: only delete/bulk-delete confirm; create/update are gated by
  the ``--write-tools`` allowlist alone).
* **Output sanitization + audit logging** — wrapped onto every tool in the bridge.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Iterable

from dotenv import load_dotenv
from mcp.server.caching import CacheHint
from mcp.server.mcpserver import MCPServer, RequestStateSecurity
from mcp.types import Icon

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
    resolve_oidc_auth,
    validate_host_binding,
)

logger = logging.getLogger("zscaler_mcp")

DEFAULT_MCP_PATH = "/mcp"

#: Presentation metadata for `server/discover`. Kept in step with the values the
#: MCP registry manifest (`server.json`) and the MCPB bundle
#: (`integrations/anthropic/manifest.json`) already publish, so the server does
#: not present one identity in a directory listing and a different one once a
#: client connects. `tests/test_server_metadata.py` asserts they stay aligned.
SERVER_TITLE = "Zscaler MCP Server"
SERVER_DESCRIPTION = (
    "Manage the Zscaler Zero Trust Exchange — ZPA, ZIA, ZDX, ZCC, ZCell, ZTW, "
    "ZIdentity, EASM, Z-Insights and ZMS — through the Model Context Protocol. "
    "Read-only by default; write tools require an explicit allowlist and every "
    "delete is confirmed by a human."
)
SERVER_WEBSITE_URL = "https://github.com/zscaler/zscaler-mcp-server"
#: Raw-content URL rather than a repo path: clients fetch this over HTTP and
#: cannot resolve a path relative to the source tree.
SERVER_ICON_URL = (
    "https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/assets/icon.png"
)

#: SEP-2549 freshness hints. Only ``tools/list`` is hinted, and only because this
#: server's inventory is genuinely immutable after startup: every filter
#: (toolsets, write allowlist, entitlement downscope) is resolved once during
#: registration and there is no runtime registration path, so the listing a
#: client receives cannot change while the connection lives. ``scope="public"``
#: follows from the same fact — the inventory is a property of this server's
#: configuration, identical for every caller, so sharing a cached copy across
#: authorization contexts leaks nothing. Re-check both claims before adding a
#: runtime "enable toolset" tool; that would make this hint a lie.
_TOOL_LIST_CACHE_HINTS = {"tools/list": CacheHint(ttl_ms=300_000, scope="public")}


def _request_state_security() -> RequestStateSecurity:
    """Sealing for the multi-round-trip ``requestState`` (SEP-2322).

    ``requestState`` is the token the server hands a client when a call needs
    input, and which the client echoes back on the retry. Left unsealed it is
    caller-controlled input bearing on whether a destructive operation was
    approved, so the SDK seals it: AES-256-GCM, plus expiry, request binding and
    principal binding. A confirmation answered on one call cannot be lifted onto
    a different call or reused by a different principal, and expires.

    **It is not single-use, unlike the HMAC confirmation token.** The sealed blob
    pins the *question* the server asked, not the answer — that arrives in
    ``inputResponses`` on every round — so re-sending an identical approved call
    inside the TTL executes again. Request and principal binding cap that at
    repeating the same delete of the same resource as the same caller, which then
    finds it already gone. A ledger cannot be added here: the only per-mint-unique
    value is the *sealed* outer string, and the SDK's ``RequestStateBoundary``
    unseals it before any of our code runs, while the inner plaintext is identical
    across two independent asks for the same delete — keying on it would reject a
    legitimate re-approval after a failed delete. Fixing this belongs in SEP-2322.

    **Two key regimes, chosen by whether the operator supplied one.**

    ``ZSCALER_MCP_REQUEST_STATE_KEYS`` set → ``RequestStateSecurity(keys=[...])``.
    The first key seals; every key unseals, which is what makes zero-downtime
    rotation possible: roll ``[old, new]``, then ``[new, old]``, then ``[new]``
    after at least one TTL. **This is required for multi-replica HTTP write
    deployments** — see below for why nothing else works.

    Unset → ``ephemeral()``: a key generated at startup, never persisted, so state
    minted by one process is unintelligible to another. Correct for stdio and
    single-instance HTTP. Two consequences:

    * A restart invalidates in-flight confirmations. The client is told the state
      is invalid and asks again — the right outcome, since nobody approved
      anything in the new process.
    * Behind a load balancer, a retry landing on another replica will not decrypt.

    **Sticky sessions do NOT rescue the second case on ``2026-07-28``.** It is
    tempting to assume they do, because the server does still issue an
    ``Mcp-Session-Id`` — but only to *handshake-era* clients. The SDK routes a
    modern request to ``handle_modern_request`` **before** any session handling
    (``streamable_http_manager._handle_request``), and that handler never sets a
    session id at all: a ``2026-07-28`` request is a self-contained POST. There is
    therefore no MCP session for a load balancer to pin on, and any affinity would
    have to come from infrastructure-level cookie or source-IP stickiness, which
    is not a protocol guarantee. A shared key ring is the only mechanism that
    actually works, which is why the env var exists despite the general rule
    against adding configuration for native protocol features: whether a
    deployment runs one replica or many is a fact only the operator knows, and it
    genuinely changes which configuration is correct.

    The default ``bind_principal`` is kept. It binds state to the authenticated
    caller in **every** HTTP auth mode: ``jwt`` and ``oidc`` from verified token
    claims, ``zscaler`` from the OneAPI client id, and ``api-key`` from a
    domain-separated fingerprint of the key (see
    :meth:`zscaler_mcp.security.auth.AuthProvider.principal`). With auth disabled
    there is no principal to bind, which is the honest representation of an
    unauthenticated deployment.
    """
    keys = _request_state_keys()
    if not keys:
        return RequestStateSecurity.ephemeral()
    try:
        policy = RequestStateSecurity(keys=keys)
    except ValueError as exc:
        # The SDK enforces >=32 bytes of randomness per key. Re-raise naming OUR
        # env var and the generation command, because the SDK's message says
        # "request-state keys" and the operator set ZSCALER_MCP_REQUEST_STATE_KEYS.
        raise ValueError(
            f"ZSCALER_MCP_REQUEST_STATE_KEYS is invalid: {exc} "
            "Generate one per key with: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        ) from exc
    logger.info(
        "Request-state protection: shared key ring (%d key(s); the first seals, "
        "all unseal). Confirmations survive a restart and any replica can "
        "validate a retry.",
        len(keys),
    )
    return policy


def _request_state_keys() -> list[str]:
    """Parse ``ZSCALER_MCP_REQUEST_STATE_KEYS`` into an ordered key ring.

    Accepts a JSON array (``'["k1","k2"]'``) or a comma-separated list. Order is
    significant and preserved: the SDK seals with the first and unseals with any.
    """
    raw = os.getenv("ZSCALER_MCP_REQUEST_STATE_KEYS", "").strip()
    if not raw:
        return []
    keys: list[str] = []
    if raw.startswith("{"):
        # A JSON object does not start with "[", so without this it would fall to
        # the comma-split branch and become one literal "key" — the silent
        # misconfiguration this variable exists to prevent.
        raise ValueError(
            "ZSCALER_MCP_REQUEST_STATE_KEYS must be a JSON array of strings or a "
            "comma-separated list, not a JSON object."
        )
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "ZSCALER_MCP_REQUEST_STATE_KEYS looks like JSON but does not parse "
                f"({exc}). Use a JSON array of strings, or a comma-separated list."
            ) from exc
        if not isinstance(parsed, list) or not all(isinstance(k, str) for k in parsed):
            raise ValueError("ZSCALER_MCP_REQUEST_STATE_KEYS must be a JSON array of strings.")
        keys = [k.strip() for k in parsed]
    else:
        keys = [k.strip() for k in raw.split(",")]
    keys = [k for k in keys if k]
    if not keys:
        raise ValueError("ZSCALER_MCP_REQUEST_STATE_KEYS was set but contained no usable key.")
    return keys


def _log_sanitization_posture() -> None:
    """State whether output sanitization is active.

    On by default and therefore easy to leave unstated — but it is the layer that
    strips prompt-injection payloads out of admin-editable Zscaler fields, so an
    operator who turned it off for diagnostics should see that in the startup log
    rather than having to remember. Announced on every transport, because it wraps
    tool results rather than the HTTP stack.
    """
    from zscaler_mcp.security.sanitize import is_sanitization_enabled

    if is_sanitization_enabled():
        logger.info("Output sanitization active (BiDi / zero-width / HTML / code-fence)")
        return

    # One line, not the full multi-line banner: this is a setting the operator
    # chose, and a wall of text on every restart trains people to skim the log.
    logger.warning(
        "Output sanitization is DISABLED "
        "(ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION) — tool results reach the agent "
        "with invisible Unicode, HTML and forged code-fence markers intact."
    )


def _warn_if_scaled_writes_on_ephemeral_key(
    *, transport: str, enable_write: bool, keys: list[str]
) -> None:
    """Warn when write confirmations cannot survive a second replica.

    Deliberately loud: this is the configuration where a delete confirmation
    silently becomes unreliable, and the failure looks like a flaky client rather
    than a misconfiguration.
    """
    if keys or enable_write is False or transport == "stdio":
        return
    logger.warning(
        "Write tools are enabled on an HTTP transport with a per-process "
        "request-state key. Confirmations are valid ONLY on the replica that "
        "issued them and do not survive a restart. This is safe on a single "
        "instance; if you run more than one, set ZSCALER_MCP_REQUEST_STATE_KEYS "
        "to a shared key ring or confirmations will intermittently fail."
    )


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
    oidc_auth: dict | None = None,
) -> MCPServer:
    """Discover tools, apply the filter selection, and wire up the MCP server.

    The filter arguments mirror v1's knobs (toolsets / entitlement / write
    allowlist / disabled patterns) and are resolved once here via the registry
    query. Each selected spec is bridged onto an MCP ``Tool`` that
    carries the flat input schema, the curated output schema, and the security wrap.

    Args:
        disable_entitlement_filter: When True, skip the OneAPI product
            entitlement downscope (env opt-out: ``ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER``).
        oidc_auth: Constructor kwargs from
            :func:`~zscaler_mcp.security.auth.resolve_oidc_auth` — an
            ``AuthSettings`` naming the external IdP plus a token verifier. Given
            these, the SDK publishes protected-resource metadata (RFC 9728) and
            enforces bearer auth itself, so the ASGI ``AuthMiddleware`` path is
            skipped for this server. ``None`` for every other auth mode.
    """
    discover_tools()

    _warn_unknown_toolsets(enabled_toolsets, "--toolsets")
    _warn_unknown_toolsets(disabled_toolsets, "--disabled-toolsets")

    # Writes need BOTH knobs: the switch grants nothing on its own, and an
    # absent allowlist means zero write tools rather than all of them. Enforced
    # here, at the registration boundary, so the CLI, tests and embedders all
    # fail closed instead of trusting each caller to combine the flags safely.
    write_allowlist = list(write_allowlist) if write_allowlist is not None else None
    if enable_write and not write_allowlist:
        logger.warning(
            "Write tools are enabled but no allowlist was given — registering 0 write "
            "tools. Name what you want to permit: --write-tools 'zpa_create_*,zia_update_*' "
            "(env: ZSCALER_MCP_WRITE_TOOLS)."
        )
        enable_write = False
    elif write_allowlist and not enable_write:
        logger.warning(
            "A write-tool allowlist was given (%d pattern(s)) but write tools are "
            "disabled — registering 0 write tools. Add --enable-write-tools "
            "(env: ZSCALER_MCP_WRITE_ENABLED=true) to turn them on.",
            len(write_allowlist),
        )

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

    # Tools are built first and handed to the constructor: ``MCPServer.add_tool``
    # takes a *function* and builds the Tool itself, which would discard the
    # bridge's flattened signature and derived schemas. The ``tools=`` argument is
    # the path that accepts preconstructed tools.
    server = MCPServer(
        "zscaler-mcp",
        # Not derived from the package: omitting it reports an empty string as our
        # version, on both the legacy `initialize` result and the `2026-07-28`
        # `_meta` serverInfo, which is what a client displays.
        version=__version__,
        # Presentation metadata, surfaced on `server/discover` and the legacy
        # `initialize` result. Without it a connected client shows the bare
        # program name and nothing else — while the SAME product already
        # publishes a title, description and icon to the MCP registry
        # (`server.json`) and the Claude Desktop directory
        # (`integrations/anthropic/manifest.json`). These constants deliberately
        # mirror those files so the server presents identically whether a user
        # is browsing a directory or already connected. Purely display data: no
        # behaviour, no capability, nothing a client may act on.
        title=SERVER_TITLE,
        description=SERVER_DESCRIPTION,
        website_url=SERVER_WEBSITE_URL,
        icons=[Icon(src=SERVER_ICON_URL, mimeType="image/png", sizes=["512x512"])],
        tools=[build_function_tool(spec) for spec in selected],
        # SEP-2549. The inventory is fixed once registration finishes — filters
        # are applied here at startup, never at runtime — so a client may cache
        # `tools/list` for the life of the connection instead of re-fetching a
        # listing of several hundred tools. `public` scope is honest for the same
        # reason: the listing depends on this server's configuration, not on the
        # caller, so a shared cache cannot leak one caller's view to another.
        cache_hints=_TOOL_LIST_CACHE_HINTS,
        # SEP-2322 state protection. Seals the multi-round-trip `requestState` with
        # AES-256-GCM plus expiry, request binding and principal binding, so a
        # confirmation answered on one round cannot be lifted onto a different
        # call or a different principal. It is not single-use; see
        # `_request_state_security`.
        request_state_security=_request_state_security(),
        **(oidc_auth or {}),
    )

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

    _install_logging_set_level(server)

    return server


def _install_logging_set_level(server: MCPServer) -> None:
    """Let a pre-``2026-07-28`` client set this server's log verbosity.

    ``logging/setLevel`` is part of the ``2025-06-18`` and ``2025-11-25`` base
    spec, and a client that asks for it and gets ``-32601 Method not found`` has no
    way to turn on diagnostics against a server it did not launch — the situation
    for every HTTP deployment. ``MCPServer`` registers no handler, so this adds one
    and is what keeps the ``logging-set-level`` conformance scenario green.

    **It is deliberately a no-op on ``2026-07-28``.** SEP-2577 deprecated the
    logging capability, and that revision drops the method from its surface
    entirely: the SDK's runner rejects it during request validation, before handler
    lookup, so this handler is unreachable there no matter what we register.
    Nothing to work around — the method is gone by design, and clients on that
    revision are expected to use OpenTelemetry, which the SDK emits natively.
    Keeping the handler costs nothing and serves every older client.

    The level applies to the ``zscaler_mcp`` logger tree only. Raising the root
    logger would drag in ``httpx``, ``uvicorn`` and the Zscaler SDK's own request
    logging, which at ``debug`` prints credential-bearing headers — a client
    asking for verbose MCP logs is not asking for that.
    """
    import logging as _logging

    from mcp.types import EmptyResult, SetLevelRequestParams

    #: MCP's eight severities collapsed onto Python's five. ``notice`` reads as
    #: informational, and everything above ``critical`` has no louder Python
    #: equivalent, so the three top levels all pin to ``CRITICAL``.
    levels = {
        "debug": _logging.DEBUG,
        "info": _logging.INFO,
        "notice": _logging.INFO,
        "warning": _logging.WARNING,
        "error": _logging.ERROR,
        "critical": _logging.CRITICAL,
        "alert": _logging.CRITICAL,
        "emergency": _logging.CRITICAL,
    }

    async def set_level(ctx, params: SetLevelRequestParams) -> EmptyResult:
        level = levels.get(params.level, _logging.INFO)
        _logging.getLogger("zscaler_mcp").setLevel(level)
        logger.info("Log level set to %s by client request", params.level)
        return EmptyResult()

    server._lowlevel_server.add_request_handler(
        "logging/setLevel", SetLevelRequestParams, set_level
    )


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
    server: MCPServer,
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

    # ``MCPServer`` exposes one factory per transport instead of FastMCP's single
    # ``http_app(transport=...)``. Both still return a plain Starlette app, so the
    # middleware stack below is unchanged. ``host=`` is passed through because the
    # SDK derives its own transport-security defaults from it; our stricter
    # host-header allowlist is applied separately in step 3.
    if transport == "streamable-http":
        # Sessions stay ON for the clients that still use a handshake, because that
        # session is the only way to *push* a delete confirmation to them. A
        # pre-2026-07-28 client declares `elicitation` once during `initialize` and
        # the session is what remembers it; run sessionless and the server sees no
        # capabilities, cannot ask, and falls back to the HMAC token — which the
        # agent can redeem in the same turn, so no human necessarily approves the
        # delete. That is a safety regression, and it is what a real Claude session
        # exhibited.
        #
        # This costs 2026-07-28 clients nothing. The SDK routes any request whose
        # `mcp-protocol-version` is not a handshake revision to its modern entry
        # point *before* the session branch, so those callers are served sessionless
        # either way and answer with `InputRequiredResult`. Verified across all four
        # {legacy, 2026-07-28} x {session, sessionless} combinations; only the
        # legacy/sessionless cell loses the human, so that is the cell to avoid.
        #
        # The trade-off accepted here: handshake clients get an `Mcp-Session-Id`
        # back, so multi-replica deployments need sticky routing for them. A human
        # approving their own deletes is worth more than dropping affinity.
        app = server.streamable_http_app(
            streamable_http_path=DEFAULT_MCP_PATH,
            host=host,
            stateless_http=False,
        )
    else:
        app = server.sse_app(sse_path=DEFAULT_MCP_PATH, host=host)

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
        "Starting %s transport on %s://%s:%d (path=%s, tls=%s, sessions=%s)",
        transport,
        scheme,
        host,
        port,
        DEFAULT_MCP_PATH,
        "on" if tls_kwargs else "off",
        # Both transports issue a session to handshake clients; only the revision
        # decides otherwise, per connection. Reporting "off" here was left over from
        # the sessionless experiment and contradicted the running configuration.
        "on (handshake clients)",
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
            "Master switch for write operations (create/update/delete). Off by default "
            "for safety. Has no effect on its own — --write-tools must also name the "
            "permitted patterns (env: ZSCALER_MCP_WRITE_ENABLED)."
        ),
    )
    p.add_argument(
        "--write-tools",
        default=os.getenv("ZSCALER_MCP_WRITE_TOOLS", ""),
        help=(
            "Allowlist of write tools to permit (fnmatch patterns, e.g. 'zpa_create_*'). "
            "Required alongside --enable-write-tools; neither flag enables writes alone "
            "(env: ZSCALER_MCP_WRITE_TOOLS)."
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

    # Optionally hydrate credentials from a cloud secret store BEFORE anything
    # reads them: AWS Secrets Manager (ZSCALER_SECRET_NAME) or GCP Secret
    # Manager (ZSCALER_MCP_GCP_SECRET_MANAGER=true). No-op otherwise; each
    # provider's SDK is imported only when its loader is enabled.
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

    # --enable-write-tools is the master switch and --write-tools names the
    # permitted patterns; both are required. build_server enforces the pairing.
    write_allowlist = _parse_csv(args.write_tools)
    write_enabled = args.enable_write_tools

    # OIDC mode → protected-resource metadata + a token verifier on the
    # constructor, which the SDK wires itself. Every other mode returns None
    # (handled by AuthMiddleware at the ASGI layer). stdio never authenticates.
    oidc_auth = None
    if args.transport != "stdio":
        oidc_auth = resolve_oidc_auth()

    server = build_server(
        enabled_services=enabled_services,
        disabled_services=disabled_services,
        enabled_toolsets=_resolve_toolsets(args.toolsets),
        disabled_toolsets=_parse_csv(args.disabled_toolsets),
        enable_write=write_enabled,
        write_allowlist=write_allowlist,
        disabled_patterns=_parse_csv(args.disabled_tools),
        disable_entitlement_filter=args.no_entitlement_filter,
        oidc_auth=oidc_auth,
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
    _log_sanitization_posture()
    _warn_if_scaled_writes_on_ephemeral_key(
        transport=args.transport,
        enable_write=write_enabled,
        keys=_request_state_keys(),
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
