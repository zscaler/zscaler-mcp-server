"""
Tests for the Zscaler Integrations MCP Server.
"""

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
        server = ZscalerMCPServer(
            enabled_services={"zpa"},
            enabled_tools={"zpa_app_segments"}
        )

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

        # Verify result matches registry
        self.assertEqual(set(result["services"]), set(expected_services))

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
            user_agent_comment="test_comment"
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
        with patch.dict(services._AVAILABLE_SERVICES, {  # pylint: disable=protected-access
            "test_service": MagicMock(side_effect=Exception("Service init failed"))
        }):
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
        with patch.object(server.server, 'run') as mock_run:
            server.run("stdio")
            mock_run.assert_called_once_with("stdio")

        # Test sse transport
        with patch("zscaler_mcp.server.uvicorn.run") as mock_uvicorn_run:
            server.run("sse", host="0.0.0.0", port=8080)
            mock_uvicorn_run.assert_called_once()

        # Test streamable-http transport
        with patch("zscaler_mcp.server.uvicorn.run") as mock_uvicorn_run:
            server.run("streamable-http", host="0.0.0.0", port=8080)
            mock_uvicorn_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
