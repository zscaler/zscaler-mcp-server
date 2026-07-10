"""Tests for transport hardening + source-IP ACL (security/hardening.py)."""

from __future__ import annotations

import pytest

from zscaler_mcp.security import hardening as h


# ---------------------------------------------------------------------------
# IP matching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "client_ip,allowed,expected",
    [
        ("10.0.0.5", ["10.0.0.5"], True),
        ("10.0.0.5", ["10.0.0.0/24"], True),
        ("10.0.1.5", ["10.0.0.0/24"], False),
        ("10.0.0.5", ["*"], True),
        ("10.0.0.5", ["0.0.0.0/0"], True),
        ("10.0.0.5", ["192.168.1.1"], False),
        ("not-an-ip", ["10.0.0.0/24"], False),
    ],
)
def test_ip_matches(client_ip, allowed, expected):
    assert h._ip_matches(client_ip, allowed) is expected


def test_get_allowed_source_ips(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_ALLOWED_SOURCE_IPS", raising=False)
    assert h.get_allowed_source_ips() is None
    monkeypatch.setenv("ZSCALER_MCP_ALLOWED_SOURCE_IPS", "10.0.0.1, 192.168.0.0/16")
    assert h.get_allowed_source_ips() == ["10.0.0.1", "192.168.0.0/16"]


# ---------------------------------------------------------------------------
# ASGI middleware behavior (driven directly with synthetic scopes)
# ---------------------------------------------------------------------------


async def _drive(mw, scope):
    """Drive an ASGI middleware once, capturing the response start + body."""
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    forwarded = {"called": False}

    async def app(s, r, sd):
        forwarded["called"] = True
        await sd({"type": "http.response.start", "status": 200, "headers": []})
        await sd({"type": "http.response.body", "body": b"OK"})

    mw.app = app
    await mw(scope, receive, send)
    return forwarded["called"], sent


@pytest.mark.asyncio
async def test_source_ip_blocks_disallowed():
    mw = h.SourceIPMiddleware(None, ["10.0.0.0/24"])
    scope = {"type": "http", "path": "/mcp", "client": ("8.8.8.8", 1234), "headers": []}
    called, sent = await _drive(mw, scope)
    assert called is False
    assert sent[0]["status"] == 403


@pytest.mark.asyncio
async def test_source_ip_allows_allowed():
    mw = h.SourceIPMiddleware(None, ["10.0.0.0/24"])
    scope = {"type": "http", "path": "/mcp", "client": ("10.0.0.9", 1234), "headers": []}
    called, _ = await _drive(mw, scope)
    assert called is True


@pytest.mark.asyncio
async def test_source_ip_health_exempt():
    mw = h.SourceIPMiddleware(None, ["10.0.0.0/24"])
    scope = {"type": "http", "path": "/health", "client": ("8.8.8.8", 1234), "headers": []}
    called, _ = await _drive(mw, scope)
    assert called is True


@pytest.mark.asyncio
async def test_health_check_short_circuits():
    mw = h.HealthCheckMiddleware(None, path="/health")
    scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
    called, sent = await _drive(mw, scope)
    assert called is False
    assert sent[0]["status"] == 200
    assert sent[1]["body"] == b'{"status":"ok"}'


@pytest.mark.asyncio
async def test_strip_trailing_slash():
    mw = h.StripTrailingSlashMiddleware(None)
    scope = {"type": "http", "path": "/mcp/", "headers": []}
    await _drive(mw, scope)
    assert scope["path"] == "/mcp"


@pytest.mark.asyncio
async def test_normalize_content_type():
    mw = h.NormalizeContentTypeMiddleware(None)
    scope = {
        "type": "http",
        "path": "/mcp",
        "headers": [(b"content-type", b"application/json-rpc")],
    }
    await _drive(mw, scope)
    assert (b"content-type", b"application/json") in scope["headers"]


@pytest.mark.asyncio
async def test_reject_non_sse_get_returns_405():
    mw = h.RejectNonSSEGetMiddleware(None, mcp_path="/mcp")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/mcp",
        "headers": [(b"accept", b"application/json")],
    }
    called, sent = await _drive(mw, scope)
    assert called is False
    assert sent[0]["status"] == 405


@pytest.mark.asyncio
async def test_reject_non_sse_get_passes_sse_accept():
    mw = h.RejectNonSSEGetMiddleware(None, mcp_path="/mcp")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/mcp",
        "headers": [(b"accept", b"text/event-stream")],
    }
    called, _ = await _drive(mw, scope)
    assert called is True


def test_apply_transport_hardening_noop_for_stdio():
    sentinel = object()
    assert h.apply_transport_hardening(sentinel, "stdio") is sentinel
