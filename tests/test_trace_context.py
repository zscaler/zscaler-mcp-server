"""Tests for W3C Trace Context propagation (P5 prototype)."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from zscaler_mcp.common.tool_helpers import _wrap_with_audit, enable_tool_call_logging
from zscaler_mcp.common.trace_context import (
    TraceContextMiddleware,
    apply_trace_headers_to_client,
    bind_trace_context,
    build_trace_context,
    extract_trace_context_from_http_headers,
    extract_trace_context_from_mcp_request_ctx,
    extract_trace_context_from_meta,
    format_audit_trace_suffix,
    get_current_trace_context,
    reset_trace_context,
    sdk_trace_headers,
    try_extract_from_tool_kwargs,
    validate_traceparent,
)

_VALID_TRACEPARENT = (
    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
)
_VALID_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"


class TestValidateTraceparent(unittest.TestCase):
    def test_valid_traceparent(self):
        self.assertTrue(validate_traceparent(_VALID_TRACEPARENT))

    def test_rejects_all_zero_trace_id(self):
        bad = "00-" + ("0" * 32) + "-00f067aa0ba902b7-01"
        self.assertFalse(validate_traceparent(bad))

    def test_rejects_all_zero_span_id(self):
        bad = "00-4bf92f3577b34da6a3ce929d0e0e4736-" + ("0" * 16) + "-01"
        self.assertFalse(validate_traceparent(bad))

    def test_rejects_wrong_version(self):
        bad = "01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        self.assertFalse(validate_traceparent(bad))

    def test_rejects_malformed(self):
        self.assertFalse(validate_traceparent("not-a-traceparent"))
        self.assertFalse(validate_traceparent(""))
        self.assertFalse(validate_traceparent(None))  # type: ignore[arg-type]


class TestExtractTraceContext(unittest.TestCase):
    def test_extract_from_meta(self):
        ctx = extract_trace_context_from_meta(
            {
                "traceparent": _VALID_TRACEPARENT,
                "tracestate": "vendor=value",
                "baggage": "user=alice",
            }
        )
        self.assertIsNotNone(ctx)
        assert ctx is not None
        self.assertEqual(ctx.trace_id, _VALID_TRACE_ID)
        self.assertEqual(ctx.tracestate, "vendor=value")
        self.assertEqual(ctx.baggage, "user=alice")

    def test_extract_from_meta_ignores_invalid_traceparent(self):
        self.assertIsNone(
            extract_trace_context_from_meta({"traceparent": "bad-value"})
        )

    def test_extract_from_http_headers_case_insensitive(self):
        ctx = extract_trace_context_from_http_headers(
            {
                "Traceparent": _VALID_TRACEPARENT,
                "Tracestate": "vendor=value",
                "Baggage": "user=alice",
            }
        )
        self.assertIsNotNone(ctx)
        assert ctx is not None
        self.assertEqual(ctx.trace_id, _VALID_TRACE_ID)

    def test_try_extract_from_kwargs_meta_string(self):
        ctx = try_extract_from_tool_kwargs(
            {
                "kwargs": json.dumps(
                    {
                        "_meta": {
                            "traceparent": _VALID_TRACEPARENT,
                            "tracestate": "vendor=value",
                        }
                    }
                )
            }
        )
        self.assertIsNotNone(ctx)
        assert ctx is not None
        self.assertEqual(ctx.tracestate, "vendor=value")

    def test_try_extract_from_direct_meta_kwarg(self):
        ctx = try_extract_from_tool_kwargs(
            {"_meta": {"traceparent": _VALID_TRACEPARENT}}
        )
        self.assertIsNotNone(ctx)


class TestContextVarLifecycle(unittest.TestCase):
    def test_bind_and_reset(self):
        self.assertIsNone(get_current_trace_context())
        ctx = build_trace_context(_VALID_TRACEPARENT)
        token = bind_trace_context(ctx)
        try:
            self.assertIs(get_current_trace_context(), ctx)
            self.assertIn(_VALID_TRACE_ID, format_audit_trace_suffix())
        finally:
            reset_trace_context(token)
        self.assertIsNone(get_current_trace_context())

    def test_missing_traceparent_no_audit_suffix(self):
        self.assertEqual(format_audit_trace_suffix(), "")


class TestSdkHeaderPropagation(unittest.TestCase):
    def test_sdk_trace_headers(self):
        ctx = build_trace_context(
            _VALID_TRACEPARENT,
            tracestate="vendor=value",
            baggage="user=alice",
        )
        token = bind_trace_context(ctx)
        try:
            headers = sdk_trace_headers()
            self.assertEqual(headers["traceparent"], _VALID_TRACEPARENT)
            self.assertEqual(headers["tracestate"], "vendor=value")
            self.assertEqual(headers["baggage"], "user=alice")
        finally:
            reset_trace_context(token)

    def test_apply_trace_headers_to_client(self):
        ctx = build_trace_context(_VALID_TRACEPARENT, tracestate="vendor=value")
        token = bind_trace_context(ctx)
        try:
            client = MagicMock()
            client._request_executor._custom_headers = {}
            apply_trace_headers_to_client(client)
            self.assertEqual(
                client._request_executor._custom_headers["traceparent"],
                _VALID_TRACEPARENT,
            )
            self.assertEqual(
                client._request_executor._custom_headers["tracestate"],
                "vendor=value",
            )
        finally:
            reset_trace_context(token)

    @patch("zscaler_mcp.client.apply_trace_headers_to_client")
    @patch("zscaler_mcp.client.ZscalerClient")
    def test_get_zscaler_client_applies_trace_headers(
        self, mock_client_cls, mock_apply
    ):
        from zscaler_mcp.client import get_zscaler_client

        mock_client_cls.return_value = MagicMock()
        with patch.dict(
            "os.environ",
            {
                "ZSCALER_CLIENT_ID": "id",
                "ZSCALER_CLIENT_SECRET": "secret",
                "ZSCALER_VANITY_DOMAIN": "example.zsapi.net",
            },
            clear=False,
        ):
            get_zscaler_client(service="zia")
        mock_apply.assert_called_once()


class TestAuditLogIntegration(unittest.TestCase):
    def setUp(self):
        enable_tool_call_logging()

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_traceparent_propagated_to_audit_log(self, mock_logger):
        fn = MagicMock(return_value=[{"id": 1}])
        wrapped = _wrap_with_audit(fn, "zia_list_locations")
        meta = {"traceparent": _VALID_TRACEPARENT}
        wrapped(
            kwargs=json.dumps({"_meta": meta}),
            page=1,
        )
        first_call_args = mock_logger.info.call_args_list[0][0]
        self.assertEqual(first_call_args[0], "[TOOL CALL] %s%s | args: %s")
        self.assertIn(_VALID_TRACE_ID, first_call_args[2])

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_missing_traceparent_no_error(self, mock_logger):
        fn = MagicMock(return_value=[{"id": 1}])
        wrapped = _wrap_with_audit(fn, "zia_list_locations")
        wrapped(page=1)
        first_call_args = mock_logger.info.call_args_list[0][0]
        self.assertEqual(first_call_args[2], "")

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_malformed_traceparent_ignored(self, mock_logger):
        fn = MagicMock(return_value=[{"id": 1}])
        wrapped = _wrap_with_audit(fn, "zia_list_locations")
        wrapped(kwargs=json.dumps({"_meta": {"traceparent": "bad"}}))
        first_call_args = mock_logger.info.call_args_list[0][0]
        self.assertEqual(first_call_args[2], "")


class TestExtractFromMcpRequestCtx(unittest.TestCase):
    """Spec-correct extraction from ``mcp.server.lowlevel.server.request_ctx``.

    This is the path that lights up end-to-end on real streamable-http
    requests once a client sends ``params._meta.traceparent`` in its
    JSON-RPC body.
    """

    def _set_request_ctx(self, meta):
        """Install a synthetic RequestContext on the SDK's ContextVar.

        Returns the reset token so the test can clean up.
        """
        from mcp.server.lowlevel.server import request_ctx as mcp_request_ctx
        from mcp.shared.context import RequestContext

        ctx = RequestContext(
            request_id=1,
            meta=meta,
            session=None,
            lifespan_context=None,
        )
        return mcp_request_ctx, mcp_request_ctx.set(ctx)

    def test_returns_none_when_ctx_unset(self):
        self.assertIsNone(extract_trace_context_from_mcp_request_ctx())

    def test_returns_none_when_meta_is_none(self):
        var, token = self._set_request_ctx(meta=None)
        try:
            self.assertIsNone(extract_trace_context_from_mcp_request_ctx())
        finally:
            var.reset(token)

    def test_returns_none_when_meta_lacks_traceparent(self):
        from mcp.types import RequestParams

        meta = RequestParams.Meta()
        var, token = self._set_request_ctx(meta=meta)
        try:
            self.assertIsNone(extract_trace_context_from_mcp_request_ctx())
        finally:
            var.reset(token)

    def test_extracts_traceparent_from_pydantic_meta(self):
        from mcp.types import RequestParams

        meta = RequestParams.Meta(
            traceparent=_VALID_TRACEPARENT,
            tracestate="vendor=value",
            baggage="user=alice",
        )
        var, token = self._set_request_ctx(meta=meta)
        try:
            ctx = extract_trace_context_from_mcp_request_ctx()
            self.assertIsNotNone(ctx)
            assert ctx is not None
            self.assertEqual(ctx.trace_id, _VALID_TRACE_ID)
            self.assertEqual(ctx.tracestate, "vendor=value")
            self.assertEqual(ctx.baggage, "user=alice")
        finally:
            var.reset(token)

    def test_ignores_invalid_traceparent_in_meta(self):
        from mcp.types import RequestParams

        meta = RequestParams.Meta(traceparent="not-a-traceparent")
        var, token = self._set_request_ctx(meta=meta)
        try:
            self.assertIsNone(extract_trace_context_from_mcp_request_ctx())
        finally:
            var.reset(token)

    def test_returns_none_when_sdk_not_importable(self):
        with patch.dict(
            "sys.modules",
            {"mcp.server.lowlevel.server": None},
        ):
            self.assertIsNone(extract_trace_context_from_mcp_request_ctx())

    def test_accepts_plain_dict_meta(self):
        # Defensive: not the SDK's normal shape, but the extractor should
        # cope if a future SDK version (or a custom integration test)
        # stuffs a plain dict in instead of a pydantic model.
        from mcp.server.lowlevel.server import request_ctx as mcp_request_ctx
        from mcp.shared.context import RequestContext

        ctx_obj = RequestContext(
            request_id=1,
            meta={"traceparent": _VALID_TRACEPARENT},  # type: ignore[arg-type]
            session=None,
            lifespan_context=None,
        )
        token = mcp_request_ctx.set(ctx_obj)
        try:
            ctx = extract_trace_context_from_mcp_request_ctx()
            self.assertIsNotNone(ctx)
            assert ctx is not None
            self.assertEqual(ctx.trace_id, _VALID_TRACE_ID)
        finally:
            mcp_request_ctx.reset(token)


class TestAuditWrapperPathPriority(unittest.TestCase):
    """The wrapper must prefer the spec-correct request_ctx path over the
    kwargs shim, and yield to an explicit pre-bound context above both.
    """

    def setUp(self):
        enable_tool_call_logging()

    def _set_request_ctx_meta(self, **trace_fields):
        from mcp.server.lowlevel.server import request_ctx as mcp_request_ctx
        from mcp.shared.context import RequestContext
        from mcp.types import RequestParams

        meta = RequestParams.Meta(**trace_fields)
        ctx = RequestContext(
            request_id=1,
            meta=meta,
            session=None,
            lifespan_context=None,
        )
        return mcp_request_ctx, mcp_request_ctx.set(ctx)

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_request_ctx_meta_lands_in_audit_log(self, mock_logger):
        var, token = self._set_request_ctx_meta(traceparent=_VALID_TRACEPARENT)
        try:
            fn = MagicMock(return_value=[{"id": 1}])
            wrapped = _wrap_with_audit(fn, "zia_list_locations")
            wrapped(page=1)
            first_call_args = mock_logger.info.call_args_list[0][0]
            self.assertEqual(first_call_args[0], "[TOOL CALL] %s%s | args: %s")
            self.assertIn(_VALID_TRACE_ID, first_call_args[2])
        finally:
            var.reset(token)

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_request_ctx_path_propagates_into_tool_scope(self, mock_logger):
        # The tool function sees the trace context bound for the call —
        # which is what makes downstream SDK header forwarding work.
        seen = {}

        def fn(**kwargs):
            ctx = get_current_trace_context()
            seen["trace_id"] = ctx.trace_id if ctx else None
            return []

        var, token = self._set_request_ctx_meta(traceparent=_VALID_TRACEPARENT)
        try:
            wrapped = _wrap_with_audit(fn, "zia_list_locations")
            wrapped(page=1)
        finally:
            var.reset(token)
        self.assertEqual(seen["trace_id"], _VALID_TRACE_ID)

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_request_ctx_preferred_over_kwargs_shim(self, mock_logger):
        alt_traceparent = (
            "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"
        )
        alt_trace_id = "a" * 32
        # request_ctx wins; the kwargs shim payload must be ignored.
        var, token = self._set_request_ctx_meta(traceparent=_VALID_TRACEPARENT)
        try:
            fn = MagicMock(return_value=[])
            wrapped = _wrap_with_audit(fn, "zia_list_locations")
            wrapped(kwargs=json.dumps({"_meta": {"traceparent": alt_traceparent}}))
            first_call_args = mock_logger.info.call_args_list[0][0]
            self.assertIn(_VALID_TRACE_ID, first_call_args[2])
            self.assertNotIn(alt_trace_id, first_call_args[2])
        finally:
            var.reset(token)

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_kwargs_shim_used_only_when_request_ctx_empty(self, mock_logger):
        # No active request_ctx → fall through to the shim path.
        fn = MagicMock(return_value=[])
        wrapped = _wrap_with_audit(fn, "zia_list_locations")
        wrapped(kwargs=json.dumps({"_meta": {"traceparent": _VALID_TRACEPARENT}}))
        first_call_args = mock_logger.info.call_args_list[0][0]
        self.assertIn(_VALID_TRACE_ID, first_call_args[2])

    @patch("zscaler_mcp.common.tool_helpers.audit_logger")
    def test_explicit_bound_context_beats_request_ctx(self, mock_logger):
        # If someone bound the context manually before invoking the tool
        # (a future middleware that DOES propagate), the wrapper must
        # respect it and not silently override.
        explicit = build_trace_context(
            "00-cccccccccccccccccccccccccccccccc-dddddddddddddddd-01"
        )
        explicit_trace_id = "c" * 32
        bind_token = bind_trace_context(explicit)
        var, token = self._set_request_ctx_meta(traceparent=_VALID_TRACEPARENT)
        try:
            fn = MagicMock(return_value=[])
            wrapped = _wrap_with_audit(fn, "zia_list_locations")
            wrapped(page=1)
            first_call_args = mock_logger.info.call_args_list[0][0]
            self.assertIn(explicit_trace_id, first_call_args[2])
            self.assertNotIn(_VALID_TRACE_ID, first_call_args[2])
        finally:
            var.reset(token)
            reset_trace_context(bind_token)


class TestTraceContextMiddleware(unittest.IsolatedAsyncioTestCase):
    async def test_middleware_binds_headers_for_request(self):
        seen = {}

        async def app(scope, receive, send):
            ctx = get_current_trace_context()
            seen["trace_id"] = ctx.trace_id if ctx else None
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = TraceContextMiddleware(app)
        scope = {
            "type": "http",
            "headers": [
                (b"traceparent", _VALID_TRACEPARENT.encode()),
                (b"tracestate", b"vendor=value"),
            ],
        }
        await middleware(scope, receive=lambda: None, send=AsyncMock())
        self.assertEqual(seen["trace_id"], _VALID_TRACE_ID)

    async def test_middleware_clears_context_after_request(self):
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = TraceContextMiddleware(app)
        scope = {
            "type": "http",
            "headers": [(b"traceparent", _VALID_TRACEPARENT.encode())],
        }
        await middleware(scope, receive=lambda: None, send=AsyncMock())
        self.assertIsNone(get_current_trace_context())


if __name__ == "__main__":
    unittest.main()
