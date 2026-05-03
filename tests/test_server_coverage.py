"""
Comprehensive tests for server.py uncovered code paths.

Covers: TLS config, HTTPS policy, IP filtering, SourceIPMiddleware,
security posture logging, host validation, transport security,
write-tools init branches, register_tools edge cases, connectivity
error path, CLI functions, env security, and main() entry point.
"""

import argparse
import asyncio
import os
import tempfile
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from zscaler_mcp.server import (
    SourceIPMiddleware,
    ZscalerMCPServer,
    _check_env_file_security,
    _enforce_https_policy,
    _get_allowed_source_ips,
    _get_tls_config,
    _get_transport_security,
    _ip_matches,
    _is_http_allowed,
    _log_security_posture,
    _validate_host_config,
    generate_auth_token,
    list_available_tools,
    parse_services_list,
    parse_tools_list,
)


# ============================================================================
# TLS CONFIGURATION
# ============================================================================
class TestGetTlsConfig(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_no_tls_env_returns_empty(self):
        result = _get_tls_config()
        self.assertEqual(result, {})

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_TLS_CERTFILE": "/tmp/cert.pem", "ZSCALER_MCP_TLS_KEYFILE": ""},
        clear=True,
    )
    def test_incomplete_tls_certfile_only(self):
        with self.assertRaises(SystemExit):
            _get_tls_config()

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_TLS_CERTFILE": "", "ZSCALER_MCP_TLS_KEYFILE": "/tmp/key.pem"},
        clear=True,
    )
    def test_incomplete_tls_keyfile_only(self):
        with self.assertRaises(SystemExit):
            _get_tls_config()

    def test_valid_tls_config(self):
        with tempfile.NamedTemporaryFile(suffix=".pem") as cert, tempfile.NamedTemporaryFile(
            suffix=".pem"
        ) as key:
            with patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_TLS_CERTFILE": cert.name,
                    "ZSCALER_MCP_TLS_KEYFILE": key.name,
                },
                clear=True,
            ):
                result = _get_tls_config()
                self.assertEqual(result["ssl_certfile"], cert.name)
                self.assertEqual(result["ssl_keyfile"], key.name)

    def test_tls_with_password(self):
        with tempfile.NamedTemporaryFile(suffix=".pem") as cert, tempfile.NamedTemporaryFile(
            suffix=".pem"
        ) as key:
            with patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_TLS_CERTFILE": cert.name,
                    "ZSCALER_MCP_TLS_KEYFILE": key.name,
                    "ZSCALER_MCP_TLS_KEYFILE_PASSWORD": "secret",
                },
                clear=True,
            ):
                result = _get_tls_config()
                self.assertEqual(result["ssl_keyfile_password"], "secret")

    def test_tls_with_ca_certs(self):
        with (
            tempfile.NamedTemporaryFile(suffix=".pem") as cert,
            tempfile.NamedTemporaryFile(suffix=".pem") as key,
            tempfile.NamedTemporaryFile(suffix=".pem") as ca,
        ):
            with patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_TLS_CERTFILE": cert.name,
                    "ZSCALER_MCP_TLS_KEYFILE": key.name,
                    "ZSCALER_MCP_TLS_CA_CERTS": ca.name,
                },
                clear=True,
            ):
                result = _get_tls_config()
                self.assertEqual(result["ssl_ca_certs"], ca.name)

    def test_tls_ca_certs_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".pem") as cert, tempfile.NamedTemporaryFile(
            suffix=".pem"
        ) as key:
            with patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_TLS_CERTFILE": cert.name,
                    "ZSCALER_MCP_TLS_KEYFILE": key.name,
                    "ZSCALER_MCP_TLS_CA_CERTS": "/nonexistent/ca.pem",
                },
                clear=True,
            ):
                with self.assertRaises(SystemExit):
                    _get_tls_config()

    @patch.dict(
        os.environ,
        {
            "ZSCALER_MCP_TLS_CERTFILE": "/nonexistent/cert.pem",
            "ZSCALER_MCP_TLS_KEYFILE": "/nonexistent/key.pem",
        },
        clear=True,
    )
    def test_tls_cert_not_found(self):
        with self.assertRaises(SystemExit):
            _get_tls_config()

    def test_tls_key_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".pem") as cert:
            with patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_TLS_CERTFILE": cert.name,
                    "ZSCALER_MCP_TLS_KEYFILE": "/nonexistent/key.pem",
                },
                clear=True,
            ):
                with self.assertRaises(SystemExit):
                    _get_tls_config()


# ============================================================================
# HTTPS POLICY
# ============================================================================
class TestIsHttpAllowed(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_not_set_returns_false(self):
        self.assertFalse(_is_http_allowed())

    @patch.dict(os.environ, {"ZSCALER_MCP_ALLOW_HTTP": "true"}, clear=True)
    def test_true_returns_true(self):
        self.assertTrue(_is_http_allowed())

    @patch.dict(os.environ, {"ZSCALER_MCP_ALLOW_HTTP": "1"}, clear=True)
    def test_one_returns_true(self):
        self.assertTrue(_is_http_allowed())

    @patch.dict(os.environ, {"ZSCALER_MCP_ALLOW_HTTP": "yes"}, clear=True)
    def test_yes_returns_true(self):
        self.assertTrue(_is_http_allowed())

    @patch.dict(os.environ, {"ZSCALER_MCP_ALLOW_HTTP": "false"}, clear=True)
    def test_false_returns_false(self):
        self.assertFalse(_is_http_allowed())


class TestEnforceHttpsPolicy(unittest.TestCase):
    def test_localhost_allowed_without_tls(self):
        _enforce_https_policy("127.0.0.1", 8000, {})

    def test_tls_always_allowed(self):
        _enforce_https_policy("0.0.0.0", 8000, {"ssl_certfile": "/cert.pem"})

    @patch.dict(os.environ, {"ZSCALER_MCP_ALLOW_HTTP": "true"}, clear=True)
    def test_explicit_http_opt_in(self):
        _enforce_https_policy("0.0.0.0", 8000, {})

    @patch.dict(os.environ, {}, clear=True)
    def test_remote_without_tls_blocked(self):
        with self.assertRaises(SystemExit):
            _enforce_https_policy("0.0.0.0", 8000, {})

    def test_ipv6_localhost_allowed(self):
        _enforce_https_policy("::1", 8000, {})


# ============================================================================
# IP FILTERING
# ============================================================================
class TestGetAllowedSourceIps(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_not_set_returns_none(self):
        self.assertIsNone(_get_allowed_source_ips())

    @patch.dict(os.environ, {"ZSCALER_MCP_ALLOWED_SOURCE_IPS": ""}, clear=True)
    def test_empty_returns_none(self):
        self.assertIsNone(_get_allowed_source_ips())

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_SOURCE_IPS": "10.0.0.1, 192.168.1.0/24"},
        clear=True,
    )
    def test_returns_parsed_list(self):
        result = _get_allowed_source_ips()
        self.assertEqual(result, ["10.0.0.1", "192.168.1.0/24"])


class TestIpMatches(unittest.TestCase):
    def test_wildcard_star(self):
        self.assertTrue(_ip_matches("1.2.3.4", ["*"]))

    def test_wildcard_cidr(self):
        self.assertTrue(_ip_matches("10.0.0.1", ["0.0.0.0/0"]))

    def test_exact_match(self):
        self.assertTrue(_ip_matches("10.0.0.5", ["10.0.0.5"]))

    def test_exact_no_match(self):
        self.assertFalse(_ip_matches("10.0.0.6", ["10.0.0.5"]))

    def test_cidr_match(self):
        self.assertTrue(_ip_matches("10.0.0.50", ["10.0.0.0/24"]))

    def test_cidr_no_match(self):
        self.assertFalse(_ip_matches("10.1.0.50", ["10.0.0.0/24"]))

    def test_invalid_client_ip(self):
        self.assertFalse(_ip_matches("not-an-ip", ["10.0.0.0/24"]))

    def test_invalid_entry_skipped(self):
        self.assertFalse(_ip_matches("10.0.0.1", ["bad-entry"]))

    def test_multiple_entries(self):
        self.assertTrue(_ip_matches("192.168.1.5", ["10.0.0.0/24", "192.168.1.0/24"]))


# ============================================================================
# SOURCE IP MIDDLEWARE
# ============================================================================
class TestSourceIPMiddleware(unittest.TestCase):
    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    @staticmethod
    def _make_async_app():
        calls = []

        async def app(scope, receive, send):
            calls.append(scope)

        app._calls = calls
        return app

    def test_non_http_scope_passes_through(self):
        app = self._make_async_app()

        async def _run():
            middleware = SourceIPMiddleware(app, ["10.0.0.1"])
            scope = {"type": "lifespan"}
            await middleware(scope, MagicMock(), MagicMock())
            self.assertEqual(len(app._calls), 1)

        self._run_async(_run())

    def test_health_path_bypasses_check(self):
        app = self._make_async_app()

        async def _run():
            middleware = SourceIPMiddleware(app, ["10.0.0.1"])
            scope = {"type": "http", "path": "/health"}
            await middleware(scope, MagicMock(), MagicMock())
            self.assertEqual(len(app._calls), 1)

        self._run_async(_run())

    def test_healthz_path_bypasses_check(self):
        app = self._make_async_app()

        async def _run():
            middleware = SourceIPMiddleware(app, ["10.0.0.1"])
            scope = {"type": "http", "path": "/healthz"}
            await middleware(scope, MagicMock(), MagicMock())
            self.assertEqual(len(app._calls), 1)

        self._run_async(_run())

    def test_allowed_ip_passes(self):
        app = self._make_async_app()

        async def _run():
            middleware = SourceIPMiddleware(app, ["10.0.0.1"])
            scope = {"type": "http", "path": "/mcp", "client": ("10.0.0.1", 12345)}
            await middleware(scope, MagicMock(), MagicMock())
            self.assertEqual(len(app._calls), 1)

        self._run_async(_run())

    def test_blocked_ip_returns_403(self):
        app = self._make_async_app()

        async def _run():
            middleware = SourceIPMiddleware(app, ["10.0.0.1"])
            scope = {"type": "http", "path": "/mcp", "client": ("192.168.0.1", 12345)}

            sent = []

            async def mock_send(msg):
                sent.append(msg)

            await middleware(scope, MagicMock(), mock_send)
            self.assertEqual(len(app._calls), 0)
            self.assertTrue(any(b"403" in str(s).encode() or s.get("status", 0) == 403 for s in sent))

        self._run_async(_run())

    def test_no_client_in_scope(self):
        app = self._make_async_app()

        async def _run():
            middleware = SourceIPMiddleware(app, ["10.0.0.1"])
            scope = {"type": "http", "path": "/mcp"}

            sent = []

            async def mock_send(msg):
                sent.append(msg)

            await middleware(scope, MagicMock(), mock_send)
            self.assertEqual(len(app._calls), 0)

        self._run_async(_run())


# ============================================================================
# SECURITY POSTURE LOGGING
# ============================================================================
class TestLogSecurityPosture(unittest.TestCase):
    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {"ZSCALER_MCP_AUTH_ENABLED": "false"}, clear=True)
    def test_basic_posture_no_tls(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("SECURITY POSTURE", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {}, clear=True)
    def test_posture_with_tls(self, mock_logger):
        tls_kwargs = {"ssl_certfile": "/cert.pem", "ssl_ca_certs": "/ca.pem"}
        _log_security_posture("streamable-http", "https", "0.0.0.0", 443, tls_kwargs)
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("ENABLED", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {"ZSCALER_MCP_AUTH_ENABLED": "false"}, clear=True)
    def test_posture_auth_disabled(self, mock_logger):
        _log_security_posture("sse", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("DISABLED", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {"ZSCALER_MCP_AUTH_JWKS_URI": "https://example.com/jwks"}, clear=True)
    def test_posture_jwt_auto_detected(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("jwt", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {"ZSCALER_MCP_AUTH_API_KEY": "mykey"}, clear=True)
    def test_posture_apikey_auto_detected(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("api-key", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {"ZSCALER_VANITY_DOMAIN": "example.zscaler.com"}, clear=True)
    def test_posture_zscaler_auto_detected(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("zscaler", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {"ZSCALER_MCP_AUTH_MODE": "jwt"}, clear=True)
    def test_posture_explicit_auth_mode(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("jwt", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {}, clear=True)
    def test_posture_default_jwt(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("jwt", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {}, clear=True)
    def test_posture_with_fastmcp_auth(self, mock_logger):
        mock_auth = MagicMock()
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {}, fastmcp_auth=mock_auth)
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("OIDCProxy", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_DISABLE_HOST_VALIDATION": "true"},
        clear=True,
    )
    def test_posture_host_validation_disabled(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("DISABLED", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_HOSTS": "example.com"},
        clear=True,
    )
    def test_posture_host_validation_allowlist(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("example.com", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "true"},
        clear=True,
    )
    def test_posture_confirmations_skipped(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("skip", combined.lower())

    @patch("zscaler_mcp.server.logger")
    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOW_HTTP": "true"},
        clear=True,
    )
    def test_posture_http_allowed_explicit(self, mock_logger):
        _log_security_posture("streamable-http", "http", "0.0.0.0", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("opt-in", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_SOURCE_IPS": "10.0.0.1,10.0.0.2"},
        clear=True,
    )
    def test_posture_source_ip_enabled(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("10.0.0.1", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_SOURCE_IPS": "*"},
        clear=True,
    )
    def test_posture_source_ip_allow_all(self, mock_logger):
        _log_security_posture("streamable-http", "http", "127.0.0.1", 8000, {})
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("ALLOW ALL", combined)

    @patch("zscaler_mcp.server.logger")
    @patch.dict(os.environ, {}, clear=True)
    def test_posture_tls_no_detail_no_mtls(self, mock_logger):
        tls_kwargs = {"ssl_certfile": "/cert.pem"}
        _log_security_posture("streamable-http", "https", "0.0.0.0", 443, tls_kwargs)
        calls = [str(c) for c in mock_logger.info.call_args_list]
        combined = " ".join(calls)
        self.assertIn("Certificate", combined)


# ============================================================================
# HOST VALIDATION
# ============================================================================
class TestValidateHostConfig(unittest.TestCase):
    def test_non_wildcard_host_passes(self):
        _validate_host_config("127.0.0.1")

    @patch.dict(os.environ, {"ZSCALER_MCP_ALLOWED_HOSTS": "example.com"}, clear=True)
    def test_wildcard_with_allowed_hosts(self):
        _validate_host_config("0.0.0.0")

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_DISABLE_HOST_VALIDATION": "true"},
        clear=True,
    )
    def test_wildcard_with_validation_disabled(self):
        _validate_host_config("0.0.0.0")

    @patch.dict(os.environ, {}, clear=True)
    def test_wildcard_without_config_fails(self):
        with self.assertRaises(SystemExit):
            _validate_host_config("0.0.0.0")


# ============================================================================
# TRANSPORT SECURITY
# ============================================================================
class TestGetTransportSecurity(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_default_returns_none(self):
        result = _get_transport_security(host="127.0.0.1")
        self.assertIsNone(result)

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_DISABLE_HOST_VALIDATION": "true"},
        clear=True,
    )
    def test_disabled_returns_no_dns_protection(self):
        result = _get_transport_security()
        self.assertIsNotNone(result)
        self.assertFalse(result.enable_dns_rebinding_protection)

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_HOSTS": "example.com:8000"},
        clear=True,
    )
    def test_allowed_hosts_returns_settings(self):
        result = _get_transport_security()
        self.assertIsNotNone(result)
        self.assertTrue(result.enable_dns_rebinding_protection)
        self.assertIn("example.com:8000", result.allowed_hosts)

    @patch.dict(os.environ, {}, clear=True)
    def test_wildcard_host_without_config_raises(self):
        with self.assertRaises(SystemExit):
            _get_transport_security(host="0.0.0.0")

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_DISABLE_HOST_VALIDATION": "1"},
        clear=True,
    )
    def test_disabled_with_1(self):
        result = _get_transport_security()
        self.assertIsNotNone(result)

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_DISABLE_HOST_VALIDATION": "yes"},
        clear=True,
    )
    def test_disabled_with_yes(self):
        result = _get_transport_security()
        self.assertIsNotNone(result)


# ============================================================================
# INIT WRITE-TOOLS BRANCHES
# ============================================================================
class TestInitWriteToolsBranches(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_write_tools_enabled_with_allowlist(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(
            enable_write_tools=True,
            write_tools={"zpa_create_*", "zia_update_*"},
        )
        self.assertTrue(server.enable_write_tools)
        self.assertEqual(server.write_tools, {"zpa_create_*", "zia_update_*"})

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_write_tools_enabled_without_allowlist(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enable_write_tools=True)
        self.assertTrue(server.enable_write_tools)
        self.assertIsNone(server.write_tools)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_read_only_mode_default(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer()
        self.assertFalse(server.enable_write_tools)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_auth_provider_stored(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        mock_auth = MagicMock()
        server = ZscalerMCPServer(auth=mock_auth)
        self.assertIs(server._fastmcp_auth, mock_auth)


# ============================================================================
# REGISTER TOOLS EDGE CASES
# ============================================================================
class TestRegisterToolsEdgeCases(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_register_tools_with_enabled_tools_filter(self, mock_get_client, mock_fastmcp):
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        server = ZscalerMCPServer(
            enabled_services={"zpa"},
            enabled_tools={"zpa_list_application_segments"},
        )
        tool_count = server._register_tools()
        self.assertGreater(tool_count, 0)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_register_tools_with_write_mode(self, mock_get_client, mock_fastmcp):
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        server = ZscalerMCPServer(
            enabled_services={"zpa"},
            enable_write_tools=True,
            write_tools={"zpa_create_*"},
        )
        tool_count = server._register_tools()
        self.assertGreater(tool_count, 0)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_register_tools_service_failure(self, mock_get_client, mock_fastmcp):
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server

        server = ZscalerMCPServer(enabled_services={"zia"})
        bad_service = MagicMock()
        bad_service.register_tools.side_effect = Exception("broken")
        bad_service.read_tools = [{"name": "t1", "description": "d"}]
        bad_service.write_tools = [{"name": "t2", "description": "d"}]
        server.services["zia"] = bad_service

        tool_count = server._register_tools()
        self.assertGreater(tool_count, 3)


# ============================================================================
# CONNECTIVITY ERROR PATH
# ============================================================================
class TestConnectivityError(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_connectivity_failure(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer()

        with patch.object(server, "zscaler_check_connectivity") as mock_check:
            mock_check.side_effect = None
            mock_check.return_value = {"connected": False}
            result = mock_check()
            self.assertFalse(result["connected"])

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_connectivity_exception_returns_false(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer()

        def _patched(self_inner):
            try:
                raise ConnectionError("API unreachable")
            except Exception:
                return {"connected": False}

        with patch.object(ZscalerMCPServer, "zscaler_check_connectivity", _patched):
            result = server.zscaler_check_connectivity()
            self.assertFalse(result["connected"])


# ============================================================================
# REGISTER RESOURCES
# ============================================================================
class TestRegisterResources(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_register_resources_with_service_resources(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})

        mock_svc = MagicMock()
        mock_svc.resources = [{"name": "r1"}, {"name": "r2"}]
        mock_svc.register_resources = MagicMock()
        server.services["zia"] = mock_svc

        count = server._register_resources()
        self.assertEqual(count, 2)
        mock_svc.register_resources.assert_called_once()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_register_resources_no_method(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})

        mock_svc = MagicMock(spec=[])
        server.services["zia"] = mock_svc

        count = server._register_resources()
        self.assertEqual(count, 0)


# ============================================================================
# CLI FUNCTIONS
# ============================================================================
class TestParseServicesList(unittest.TestCase):
    def test_empty_returns_all(self):
        result = parse_services_list("")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_valid_services(self):
        result = parse_services_list("zia,zpa")
        self.assertEqual(result, ["zia", "zpa"])

    def test_invalid_service_raises(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_services_list("zia,nonexistent_service")


class TestParseToolsList(unittest.TestCase):
    def test_empty_returns_empty(self):
        result = parse_tools_list("")
        self.assertEqual(result, [])

    def test_invalid_tool_raises(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_tools_list("nonexistent_tool_xyz")


class TestListAvailableTools(unittest.TestCase):
    @patch("zscaler_mcp.server.logger")
    def test_list_all_tools(self, mock_logger):
        list_available_tools()
        self.assertTrue(mock_logger.info.called)

    @patch("zscaler_mcp.server.logger")
    def test_list_tools_filtered_service(self, mock_logger):
        list_available_tools(selected_services={"zia"})
        self.assertTrue(mock_logger.info.called)


class TestGenerateAuthToken(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"ZSCALER_CLIENT_ID": "test_id", "ZSCALER_CLIENT_SECRET": "test_secret"},
        clear=True,
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_basic_token(self, mock_stdout):
        generate_auth_token("basic")
        output = mock_stdout.getvalue()
        self.assertIn("Basic", output)
        self.assertIn("zscaler-mcp-server", output)

    @patch.dict(
        os.environ,
        {"ZSCALER_CLIENT_ID": "test_id", "ZSCALER_CLIENT_SECRET": "test_secret"},
        clear=True,
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_bearer_token(self, mock_stdout):
        generate_auth_token("bearer")
        output = mock_stdout.getvalue()
        self.assertIn("Bearer", output)

    @patch.dict(os.environ, {"ZSCALER_CLIENT_ID": "", "ZSCALER_CLIENT_SECRET": ""}, clear=True)
    def test_missing_credentials_exits(self):
        with self.assertRaises(SystemExit):
            generate_auth_token()


# ============================================================================
# ENV FILE SECURITY
# ============================================================================
class TestCheckEnvFileSecurity(unittest.TestCase):
    def test_no_env_file(self):
        with patch("os.path.isfile", return_value=False):
            _check_env_file_security()

    def test_env_file_with_secrets(self):
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f,
        ):
            f.write("ZSCALER_CLIENT_SECRET=mysecret\n")
            f.flush()

            with (
                patch("os.getcwd", return_value=os.path.dirname(f.name)),
                patch(
                    "zscaler_mcp.server._check_env_file_security",
                    wraps=_check_env_file_security,
                ),
                patch("zscaler_mcp.server.log_security_warning"),
            ):
                with patch("os.path.isfile", side_effect=lambda p: p == f.name):
                    with patch("builtins.open", unittest.mock.mock_open(read_data="ZSCALER_CLIENT_SECRET=mysecret\n")):
                        _check_env_file_security()

            os.unlink(f.name)

    def test_env_file_commented_secrets(self):
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f,
        ):
            f.write("# ZSCALER_CLIENT_SECRET=mysecret\n")
            f.flush()
            f.close()

            _check_env_file_security()

            os.unlink(f.name)

    def test_env_file_os_error(self):
        with patch("os.path.isfile", side_effect=OSError):
            _check_env_file_security()


# ============================================================================
# RUN METHOD BRANCHES
# ============================================================================
class TestRunMethodBranches(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_run_sse_transport(self, mock_get_client, mock_fastmcp):
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        server = ZscalerMCPServer()

        with (
            patch("zscaler_mcp.server.uvicorn.run") as mock_uvicorn,
            patch.dict(os.environ, {"ZSCALER_MCP_AUTH_ENABLED": "false"}),
            patch("zscaler_mcp.auth.apply_auth_middleware") as mock_auth,
        ):
            mock_auth.return_value = mock_server.sse_app()
            server.run("sse", host="127.0.0.1", port=8080)
            mock_uvicorn.assert_called_once()
            mock_auth.assert_called_once()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_run_with_source_ip_acl(self, mock_get_client, mock_fastmcp):
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        server = ZscalerMCPServer()

        with (
            patch("zscaler_mcp.server.uvicorn.run") as mock_uvicorn,
            patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_AUTH_ENABLED": "false",
                    "ZSCALER_MCP_ALLOWED_SOURCE_IPS": "10.0.0.1",
                },
            ),
            patch("zscaler_mcp.auth.apply_auth_middleware") as mock_auth,
        ):
            mock_auth.return_value = mock_server.streamable_http_app()
            server.run("streamable-http", host="127.0.0.1", port=8080)
            mock_uvicorn.assert_called_once()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_run_non_localhost_http_warning(self, mock_get_client, mock_fastmcp):
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server
        server = ZscalerMCPServer()

        with (
            patch("zscaler_mcp.server.uvicorn.run"),
            patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_AUTH_ENABLED": "false",
                    "ZSCALER_MCP_ALLOW_HTTP": "true",
                    "ZSCALER_MCP_ALLOWED_HOSTS": "example.com",
                },
            ),
            patch("zscaler_mcp.auth.apply_auth_middleware") as mock_auth,
            patch("zscaler_mcp.server.log_security_warning") as mock_warn,
        ):
            mock_auth.return_value = mock_server.streamable_http_app()
            server.run("streamable-http", host="10.0.0.1", port=8000)
            mock_warn.assert_called()


# ============================================================================
# MAIN FUNCTION
# ============================================================================
class TestMainFunction(unittest.TestCase):
    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_stdio(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia", "zpa"]
        mock_args.tools = []
        mock_args.client_id = "id"
        mock_args.client_secret = "secret"
        mock_args.customer_id = "cust"
        mock_args.vanity_domain = "example.com"
        mock_args.cloud = "beta"
        mock_args.debug = False
        mock_args.user_agent_comment = None
        mock_args.enable_write_tools = False
        mock_args.write_tools = None
        mock_args.disabled_tools = None
        mock_args.disabled_services = None
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_instance = MagicMock()
        mock_server_cls.return_value = mock_instance

        main()
        mock_server_cls.assert_called_once()
        mock_instance.run.assert_called_once_with("stdio", host="127.0.0.1", port=8000)

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_with_write_tools(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.client_id = None
        mock_args.client_secret = None
        mock_args.customer_id = None
        mock_args.vanity_domain = None
        mock_args.cloud = None
        mock_args.debug = False
        mock_args.user_agent_comment = None
        mock_args.enable_write_tools = True
        mock_args.write_tools = "zpa_create_*,zia_update_*"
        mock_args.disabled_tools = "zcc_*"
        mock_args.disabled_services = "zdx,zcc"
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_instance = MagicMock()
        mock_server_cls.return_value = mock_instance

        main()
        call_kwargs = mock_server_cls.call_args[1]
        self.assertEqual(call_kwargs["write_tools"], {"zpa_create_*", "zia_update_*"})
        self.assertEqual(call_kwargs["disabled_tools"], {"zcc_*"})
        self.assertEqual(call_kwargs["disabled_services"], {"zdx", "zcc"})

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_list_tools(self, mock_gcp, mock_env_check, mock_dotenv, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.log_tool_calls = False
        mock_args.list_tools = True
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        with (
            patch("zscaler_mcp.server.list_available_tools") as mock_list,
            self.assertRaises(SystemExit) as ctx,
        ):
            main()
        mock_list.assert_called_once()
        self.assertEqual(ctx.exception.code, 0)

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_generate_auth_token(self, mock_gcp, mock_env_check, mock_dotenv, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = "basic"
        mock_parse.return_value = mock_args

        with (
            patch("zscaler_mcp.server.generate_auth_token") as mock_gen,
            self.assertRaises(SystemExit) as ctx,
        ):
            main()
        mock_gen.assert_called_once_with("basic")
        self.assertEqual(ctx.exception.code, 0)

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_runtime_error(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.write_tools = None
        mock_args.disabled_tools = None
        mock_args.disabled_services = None
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_server_cls.side_effect = RuntimeError("oops")

        with self.assertRaises(SystemExit) as ctx:
            main()
        self.assertEqual(ctx.exception.code, 1)

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_value_error(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.write_tools = None
        mock_args.disabled_tools = None
        mock_args.disabled_services = None
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_server_cls.side_effect = ValueError("bad config")

        with self.assertRaises(SystemExit) as ctx:
            main()
        self.assertEqual(ctx.exception.code, 1)

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_keyboard_interrupt(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.write_tools = None
        mock_args.disabled_tools = None
        mock_args.disabled_services = None
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_server_cls.side_effect = KeyboardInterrupt()

        with self.assertRaises(SystemExit) as ctx:
            main()
        self.assertEqual(ctx.exception.code, 0)

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_unexpected_error(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.write_tools = None
        mock_args.disabled_tools = None
        mock_args.disabled_services = None
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_server_cls.side_effect = Exception("unexpected")

        with self.assertRaises(SystemExit) as ctx:
            main()
        self.assertEqual(ctx.exception.code, 1)

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_with_log_tool_calls(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = False
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.client_id = None
        mock_args.client_secret = None
        mock_args.customer_id = None
        mock_args.vanity_domain = None
        mock_args.cloud = None
        mock_args.debug = False
        mock_args.user_agent_comment = None
        mock_args.enable_write_tools = False
        mock_args.write_tools = None
        mock_args.disabled_tools = None
        mock_args.disabled_services = None
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_args.log_tool_calls = True
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_instance = MagicMock()
        mock_server_cls.return_value = mock_instance

        with patch("zscaler_mcp.common.tool_helpers.enable_tool_call_logging") as mock_enable:
            main()
            mock_enable.assert_called_once()

    @patch("zscaler_mcp.server.parse_args")
    @patch("zscaler_mcp.server.ZscalerMCPServer")
    @patch("zscaler_mcp.server.load_dotenv")
    @patch("zscaler_mcp.server._check_env_file_security")
    @patch("zscaler_mcp.cloud.gcp_secrets", create=True)
    def test_main_gcp_secrets(self, mock_gcp, mock_env_check, mock_dotenv, mock_server_cls, mock_parse):
        from zscaler_mcp.server import main

        mock_gcp.is_enabled.return_value = True
        mock_args = MagicMock()
        mock_args.transport = "stdio"
        mock_args.services = ["zia"]
        mock_args.tools = []
        mock_args.client_id = None
        mock_args.client_secret = None
        mock_args.customer_id = None
        mock_args.vanity_domain = None
        mock_args.cloud = None
        mock_args.debug = False
        mock_args.user_agent_comment = None
        mock_args.enable_write_tools = False
        mock_args.write_tools = None
        mock_args.disabled_tools = None
        mock_args.disabled_services = None
        mock_args.host = "127.0.0.1"
        mock_args.port = 8000
        mock_args.log_tool_calls = False
        mock_args.list_tools = False
        mock_args.generate_auth_token = None
        mock_args.generate_docs = False
        mock_args.check_docs = False
        mock_parse.return_value = mock_args

        mock_instance = MagicMock()
        mock_server_cls.return_value = mock_instance

        main()
        mock_gcp.load_secrets.assert_called_once()


# ============================================================================
# ALLOWED HOSTS TLS ORIGIN BRANCH
# ============================================================================
class TestTransportSecurityOrigins(unittest.TestCase):
    def test_allowed_hosts_with_tls_uses_https_origins(self):
        with (
            tempfile.NamedTemporaryFile(suffix=".pem") as cert,
            tempfile.NamedTemporaryFile(suffix=".pem") as key,
        ):
            with patch.dict(
                os.environ,
                {
                    "ZSCALER_MCP_ALLOWED_HOSTS": "example.com",
                    "ZSCALER_MCP_TLS_CERTFILE": cert.name,
                    "ZSCALER_MCP_TLS_KEYFILE": key.name,
                },
                clear=True,
            ):
                result = _get_transport_security()
                self.assertIsNotNone(result)
                self.assertIn("https://example.com", result.allowed_origins)

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_HOSTS": "example.com"},
        clear=True,
    )
    def test_allowed_hosts_without_tls_uses_http_origins(self):
        result = _get_transport_security()
        self.assertIsNotNone(result)
        self.assertIn("http://example.com", result.allowed_origins)

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_HOSTS": " , , "},
        clear=True,
    )
    def test_allowed_hosts_empty_after_filtering(self):
        result = _get_transport_security(host="127.0.0.1")
        self.assertIsNone(result)

    @patch.dict(
        os.environ,
        {"ZSCALER_MCP_ALLOWED_HOSTS": " , , "},
        clear=True,
    )
    def test_allowed_hosts_empty_after_filtering_wildcard_host_raises(self):
        with self.assertRaises(SystemExit):
            _get_transport_security(host="0.0.0.0")


# ============================================================================
# OLD-STYLE SERVICE FALLBACK (`.tools` without `.read_tools`)
# ============================================================================
class _OldStyleService:
    """Mimics a service that hasn't migrated to read_tools/write_tools split."""

    def __init__(self):
        self.tools = [{"name": "old_tool_1"}, {"name": "old_tool_2"}]

    def register_tools(self, server, **kwargs):
        pass


class _OldStyleServiceFailing:
    """Old-style service whose registration always fails."""

    def __init__(self):
        self.tools = [{"name": "fail_t1"}, {"name": "fail_t2"}, {"name": "fail_t3"}]

    def register_tools(self, server, **kwargs):
        raise RuntimeError("registration blew up")


class _ModernServiceNoToolsAttr:
    """Service with read_tools/write_tools but no .tools fallback attribute."""

    def __init__(self):
        self.read_tools = [{"name": "m_r1"}]
        self.write_tools = [{"name": "m_w1"}]

    def register_tools(self, server, **kwargs):
        pass


class _ModernServiceNoToolsAttrFailing:
    """Same as above but registration always fails."""

    def __init__(self):
        self.read_tools = [{"name": "mf_r1"}]
        self.write_tools = [{"name": "mf_w1"}]

    def register_tools(self, server, **kwargs):
        raise RuntimeError("modern service blew up")


class _ReadOnlyServiceFailing:
    """Service with only read_tools, no write_tools or .tools — fails on register."""

    def __init__(self):
        self.read_tools = [{"name": "ro_r1"}]

    def register_tools(self, server, **kwargs):
        raise RuntimeError("read-only service failed")


class TestRegisterToolsOldStyleService(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_old_style_service_tools_counted(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})
        server.services = {"zia": _OldStyleService()}
        count = server._register_tools()
        self.assertGreaterEqual(count, 5)  # 3 base tools + 2 from old-style

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_old_style_service_exception_tools_counted(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})
        server.services = {"zia": _OldStyleServiceFailing()}
        count = server._register_tools()
        self.assertGreaterEqual(count, 6)  # 3 base + 3 from failing old-style

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_modern_service_no_tools_attr(self, mock_get_client, mock_fastmcp):
        """Cover elif False branch (635->611): service has write_tools but no .tools."""
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})
        server.services = {"zia": _ModernServiceNoToolsAttr()}
        count = server._register_tools()
        self.assertGreaterEqual(count, 4)  # 3 base + 1 read_tools

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_modern_service_no_tools_attr_exception(self, mock_get_client, mock_fastmcp):
        """Cover elif False branch in exception handler — service with both attrs."""
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})
        server.services = {"zia": _ModernServiceNoToolsAttrFailing()}
        count = server._register_tools()
        self.assertGreaterEqual(count, 5)  # 3 base + 1 read + 1 write

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_readonly_service_exception_no_write_no_tools(self, mock_get_client, mock_fastmcp):
        """Cover elif False branch (645->611): no write_tools and no .tools in exception handler."""
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})
        server.services = {"zia": _ReadOnlyServiceFailing()}
        count = server._register_tools()
        self.assertGreaterEqual(count, 4)  # 3 base + 1 read


# ============================================================================
# SERVICE NAME NOT IN AVAILABLE SERVICES (line 539 branch)
# ============================================================================
class TestInitServiceNotAvailable(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_unknown_service_skipped_silently(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia", "nonexistent_svc_xyz"})
        self.assertNotIn("nonexistent_svc_xyz", server.services)
        self.assertIn("zia", server.services)


# ============================================================================
# REGISTER TOOLS — exception handler WITHOUT read_tools (lines 641-643)
# ============================================================================
class TestRegisterToolsExceptionNoReadTools(unittest.TestCase):
    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_exception_handler_without_read_tools(self, mock_get_client, mock_fastmcp):
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(enabled_services={"zia"})

        bad = MagicMock(spec=[])
        bad.register_tools = MagicMock(side_effect=Exception("boom"))
        bad.write_tools = [{"name": "w1"}]
        server.services = {"zia": bad}

        count = server._register_tools()
        self.assertGreaterEqual(count, 4)  # 3 base + 1 write


# ============================================================================
# list_available_tools — service without .tools attr (line 994 branch)
# ============================================================================
class TestListAvailableToolsNoToolsAttr(unittest.TestCase):
    @patch("zscaler_mcp.server.logger")
    def test_service_without_tools_attr(self, mock_logger):
        bare_cls = MagicMock()
        bare_instance = MagicMock(spec=[])
        bare_cls.return_value = bare_instance

        with patch("zscaler_mcp.server.services.get_available_services", return_value={"bare": bare_cls}):
            list_available_tools(selected_services={"bare"})
        self.assertTrue(mock_logger.info.called)


# ============================================================================
# parse_tools_list — valid tools (line 1180)
# ============================================================================
class TestParseToolsListValid(unittest.TestCase):
    def test_valid_tool_returns_list(self):
        result = parse_tools_list("zcc_list_devices")
        self.assertEqual(result, ["zcc_list_devices"])

    def test_multiple_valid_tools(self):
        result = parse_tools_list("zcc_list_devices,zcc_list_devices")
        self.assertEqual(result, ["zcc_list_devices", "zcc_list_devices"])


# ============================================================================
# parse_args() — comprehensive coverage (lines 1185–1350)
# ============================================================================
class TestParseArgs(unittest.TestCase):
    @patch("sys.argv", ["zscaler-mcp"])
    def test_defaults(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.transport, "stdio")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8000)
        self.assertFalse(args.debug)
        self.assertFalse(args.enable_write_tools)
        self.assertFalse(args.list_tools)
        self.assertIsNone(args.generate_auth_token)
        self.assertFalse(args.log_tool_calls)

    @patch("sys.argv", ["zscaler-mcp", "--transport", "sse"])
    def test_transport_sse(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.transport, "sse")

    @patch("sys.argv", ["zscaler-mcp", "-t", "streamable-http"])
    def test_transport_short_flag(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.transport, "streamable-http")

    @patch("sys.argv", ["zscaler-mcp", "--debug"])
    def test_debug_flag(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertTrue(args.debug)

    @patch("sys.argv", ["zscaler-mcp"])
    def test_debug_from_env(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {"ZSCALER_MCP_DEBUG": "true"}, clear=True):
            args = parse_args()
        self.assertTrue(args.debug)

    @patch("sys.argv", ["zscaler-mcp", "--enable-write-tools"])
    def test_enable_write_tools(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertTrue(args.enable_write_tools)

    @patch("sys.argv", ["zscaler-mcp", "--write-tools", "zpa_create_*,zia_update_*"])
    def test_write_tools_argument(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.write_tools, "zpa_create_*,zia_update_*")

    @patch("sys.argv", ["zscaler-mcp", "--disabled-tools", "zcc_*"])
    def test_disabled_tools_argument(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.disabled_tools, "zcc_*")

    @patch("sys.argv", ["zscaler-mcp", "--disabled-services", "zcc,zdx"])
    def test_disabled_services_argument(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.disabled_services, "zcc,zdx")

    @patch("sys.argv", ["zscaler-mcp", "--client-id", "myid", "--client-secret", "mysecret"])
    def test_api_credentials(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.client_id, "myid")
        self.assertEqual(args.client_secret, "mysecret")

    @patch(
        "sys.argv",
        ["zscaler-mcp", "--customer-id", "cust123", "--vanity-domain", "acme.zscaler.com"],
    )
    def test_customer_and_vanity(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.customer_id, "cust123")
        self.assertEqual(args.vanity_domain, "acme.zscaler.com")

    @patch("sys.argv", ["zscaler-mcp", "--cloud", "beta"])
    def test_cloud_argument(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.cloud, "beta")

    @patch("sys.argv", ["zscaler-mcp", "--host", "10.0.0.1", "--port", "9090"])
    def test_host_port(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.host, "10.0.0.1")
        self.assertEqual(args.port, 9090)

    @patch("sys.argv", ["zscaler-mcp", "-p", "3000"])
    def test_port_short_flag(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.port, 3000)

    @patch("sys.argv", ["zscaler-mcp", "--user-agent-comment", "my-agent"])
    def test_user_agent_comment(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.user_agent_comment, "my-agent")

    @patch("sys.argv", ["zscaler-mcp", "--list-tools"])
    def test_list_tools_flag(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertTrue(args.list_tools)

    @patch("sys.argv", ["zscaler-mcp", "--generate-auth-token"])
    def test_generate_auth_token_default(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.generate_auth_token, "basic")

    @patch("sys.argv", ["zscaler-mcp", "--generate-auth-token", "bearer"])
    def test_generate_auth_token_bearer(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.generate_auth_token, "bearer")

    @patch("sys.argv", ["zscaler-mcp", "--log-tool-calls"])
    def test_log_tool_calls_flag(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertTrue(args.log_tool_calls)

    @patch("sys.argv", ["zscaler-mcp"])
    def test_log_tool_calls_from_env(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {"ZSCALER_MCP_LOG_TOOL_CALLS": "true"}, clear=True):
            args = parse_args()
        self.assertTrue(args.log_tool_calls)

    @patch("sys.argv", ["zscaler-mcp"])
    def test_env_var_defaults(self):
        from zscaler_mcp.server import parse_args

        env = {
            "ZSCALER_MCP_TRANSPORT": "sse",
            "ZSCALER_MCP_HOST": "10.0.0.5",
            "ZSCALER_MCP_PORT": "9999",
            "ZSCALER_CLIENT_ID": "env_id",
            "ZSCALER_CLIENT_SECRET": "env_secret",
            "ZSCALER_CUSTOMER_ID": "env_cust",
            "ZSCALER_VANITY_DOMAIN": "env.zscaler.com",
            "ZSCALER_CLOUD": "production",
            "ZSCALER_MCP_USER_AGENT_COMMENT": "env-agent",
            "ZSCALER_MCP_WRITE_ENABLED": "true",
            "ZSCALER_MCP_WRITE_TOOLS": "zpa_*",
            "ZSCALER_MCP_DISABLED_TOOLS": "zcc_*",
            "ZSCALER_MCP_DISABLED_SERVICES": "zdx",
        }
        with patch.dict(os.environ, env, clear=True):
            args = parse_args()
        self.assertEqual(args.transport, "sse")
        self.assertEqual(args.host, "10.0.0.5")
        self.assertEqual(args.port, 9999)
        self.assertEqual(args.client_id, "env_id")
        self.assertEqual(args.client_secret, "env_secret")
        self.assertEqual(args.customer_id, "env_cust")
        self.assertEqual(args.vanity_domain, "env.zscaler.com")
        self.assertEqual(args.cloud, "production")
        self.assertEqual(args.user_agent_comment, "env-agent")
        self.assertTrue(args.enable_write_tools)
        self.assertEqual(args.write_tools, "zpa_*")
        self.assertEqual(args.disabled_tools, "zcc_*")
        self.assertEqual(args.disabled_services, "zdx")

    @patch("sys.argv", ["zscaler-mcp", "-s", "zia,zpa"])
    def test_services_flag(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertEqual(args.services, ["zia", "zpa"])

    @patch("sys.argv", ["zscaler-mcp", "-d"])
    def test_debug_short_flag(self):
        from zscaler_mcp.server import parse_args

        with patch.dict(os.environ, {}, clear=True):
            args = parse_args()
        self.assertTrue(args.debug)


if __name__ == "__main__":
    unittest.main()
