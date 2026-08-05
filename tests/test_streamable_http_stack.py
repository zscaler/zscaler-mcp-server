"""Regression tests for the real Streamable HTTP stack.

Everything else in the suite exercises tools in-process or through the in-memory
`Client`. This file drives the actual ASGI application returned by
`MCPServer.streamable_http_app()` — with our auth and hardening middleware
wrapped around it — by speaking the ASGI protocol directly.

**Why this file exists.** The middleware chain was previously verified once, by
hand, and the result written into a planning document. That proves nothing about
tomorrow: an SDK upgrade can reorder middleware, change how the transport routes
protocol revisions, or alter header handling, and the rest of the suite would stay
green because it never touches the wire. This is the integration boundary most
likely to break silently on `uv sync`.

**No new dependency.** `httpx`/`ASGITransport` would be the conventional way to do
this, but neither is in the dependency tree and adding one to test six assertions
is a poor trade. The ASGI protocol is three callables; driving it directly costs a
~40-line harness and keeps the install surface unchanged.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any

import anyio
import pytest

from zscaler_mcp.server import DEFAULT_MCP_PATH, build_server

MODERN = "2026-07-28"
HANDSHAKE = "2025-11-25"


# ---------------------------------------------------------------------------
# Minimal ASGI harness
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def running(app: Any):
    """Run `app`'s lifespan, yielding a callable that performs one request.

    The Streamable HTTP app needs its lifespan started — that is where the
    session manager's task group is created — so a test that skips it either
    hangs or raises "Task group is not initialized".
    """
    startup = anyio.Event()
    shutdown = anyio.Event()
    lifespan_state: dict[str, Any] = {}

    async def lifespan_receive():
        if not startup.is_set():
            return {"type": "lifespan.startup"}
        await shutdown.wait()
        return {"type": "lifespan.shutdown"}

    async def lifespan_send(message):
        if message["type"] in ("lifespan.startup.complete", "lifespan.startup.failed"):
            startup.set()

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            app,
            {"type": "lifespan", "asgi": {"version": "3.0"}, "state": lifespan_state},
            lifespan_receive,
            lifespan_send,
        )
        with anyio.fail_after(10):
            await startup.wait()

        async def request(
            method: str = "POST",
            path: str = DEFAULT_MCP_PATH,
            headers: list[tuple[bytes, bytes]] | None = None,
            body: dict | None = None,
        ):
            payload = json.dumps(body).encode() if body is not None else b""
            scope = {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": headers or [],
                "client": ("127.0.0.1", 51234),
                "server": ("127.0.0.1", 8000),
                "state": lifespan_state,
            }
            sent: list[dict] = []
            delivered = False
            responded = anyio.Event()

            done = anyio.Event()

            async def receive():
                nonlocal delivered
                if delivered:
                    # Block rather than returning `http.disconnect`. The SSE path
                    # polls receive() to notice a client going away; answering
                    # "disconnected" makes it abandon the response, which looks
                    # exactly like a hang from the test's side.
                    await done.wait()
                    return {"type": "http.disconnect"}
                delivered = True
                return {"type": "http.request", "body": payload, "more_body": False}

            async def send(message):
                sent.append(message)
                if message["type"] == "http.response.start":
                    responded.set()

            with anyio.fail_after(10):
                await app(scope, receive, send)
                # In SSE mode the modern handler runs the JSON-RPC handler as a
                # SIBLING task and returns from the ASGI callable first, so the
                # response has not necessarily been sent yet. Wait for it rather
                # than forcing `json_response=True`, which would test a
                # configuration we do not ship.
                if not responded.is_set():
                    await responded.wait()
                # let the body chunks that follow the start message land
                await anyio.sleep(0.05)
            done.set()

            start = next((m for m in sent if m["type"] == "http.response.start"), {})
            chunks = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
            return {
                "status": start.get("status"),
                "headers": {k.decode().lower(): v.decode() for k, v in start.get("headers", [])},
                "body": chunks.decode(errors="replace"),
            }

        yield request
        shutdown.set()
        tg.cancel_scope.cancel()


def _jsonrpc_headers(
    protocol_version: str,
    *,
    method: str | None = None,
    host: bytes = b"127.0.0.1:8000",
    extra=None,
) -> list[tuple[bytes, bytes]]:
    """Headers for one JSON-RPC POST.

    `mcp-method` is SEP-2243 routing metadata: it lets a gateway route or
    rate-limit without parsing the body, and the server rejects it (-32020) when
    it disagrees with the body's method.
    """
    headers = [
        (b"content-type", b"application/json"),
        (b"accept", b"application/json, text/event-stream"),
        (b"mcp-protocol-version", protocol_version.encode()),
        (b"host", host),
    ]
    if method:
        headers.append((b"mcp-method", method.encode()))
    headers.extend(extra or [])
    return headers


def _app(**kwargs):
    """The HTTP app as `main()` builds it, hardening included."""
    from zscaler_mcp.security import apply_transport_hardening

    server = build_server(**kwargs)
    app = server.streamable_http_app(streamable_http_path=DEFAULT_MCP_PATH, host="127.0.0.1")
    return apply_transport_hardening(app, transport="streamable-http", mcp_path=DEFAULT_MCP_PATH)


def _modern(method: str, params: dict | None = None, *, elicitation: bool = False) -> dict:
    """A 2026-07-28 JSON-RPC request.

    The revision replaced the `initialize` handshake with a per-request envelope:
    every call must carry its protocol version and client capabilities in
    `params._meta`, or the server answers -32602. That is what makes each request
    self-contained — and what removes the need for a session.
    """
    capabilities: dict[str, Any] = {"elicitation": {}} if elicitation else {}
    body_params = dict(params or {})
    body_params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": MODERN,
        "io.modelcontextprotocol/clientCapabilities": capabilities,
    }
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": body_params}


def _body(result: dict) -> dict:
    """Parse a JSON or SSE response body into the JSON-RPC object."""
    text = result["body"]
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[len("data:") :].strip())
    return json.loads(text)


# ---------------------------------------------------------------------------
# The modern (2026-07-28) path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_modern_tools_list_needs_no_handshake_and_no_session():
    """A 2026-07-28 request is a self-contained POST.

    No `initialize`, and critically no `Mcp-Session-Id` — which is exactly why a
    shared request-state key ring, not session affinity, is what makes scaled
    deployments work.
    """
    async with running(_app()) as request:
        result = await request(
            headers=_jsonrpc_headers(MODERN, method="tools/list"),
            body=_modern("tools/list"),
        )
    assert result["status"] == 200, result["body"]
    assert "mcp-session-id" not in result["headers"], (
        "the modern path must not issue a session id — affinity cannot be relied on"
    )
    payload = _body(result)
    assert payload["result"]["tools"], "no tools returned"


@pytest.mark.anyio
async def test_modern_tools_list_carries_the_cache_hint_on_the_wire():
    """SEP-2549: asserting the hint reaches the client, not just the constructor."""
    async with running(_app()) as request:
        result = await request(
            headers=_jsonrpc_headers(MODERN, method="tools/list"),
            body=_modern("tools/list"),
        )
    payload = _body(result)["result"]
    # SEP-2549 puts these at the TOP LEVEL of the result, not under `_meta`.
    assert payload.get("cacheScope") == "public", payload.keys()
    assert payload.get("ttlMs") == 300_000, (
        f"expected ttlMs=300000 on the wire, got {payload.get('ttlMs')!r}"
    )


@pytest.mark.anyio
async def test_a_handshake_era_client_still_gets_a_session():
    """Both eras share one app; the older one must keep its session."""
    async with running(_app()) as request:
        result = await request(
            headers=_jsonrpc_headers(HANDSHAKE),
            body={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": HANDSHAKE,
                    "capabilities": {},
                    "clientInfo": {"name": "regression", "version": "1"},
                },
            },
        )
    assert result["status"] == 200, result["body"]
    assert "mcp-session-id" in result["headers"], (
        "handshake-era clients still need a session — it carries the elicitation prompt"
    )


# ---------------------------------------------------------------------------
# Our hardening middleware, on the real stack
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_bypasses_the_whole_chain():
    async with running(_app()) as request:
        result = await request(method="GET", path="/health")
    assert result["status"] == 200


@pytest.mark.anyio
async def test_a_forged_host_header_is_rejected(monkeypatch):
    """DNS-rebinding protection. Opt-in, and load-bearing when enabled."""
    monkeypatch.setenv("ZSCALER_MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*")
    async with running(_app()) as request:
        result = await request(
            headers=_jsonrpc_headers(MODERN, method="tools/list", host=b"evil.example"),
            body=_modern("tools/list"),
        )
    assert result["status"] == 421, result["body"]


@pytest.mark.anyio
async def test_a_get_without_sse_accept_is_refused():
    async with running(_app()) as request:
        result = await request(
            method="GET",
            headers=[(b"accept", b"application/json"), (b"host", b"127.0.0.1:8000")],
        )
    assert result["status"] == 405


@pytest.mark.anyio
async def test_trailing_slash_and_odd_content_type_are_normalised():
    """Both are real client behaviours that would otherwise 404/415."""
    async with running(_app()) as request:
        slashed = await request(
            path=DEFAULT_MCP_PATH + "/",
            headers=_jsonrpc_headers(MODERN, method="tools/list"),
            body=_modern("tools/list"),
        )
        odd_type = await request(
            headers=[
                (b"content-type", b"application/json-rpc"),
                (b"accept", b"application/json, text/event-stream"),
                (b"mcp-protocol-version", MODERN.encode()),
                (b"mcp-method", b"tools/list"),
                (b"host", b"127.0.0.1:8000"),
            ],
            body=_modern("tools/list"),
        )
    assert slashed["status"] == 200, slashed["body"]
    assert odd_type["status"] == 200, odd_type["body"]


# ---------------------------------------------------------------------------
# Auth on the wire
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_auth_rejects_an_unauthenticated_call_and_admits_a_valid_one(monkeypatch):
    """The auth middleware is in the real chain, not just unit-tested in isolation."""
    from zscaler_mcp.security import apply_auth_middleware

    monkeypatch.setenv("ZSCALER_MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_MODE", "api-key")
    monkeypatch.setenv("ZSCALER_MCP_AUTH_API_KEY", "regression-key")

    from zscaler_mcp.security import apply_transport_hardening

    server = build_server()
    app = server.streamable_http_app(streamable_http_path=DEFAULT_MCP_PATH, host="127.0.0.1")
    app = apply_auth_middleware(app, transport="streamable-http")
    app = apply_transport_hardening(app, transport="streamable-http", mcp_path=DEFAULT_MCP_PATH)

    body = _modern("tools/list")
    async with running(app) as request:
        anonymous = await request(headers=_jsonrpc_headers(MODERN, method="tools/list"), body=body)
        authorized = await request(
            headers=_jsonrpc_headers(
                MODERN,
                method="tools/list",
                extra=[(b"authorization", b"Bearer regression-key")],
            ),
            body=body,
        )
    assert anonymous["status"] == 401, anonymous["body"]
    assert authorized["status"] == 200, authorized["body"]


@pytest.mark.anyio
async def test_server_identity_is_advertised_on_discover():
    """Presentation metadata must reach the client, not just the constructor.

    It travels in `_meta["io.modelcontextprotocol/serverInfo"]` on the result —
    not at the result root — so asserting it on the object alone would not prove
    a client ever sees it.
    """
    async with running(_app()) as request:
        result = await request(
            headers=_jsonrpc_headers(MODERN, method="server/discover"),
            body=_modern("server/discover"),
        )
    assert result["status"] == 200, result["body"]
    info = _body(result)["result"]["_meta"]["io.modelcontextprotocol/serverInfo"]
    assert info["name"] == "zscaler-mcp"
    assert info["title"] == "Zscaler MCP Server"
    assert info["version"]
    assert "read-only" in info["description"].lower()
    assert info["websiteUrl"].startswith("https://github.com/zscaler/")
    assert info["icons"][0]["src"].endswith("/assets/icon.png")
