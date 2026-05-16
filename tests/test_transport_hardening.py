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
    NormalizeContentTypeMiddleware,
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
        self.assertIsInstance(wrapped, StripTrailingSlashMiddleware)

    def test_sse_returns_wrapped_app(self):
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "sse")
        self.assertIsNot(wrapped, app)
        self.assertIsInstance(wrapped, StripTrailingSlashMiddleware)

    def test_outermost_layer_is_strip_trailing_slash(self):
        """Path normalisation MUST happen before any header / auth logic.

        ``StripTrailingSlashMiddleware`` must be the outer layer so
        :class:`AuthMiddleware`'s ``SKIP_PATHS`` check (e.g. ``/health``)
        correctly handles ``/health/`` and ``/health``.
        """
        app = _make_recording_app()
        wrapped = apply_transport_hardening(app, "streamable-http")
        # Outer = StripTrailingSlash, inner = NormalizeContentType.
        self.assertIsInstance(wrapped, StripTrailingSlashMiddleware)
        self.assertIsInstance(wrapped.app, NormalizeContentTypeMiddleware)
        self.assertIs(wrapped.app.app, app)

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
