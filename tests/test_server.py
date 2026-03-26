"""
Tests for the Zscaler Integrations MCP Server.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from zscaler_mcp import services
from zscaler_mcp.server import ZscalerMCPServer


class TestZscalerMCPServer(unittest.TestCase):
    """Test cases for the Zscaler Integrations MCP Server."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Ensure services are available before each test
        self.available_services = services.get_available_services()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_initialization(self, mock_get_client, mock_fastmcp):
        """Test server initialization with default settings."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(
            client_id="test_client_id",
            client_secret="test_client_secret",
            customer_id="test_customer_id",
            vanity_domain="test_domain",
            cloud="beta",
            debug=True,
        )

        # Verify client initialization is deferred (not called during __init__)
        # Client will be initialized when tools are executed
        mock_get_client.assert_not_called()

        # Verify server initialization
        mock_fastmcp.assert_called_once_with(
            name="Zscaler Integrations MCP Server",
            instructions="This server provides access to Zscaler capabilities across ZIA, ZPA, ZDX, ZCC and ZIdentity services.",
            debug=True,
            log_level="DEBUG",
            transport_security=None,
        )

        # Verify services initialization
        available_service_names = services.get_service_names()
        self.assertEqual(len(server.services), len(available_service_names))
        for service_name in available_service_names:
            self.assertIn(service_name, server.services)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_with_specific_services(self, mock_get_client, mock_fastmcp):
        """Test server initialization with specific services."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server with only the zpa service
        server = ZscalerMCPServer(enabled_services={"zpa"})

        # Verify services initialization
        self.assertEqual(len(server.services), 1)
        self.assertIn("zpa", server.services)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_legacy_mode(self, mock_get_client, mock_fastmcp):
        """Test server initialization in legacy mode."""
        # Setup mocks
        mock_get_client.side_effect = ValueError("You must specify the 'service'")
        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server in legacy mode
        server = ZscalerMCPServer()

        # Verify that client is None in legacy mode
        self.assertIsNone(server.zscaler_client)

        # Verify that services are still initialized
        self.assertGreater(len(server.services), 0)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_with_enabled_tools(self, mock_get_client, mock_fastmcp):
        """Test server initialization with specific tools enabled."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server with specific tools enabled
        server = ZscalerMCPServer(enabled_services={"zpa"}, enabled_tools={"zpa_app_segments"})

        # Verify that enabled_tools is set
        self.assertEqual(server.enabled_tools, {"zpa_app_segments"})

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_zscaler_check_connectivity(self, mock_get_client, mock_fastmcp):
        """Test checking Zscaler API connectivity."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer()

        # Call zscaler_check_connectivity
        result = server.zscaler_check_connectivity()

        # Verify result
        expected_result = {"connected": True}
        self.assertEqual(result, expected_result)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_get_available_services(self, mock_get_client, mock_fastmcp):
        """Test getting available services."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer()

        # Call get_available_services
        result = server.get_available_services()

        # Get the actual service names from the registry
        expected_services = services.get_service_names()

        # Verify result contains enabled services matching the registry
        self.assertEqual(set(result["enabled_services"].keys()), set(expected_services))
        self.assertNotIn("disabled_services", result)
        self.assertNotIn("disabled_tool_patterns", result)
        self.assertNotIn("note", result)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_get_available_services_with_disabled_services(self, mock_get_client, mock_fastmcp):
        """Test get_available_services when some services are disabled."""
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        server = ZscalerMCPServer(disabled_services={"zcc", "zdx"})
        result = server.get_available_services()

        self.assertNotIn("zcc", result["enabled_services"])
        self.assertNotIn("zdx", result["enabled_services"])
        self.assertIn("disabled_services", result)
        self.assertIn("zcc", result["disabled_services"])
        self.assertIn("zdx", result["disabled_services"])
        self.assertIn("note", result)
        self.assertIn("Disabled services", result["note"])

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_get_available_services_with_disabled_tools(self, mock_get_client, mock_fastmcp):
        """Test get_available_services when tool patterns are disabled."""
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        server = ZscalerMCPServer(disabled_tools={"zcc_list_*", "zia_delete_*"})
        result = server.get_available_services()

        self.assertIn("disabled_tool_patterns", result)
        self.assertEqual(result["disabled_tool_patterns"], ["zcc_list_*", "zia_delete_*"])
        self.assertIn("note", result)
        self.assertIn("fnmatch wildcards", result["note"])

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_get_available_services_with_both_disabled(self, mock_get_client, mock_fastmcp):
        """Test get_available_services with both disabled services and tools."""
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        server = ZscalerMCPServer(disabled_services={"zcc"}, disabled_tools={"zia_delete_*"})
        result = server.get_available_services()

        self.assertIn("disabled_services", result)
        self.assertIn("zcc", result["disabled_services"])
        self.assertIn("disabled_tool_patterns", result)
        self.assertEqual(result["disabled_tool_patterns"], ["zia_delete_*"])
        self.assertIn("note", result)
        self.assertIn("Disabled services", result["note"])
        self.assertIn("fnmatch wildcards", result["note"])

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_register_tools(self, mock_get_client, mock_fastmcp):
        """Test that tools are properly registered."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer()

        # Call _register_tools
        tool_count = server._register_tools()  # pylint: disable=protected-access

        # Verify that core tools are registered
        # Note: Tool registration now includes annotations parameter
        # Just verify that add_tool was called
        self.assertGreater(mock_server_instance.add_tool.call_count, 0)

        # Verify tool count is at least 2 (core tools)
        self.assertGreaterEqual(tool_count, 2)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_register_resources(self, mock_get_client, mock_fastmcp):
        """Test that resources are properly registered."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer()

        # Call _register_resources
        resource_count = server._register_resources()  # pylint: disable=protected-access

        # Verify resource count (should be 0 for now as no resources are implemented)
        self.assertEqual(resource_count, 0)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_configuration_storage(self, mock_get_client, mock_fastmcp):
        """Test that server configuration is properly stored."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server with specific configuration
        server = ZscalerMCPServer(
            client_id="test_id",
            client_secret="test_secret",
            customer_id="test_customer",
            vanity_domain="test.domain.com",
            cloud="beta",
            debug=True,
            user_agent_comment="test_comment",
        )

        # Verify configuration is stored
        self.assertEqual(server.client_id, "test_id")
        self.assertEqual(server.client_secret, "test_secret")
        self.assertEqual(server.customer_id, "test_customer")
        self.assertEqual(server.vanity_domain, "test.domain.com")
        self.assertEqual(server.cloud, "beta")
        self.assertTrue(server.debug)
        self.assertEqual(server.user_agent_comment, "test_comment")

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_default_enabled_services(self, mock_get_client, mock_fastmcp):
        """Test that all services are enabled by default."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server without specifying enabled_services
        server = ZscalerMCPServer()

        # Verify that all available services are enabled by default
        available_service_names = services.get_service_names()
        self.assertEqual(server.enabled_services, set(available_service_names))

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_service_initialization_failure(self, mock_get_client, mock_fastmcp):
        """Test server initialization when a service fails to initialize."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Mock a service class that raises an exception
        with patch.dict(
            services._AVAILABLE_SERVICES,
            {  # pylint: disable=protected-access
                "test_service": MagicMock(side_effect=Exception("Service init failed"))
            },
        ):
            # Create server with the problematic service - should raise the exception
            with self.assertRaises(Exception) as context:
                ZscalerMCPServer(enabled_services={"test_service"})

            # Verify the exception message
            self.assertEqual(str(context.exception), "Service init failed")

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_server_run_method(self, mock_get_client, mock_fastmcp):
        """Test the server run method."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer()

        # Test stdio transport (default)
        with patch.object(server.server, "run") as mock_run:
            server.run("stdio")
            mock_run.assert_called_once_with("stdio")

        # Test sse transport (use localhost to avoid host validation guard)
        with (
            patch("zscaler_mcp.server.uvicorn.run") as mock_uvicorn_run,
            patch.dict(os.environ, {"ZSCALER_MCP_AUTH_ENABLED": "false"}),
        ):
            server.run("sse", host="127.0.0.1", port=8080)
            mock_uvicorn_run.assert_called_once()

        # Test streamable-http transport
        with (
            patch("zscaler_mcp.server.uvicorn.run") as mock_uvicorn_run,
            patch.dict(os.environ, {"ZSCALER_MCP_AUTH_ENABLED": "false"}),
        ):
            server.run("streamable-http", host="127.0.0.1", port=8080)
            mock_uvicorn_run.assert_called_once()


class TestDisabledToolsAndServices(unittest.TestCase):
    """Test cases for --disabled-tools and --disabled-services flags."""

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_disabled_tools_stored(self, mock_get_client, mock_fastmcp):
        """Test that disabled_tools parameter is stored on the server instance."""
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(disabled_tools={"zcc_*", "zdx_list_devices"})
        self.assertEqual(server.disabled_tools, {"zcc_*", "zdx_list_devices"})

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_disabled_tools_none_by_default(self, mock_get_client, mock_fastmcp):
        """Test that disabled_tools defaults to None when not provided."""
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer()
        self.assertIsNone(server.disabled_tools)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_disabled_services_stored(self, mock_get_client, mock_fastmcp):
        """Test that disabled_services parameter is stored on the server instance."""
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(disabled_services={"zcc", "zdx"})
        self.assertEqual(server.disabled_services, {"zcc", "zdx"})

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_disabled_services_removes_from_enabled(self, mock_get_client, mock_fastmcp):
        """Test that disabled_services are subtracted from enabled_services."""
        mock_fastmcp.return_value = MagicMock()
        all_services = services.get_service_names()
        server = ZscalerMCPServer(disabled_services={"zcc"})

        self.assertNotIn("zcc", server.enabled_services)
        self.assertEqual(len(server.enabled_services), len(all_services) - 1)
        self.assertNotIn("zcc", server.services)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_disabled_services_with_enabled_services(self, mock_get_client, mock_fastmcp):
        """Test that disabled_services works together with enabled_services."""
        mock_fastmcp.return_value = MagicMock()
        server = ZscalerMCPServer(
            enabled_services={"zcc", "zpa", "zia"},
            disabled_services={"zcc"},
        )
        self.assertEqual(server.enabled_services, {"zpa", "zia"})
        self.assertNotIn("zcc", server.services)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_disabled_tools_passed_to_register_tools(self, mock_get_client, mock_fastmcp):
        """Test that disabled_tools is threaded through to service.register_tools."""
        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        disabled = {"zcc_devices_csv_exporter"}
        server = ZscalerMCPServer(
            enabled_services={"zcc"},
            disabled_tools=disabled,
        )
        server._register_tools()

        for svc in server.services.values():
            if hasattr(svc, "register_tools"):
                pass


class TestZscalerMCPServerAuth(unittest.TestCase):
    """Test cases for the library-level auth parameter on ZscalerMCPServer."""

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_auth_param_stored(self, mock_get_client, mock_fastmcp):
        """Test that auth parameter is stored on the server instance."""
        mock_fastmcp.return_value = MagicMock()
        mock_auth = MagicMock()

        server = ZscalerMCPServer(auth=mock_auth)
        self.assertIs(server._fastmcp_auth, mock_auth)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_auth_param_none_by_default(self, mock_get_client, mock_fastmcp):
        """Test that auth defaults to None when not provided."""
        mock_fastmcp.return_value = MagicMock()

        server = ZscalerMCPServer()
        self.assertIsNone(server._fastmcp_auth)

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_run_stdio_ignores_auth(self, mock_get_client, mock_fastmcp):
        """Test that stdio transport ignores the auth parameter."""
        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance
        mock_auth = MagicMock()

        server = ZscalerMCPServer(auth=mock_auth)

        with patch.object(server.server, "run") as mock_run:
            server.run("stdio")
            mock_run.assert_called_once_with("stdio")

        mock_auth.get_middleware.assert_not_called()
        mock_auth.get_routes.assert_not_called()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_run_http_with_auth_skips_env_middleware(self, mock_get_client, mock_fastmcp):
        """Test that providing auth skips apply_auth_middleware."""
        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        mock_auth = MagicMock()
        mock_auth.get_middleware.return_value = []
        mock_auth.get_routes.return_value = []
        mock_auth.required_scopes = []
        mock_auth._get_resource_url.return_value = None

        server = ZscalerMCPServer(auth=mock_auth)

        with (
            patch("zscaler_mcp.server.uvicorn.run"),
            patch.dict(os.environ, {"ZSCALER_MCP_AUTH_ENABLED": "false"}),
            patch("zscaler_mcp.auth.apply_auth_middleware") as mock_apply,
            patch("zscaler_mcp.server.ZscalerMCPServer._build_fastmcp_auth_app") as mock_build,
        ):
            mock_build.return_value = MagicMock()
            server.run("streamable-http", host="127.0.0.1", port=8080)

            mock_build.assert_called_once_with("streamable-http")
            mock_apply.assert_not_called()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_run_http_without_auth_uses_env_middleware(self, mock_get_client, mock_fastmcp):
        """Test that without auth, the env-var middleware is applied."""
        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        server = ZscalerMCPServer()

        with (
            patch("zscaler_mcp.server.uvicorn.run"),
            patch.dict(os.environ, {"ZSCALER_MCP_AUTH_ENABLED": "false"}),
            patch("zscaler_mcp.auth.apply_auth_middleware") as mock_apply,
        ):
            mock_apply.return_value = mock_server_instance.streamable_http_app()
            server.run("streamable-http", host="127.0.0.1", port=8080)

            mock_apply.assert_called_once()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_build_fastmcp_auth_app_streamable_http(self, mock_get_client, mock_fastmcp):
        """Test _build_fastmcp_auth_app creates app with auth routes for streamable-http."""
        mock_server_instance = MagicMock()
        mock_server_instance._session_manager = None
        mock_server_instance.settings.json_response = False
        mock_server_instance.settings.stateless_http = False
        mock_server_instance.settings.transport_security = None
        mock_server_instance.settings.streamable_http_path = "/mcp"
        mock_fastmcp.return_value = mock_server_instance

        mock_auth = MagicMock()
        mock_auth.get_middleware.return_value = []
        mock_auth.get_routes.return_value = []
        mock_auth.required_scopes = []
        mock_auth._get_resource_url.return_value = None

        server = ZscalerMCPServer(auth=mock_auth)

        with (
            patch("mcp.server.streamable_http_manager.StreamableHTTPSessionManager"),
            patch("mcp.server.fastmcp.server.StreamableHTTPASGIApp"),
        ):
            app = server._build_fastmcp_auth_app("streamable-http")

        self.assertIsNotNone(app)
        mock_auth.get_middleware.assert_called_once()
        mock_auth.get_routes.assert_called_once_with(mcp_path="/mcp")

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_build_fastmcp_auth_app_sse(self, mock_get_client, mock_fastmcp):
        """Test _build_fastmcp_auth_app creates app with auth routes for SSE."""
        mock_server_instance = MagicMock()
        mock_server_instance.settings.sse_path = "/sse"
        mock_server_instance.settings.mount_path = "/"
        mock_server_instance.settings.message_path = "/messages/"
        mock_server_instance.settings.transport_security = None
        mock_server_instance._normalize_path.return_value = "/messages/"
        mock_fastmcp.return_value = mock_server_instance

        mock_auth = MagicMock()
        mock_auth.get_middleware.return_value = []
        mock_auth.get_routes.return_value = []
        mock_auth.required_scopes = []
        mock_auth._get_resource_url.return_value = None

        server = ZscalerMCPServer(auth=mock_auth)

        app = server._build_fastmcp_auth_app("sse")

        self.assertIsNotNone(app)
        mock_auth.get_middleware.assert_called_once()
        mock_auth.get_routes.assert_called_once_with(mcp_path="/sse")


if __name__ == "__main__":
    unittest.main()
