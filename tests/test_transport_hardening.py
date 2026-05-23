"""
Tests for ``zscaler_mcp.auth`` HTTP transport hardening middlewares.

Covers:

* :class:`StripTrailingSlashMiddleware` — path / raw_path normalisation.
* :class:`NormalizeContentTypeMiddleware` — ``application/json-rpc``
  → ``application/json`` rewrite, parameter preservation, casing.
* :func:`apply_transport_hardening` — transport gating (no-op for stdio,
  composes both middlewares for HTTP transports) and outermost ordering
  (path normalisation must run before content-type normalisation).

These middlewares are pure pre-processors — they mutate ``scope`` and
forward the request unchanged. Every test asserts the wrapped app is
called exactly once and observes the mutated scope.
"""

import asyncio
import unittest
from unittest.mock import MagicMock

from zscaler_mcp.auth import (
    HealthCheckMiddleware,
    NormalizeContentTypeMiddleware,
    RejectNonSSEGetMiddleware,
    StripTrailingSlashMiddleware,
    apply_transport_hardening,
)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_recording_app():
    """Async ASGI app that records every scope it receives."""
    calls = []

    async def app(scope, receive, send):
        calls.append(scope)

    app._calls = calls
    return app


# ============================================================================
# StripTrailingSlashMiddleware
# ============================================================================


class TestStripTrailingSlashMiddleware(unittest.TestCase):
    def test_non_http_scope_passes_through_unchanged(self):
        app = _make_recording_app()
        middleware = StripTrailingSlashMiddleware(app)

        scope = {"type": "lifespan"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 1)
        # Scope must not have grown a path / raw_path.
        self.assertNotIn("path", app._calls[0])

    def test_path_without_trailing_slash_unchanged(self):
        app = _make_recording_app()
        middleware = StripTrailingSlashMiddleware(app)

        scope = {"type": "http", "path": "/mcp", "raw_path": b"/mcp"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(app._calls[0]["path"], "/mcp")
        self.assertEqual(app._calls[0]["raw_path"], b"/mcp")

    def test_root_path_left_alone(self):
        """``/`` must NOT be stripped to an empty string."""
        app = _make_recording_app()
        middleware = StripTrailingSlashMiddleware(app)

        scope = {"type": "http", "path": "/", "raw_path": b"/"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(app._calls[0]["path"], "/")
        self.assertEqual(app._calls[0]["raw_path"], b"/")

    def test_trailing_slash_stripped(self):
        app = _make_recording_app()
        middleware = StripTrailingSlashMiddleware(app)

        scope = {"type": "http", "path": "/mcp/", "raw_path": b"/mcp/"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(app._calls[0]["path"], "/mcp")
        self.assertEqual(app._calls[0]["raw_path"], b"/mcp")

    def test_multiple_trailing_slashes_stripped(self):
        app = _make_recording_app()
        middleware = StripTrailingSlashMiddleware(app)

        scope = {"type": "http", "path": "/mcp///", "raw_path": b"/mcp///"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(app._calls[0]["path"], "/mcp")
        self.assertEqual(app._calls[0]["raw_path"], b"/mcp")

    def test_nested_path_trailing_slash_stripped(self):
        app = _make_recording_app()
        middleware = StripTrailingSlashMiddleware(app)

        scope = {"type": "http", "path": "/api/v1/tools/", "raw_path": b"/api/v1/tools/"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(app._calls[0]["path"], "/api/v1/tools")
        self.assertEqual(app._calls[0]["raw_path"], b"/api/v1/tools")

    def test_missing_raw_path_does_not_crash(self):
        """Some ASGI servers omit raw_path; middleware must still mutate path."""
        app = _make_recording_app()
        middleware = StripTrailingSlashMiddleware(app)

        scope = {"type": "http", "path": "/mcp/"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(app._calls[0]["path"], "/mcp")
        self.assertNotIn("raw_path", app._calls[0])


# ============================================================================
# NormalizeContentTypeMiddleware
# ============================================================================


class TestNormalizeContentTypeMiddleware(unittest.TestCase):
    def test_non_http_scope_passes_through_unchanged(self):
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        scope = {"type": "websocket"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 1)
        self.assertNotIn("headers", app._calls[0])

    def test_no_headers_passes_through(self):
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        scope = {"type": "http", "path": "/mcp"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 1)

    def test_compliant_content_type_unchanged(self):
        """Spec-compliant ``application/json`` must not be touched."""
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        original_headers = [(b"content-type", b"application/json")]
        scope = {"type": "http", "headers": list(original_headers)}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        # Headers should be byte-for-byte identical.
        self.assertEqual(app._calls[0]["headers"], original_headers)

    def test_other_content_type_unchanged(self):
        """``text/plain``, ``application/xml`` etc. pass through untouched."""
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        original_headers = [(b"content-type", b"text/plain; charset=utf-8")]
        scope = {"type": "http", "headers": list(original_headers)}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(app._calls[0]["headers"], original_headers)

    def test_json_rpc_content_type_normalised(self):
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        scope = {
            "type": "http",
            "headers": [(b"content-type", b"application/json-rpc")],
        }
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(
            app._calls[0]["headers"],
            [(b"content-type", b"application/json")],
        )

    def test_json_rpc_with_charset_param_preserves_param(self):
        """``application/json-rpc; charset=utf-8`` → ``application/json; charset=utf-8``."""
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        scope = {
            "type": "http",
            "headers": [(b"content-type", b"application/json-rpc; charset=utf-8")],
        }
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(
            app._calls[0]["headers"],
            [(b"content-type", b"application/json; charset=utf-8")],
        )

    def test_uppercase_json_rpc_normalised(self):
        """Match must be case-insensitive (HTTP header values are not enums)."""
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        scope = {
            "type": "http",
            "headers": [(b"content-type", b"Application/JSON-RPC")],
        }
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        # Rewrite emits lowercase canonical form.
        self.assertEqual(
            app._calls[0]["headers"],
            [(b"content-type", b"application/json")],
        )

    def test_unrelated_headers_preserved(self):
        """Every non-Content-Type header survives unchanged."""
        app = _make_recording_app()
        middleware = NormalizeContentTypeMiddleware(app)

        scope = {
            "type": "http",
            "headers": [
                (b"host", b"example.com"),
                (b"content-type", b"application/json-rpc"),
                (b"x-request-id", b"abc-123"),
                (b"authorization", b"Bearer foo"),
            ],
        }
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(
            app._calls[0]["headers"],
            [
                (b"host", b"example.com"),
                (b"content-type", b"application/json"),
                (b"x-request-id", b"abc-123"),
                (b"authorization", b"Bearer foo"),
            ],
        )


# ============================================================================
# RejectNonSSEGetMiddleware
# ============================================================================


def _make_recording_send():
    """Async ``send`` callable that records every ASGI message it sees."""
    messages = []

    async def send(message):
        messages.append(message)

    send._messages = messages
    return send


class TestRejectNonSSEGetMiddleware(unittest.TestCase):
    def test_non_http_scope_passes_through_unchanged(self):
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        scope = {"type": "lifespan"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 1)

    def test_post_is_never_intercepted(self):
        """POST is the only required method on the streamable-http endpoint."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [(b"content-type", b"application/json")],
        }
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 1)

    def test_get_on_other_paths_passes_through(self):
        """Only the configured MCP path is intercepted (don't 405 /health, /sse, etc.)."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        for path in ("/", "/health", "/sse", "/.well-known/oauth-protected-resource"):
            with self.subTest(path=path):
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": path,
                    "headers": [(b"accept", b"application/json")],
                }
                _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 4)

    def test_get_with_sse_accept_passes_through(self):
        """Spec-compliant clients (Accept: text/event-stream) reach FastMCP unchanged."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"accept", b"text/event-stream")],
        }
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 1)
        self.assertEqual(len(send._messages), 0)  # short-circuit didn't fire

    def test_get_with_multi_value_accept_passes_through(self):
        """The Bedrock pattern would still pass IF it set Accept correctly."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"accept", b"application/json, text/event-stream")],
        }
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 1)
        self.assertEqual(len(send._messages), 0)

    def test_get_without_sse_accept_returns_405(self):
        """The Bedrock Harness case — GET /mcp with no SSE Accept → 405."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"accept", b"application/json")],
        }
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 0)  # short-circuited — never reached FastMCP
        self.assertEqual(len(send._messages), 2)
        self.assertEqual(send._messages[0]["type"], "http.response.start")
        self.assertEqual(send._messages[0]["status"], 405)
        # Allow header is mandatory for 405.
        headers = dict(send._messages[0]["headers"])
        self.assertEqual(headers[b"allow"], b"POST")

    def test_get_with_no_accept_header_returns_405(self):
        """Missing Accept entirely is the worst-case spec violation — same 405."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [],
        }
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 0)
        self.assertEqual(send._messages[0]["status"], 405)

    def test_get_with_wildcard_accept_returns_405(self):
        """Accept: */* doesn't explicitly request SSE → 405 (let client retry properly)."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"accept", b"*/*")],
        }
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(send._messages[0]["status"], 405)

    def test_custom_mcp_path(self):
        """Operator-customised streamable_http_path is respected."""
        app = _make_recording_app()
        middleware = RejectNonSSEGetMiddleware(app, mcp_path="/custom-mcp")

        # Default /mcp passes through (not the configured path)
        scope_default = {
            "type": "http",
            "method": "GET",
            "path": "/mcp",
            "headers": [(b"accept", b"application/json")],
        }
        _run_async(middleware(scope_default, MagicMock(), MagicMock()))
        self.assertEqual(len(app._calls), 1)

        # Custom path triggers the 405.
        scope_custom = {
            "type": "http",
            "method": "GET",
            "path": "/custom-mcp",
            "headers": [(b"accept", b"application/json")],
        }
        send = _make_recording_send()
        _run_async(middleware(scope_custom, MagicMock(), send))
        self.assertEqual(send._messages[0]["status"], 405)


# ============================================================================
# HealthCheckMiddleware
# ============================================================================


class TestHealthCheckMiddleware(unittest.TestCase):
    """Cover the LB-probe short-circuit in :class:`HealthCheckMiddleware`.

    The middleware must:

    * return 200 OK with a JSON body for ``GET /health``,
    * return 200 OK with an empty body for ``HEAD /health``,
    * **not** invoke the wrapped app for either case (so probes never
      blow up auth-token caches, audit log lines, or MCP session
      creation),
    * pass every other request through unchanged,
    * honour a custom ``path`` so operators can move it to ``/healthz``,
      ``/readyz``, etc.
    """

    def test_get_health_short_circuits_with_200(self):
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
        }
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 0)
        self.assertEqual(send._messages[0]["type"], "http.response.start")
        self.assertEqual(send._messages[0]["status"], 200)
        body = send._messages[1]["body"]
        self.assertIn(b'"status"', body)
        self.assertIn(b'"ok"', body)

    def test_get_health_sets_no_cache_headers(self):
        """``cache-control: no-store`` keeps stale probes from being cached
        by Cloud Front / ALB / sidecars."""
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app)

        scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        headers = dict(send._messages[0]["headers"])
        self.assertEqual(headers.get(b"content-type"), b"application/json")
        self.assertEqual(headers.get(b"cache-control"), b"no-store")

    def test_head_health_returns_empty_body(self):
        """HEAD must return 200 with no body, per HTTP semantics."""
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app)

        scope = {"type": "http", "method": "HEAD", "path": "/health", "headers": []}
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 0)
        self.assertEqual(send._messages[0]["status"], 200)
        self.assertEqual(send._messages[1]["body"], b"")

    def test_post_health_passes_through(self):
        """Only GET / HEAD are short-circuited — POST /health goes downstream
        in case a downstream app actually defines a POST handler."""
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app)

        scope = {"type": "http", "method": "POST", "path": "/health", "headers": []}
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 1)
        self.assertEqual(len(send._messages), 0)

    def test_non_health_path_passes_through(self):
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app)

        scope = {"type": "http", "method": "GET", "path": "/mcp", "headers": []}
        send = _make_recording_send()
        _run_async(middleware(scope, MagicMock(), send))

        self.assertEqual(len(app._calls), 1)

    def test_websocket_scope_passes_through(self):
        """Non-HTTP scopes (websocket, lifespan) must always pass through."""
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app)

        scope = {"type": "websocket", "path": "/health"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 1)

    def test_lifespan_scope_passes_through(self):
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app)

        scope = {"type": "lifespan"}
        _run_async(middleware(scope, MagicMock(), MagicMock()))

        self.assertEqual(len(app._calls), 1)

    def test_custom_path(self):
        """Operators behind a kube-native convention use ``/healthz``."""
        app = _make_recording_app()
        middleware = HealthCheckMiddleware(app, path="/healthz")

        scope_default = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
        }
        send = _make_recording_send()
        _run_async(middleware(scope_default, MagicMock(), send))
        self.assertEqual(len(app._calls), 1)
        self.assertEqual(len(send._messages), 0)

        scope_custom = {
            "type": "http",
            "method": "GET",
            "path": "/healthz",
            "headers": [],
        }
        send = _make_recording_send()
        _run_async(middleware(scope_custom, MagicMock(), send))
        self.assertEqual(send._messages[0]["status"], 200)


# ============================================================================
# apply_transport_hardening factory
# ============================================================================


class TestApplyTransportHardening(unittest.TestCase):
    def test_stdio_returns_app_unchanged(self):
        """stdio transport never goes through HTTP — middleware would be dead weight."""
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "stdio")
        self.assertIs(wrapped, app)

    def test_streamable_http_returns_wrapped_app(self):
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "streamable-http")
        self.assertIsNot(wrapped, app)
        self.assertIsInstance(wrapped, HealthCheckMiddleware)

    def test_sse_returns_wrapped_app(self):
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "sse")
        self.assertIsNot(wrapped, app)
        self.assertIsInstance(wrapped, HealthCheckMiddleware)

    def test_streamable_http_includes_get_405_layer(self):
        """The GET→405 middleware must be in the chain for streamable-http."""
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "streamable-http")
        # Walk: HealthCheck → StripTrailingSlash → NormalizeContentType →
        #       RejectNonSSEGet → app
        self.assertIsInstance(wrapped, HealthCheckMiddleware)
        self.assertIsInstance(wrapped.app, StripTrailingSlashMiddleware)
        self.assertIsInstance(wrapped.app.app, NormalizeContentTypeMiddleware)
        self.assertIsInstance(wrapped.app.app.app, RejectNonSSEGetMiddleware)
        self.assertIs(wrapped.app.app.app.app, app)

    def test_sse_does_not_include_get_405_layer(self):
        """SSE transport REQUIRES GET to work on /sse — we must not 405 it."""
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "sse")
        # Walk: HealthCheck → StripTrailingSlash → NormalizeContentType → app
        self.assertIsInstance(wrapped, HealthCheckMiddleware)
        self.assertIsInstance(wrapped.app, StripTrailingSlashMiddleware)
        self.assertIsInstance(wrapped.app.app, NormalizeContentTypeMiddleware)
        self.assertIs(wrapped.app.app.app, app)  # no GET-405 layer

    def test_outermost_layer_is_health_check(self):
        """Health probes MUST bypass every other middleware.

        ``HealthCheckMiddleware`` has to be the outermost layer so LB
        probes against ``/health`` never reach auth, source-IP ACL,
        the GET→405 hardening, or FastMCP itself. Otherwise the ALB /
        kubelet / Cloud Run scheduler will mark targets unhealthy the
        moment we turn on auth or any path-restrictive middleware.
        """
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "streamable-http")
        self.assertIsInstance(wrapped, HealthCheckMiddleware)
        self.assertIsInstance(wrapped.app, StripTrailingSlashMiddleware)

    def test_custom_mcp_path_is_forwarded(self):
        """Caller-passed mcp_path reaches the GET-405 middleware."""
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "streamable-http", mcp_path="/x")
        # HealthCheck → StripTrailingSlash → NormalizeContentType →
        # RejectNonSSEGet
        get_405 = wrapped.app.app.app
        self.assertIsInstance(get_405, RejectNonSSEGetMiddleware)
        self.assertEqual(get_405._mcp_path, "/x")

    def test_custom_health_path_is_forwarded(self):
        """Caller-passed health_path reaches the HealthCheckMiddleware."""
        app = _make_recording_app()
        wrapped = apply_transport_hardening(
            app, "streamable-http", health_path="/readyz"
        )
        self.assertIsInstance(wrapped, HealthCheckMiddleware)
        self.assertEqual(wrapped._path, "/readyz")

    def test_end_to_end_normalises_both_path_and_content_type(self):
        """Single request with BOTH trailing slash AND application/json-rpc."""
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "streamable-http")

        scope = {
            "type": "http",
            "path": "/mcp/",
            "raw_path": b"/mcp/",
            "headers": [(b"content-type", b"application/json-rpc; charset=utf-8")],
        }
        _run_async(wrapped(scope, MagicMock(), MagicMock()))

        observed = app._calls[0]
        self.assertEqual(observed["path"], "/mcp")
        self.assertEqual(observed["raw_path"], b"/mcp")
        self.assertEqual(
            observed["headers"],
            [(b"content-type", b"application/json; charset=utf-8")],
        )


if __name__ == "__main__":
    unittest.main()
