"""
Tests for streamable-http transport functionality.
"""

import unittest
from unittest.mock import MagicMock, patch

from zscaler_mcp.server import ZscalerMCPServer


class TestStreamableHttpTransport(unittest.TestCase):
    """Test cases for streamable-http transport."""

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_streamable_http_transport_initialization(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test streamable-http transport initialization."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_app = MagicMock()
        mock_server_instance.streamable_http_app.return_value = mock_app
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(debug=True)

        # Test streamable-http transport
        server.run("streamable-http", host="0.0.0.0", port=8080)

        # Verify uvicorn was called with correct parameters
        mock_uvicorn.run.assert_called_once_with(
            mock_app, host="0.0.0.0", port=8080, log_level="debug"
        )

        # Verify streamable_http_app was called
        mock_server_instance.streamable_http_app.assert_called_once()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_streamable_http_default_parameters(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test streamable-http transport with default parameters."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_app = MagicMock()
        mock_server_instance.streamable_http_app.return_value = mock_app
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(debug=False)

        # Test streamable-http transport with defaults
        server.run("streamable-http")

        # Verify uvicorn was called with default parameters
        mock_uvicorn.run.assert_called_once_with(
            mock_app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_non_streamable_http_transport_unchanged(
        self,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test that non-streamable-http transports use the original method."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer()

        # Test stdio transport (should use original method)
        server.run("stdio")

        # Verify the original run method was called
        mock_server_instance.run.assert_called_once_with("stdio")

        # Verify streamable_http_app was NOT called
        mock_server_instance.streamable_http_app.assert_not_called()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_streamable_http_custom_parameters(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test streamable-http transport with custom parameters."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_app = MagicMock()
        mock_server_instance.streamable_http_app.return_value = mock_app
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(debug=True)

        # Test streamable-http transport with custom parameters
        server.run("streamable-http", host="192.168.1.100", port=9000)

        # Verify uvicorn was called with custom parameters
        mock_uvicorn.run.assert_called_once_with(
            mock_app,
            host="192.168.1.100",
            port=9000,
            log_level="debug",
        )

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_streamable_http_logging_levels(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test streamable-http transport logging level configuration."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_app = MagicMock()
        mock_server_instance.streamable_http_app.return_value = mock_app
        mock_fastmcp.return_value = mock_server_instance

        # Test with debug=True
        server_debug = ZscalerMCPServer(debug=True)
        server_debug.run("streamable-http")

        # Verify debug log level
        mock_uvicorn.run.assert_called_with(
            mock_app,
            host="127.0.0.1",
            port=8000,
            log_level="debug",
        )

        # Reset mock
        mock_uvicorn.reset_mock()

        # Test with debug=False
        server_info = ZscalerMCPServer(debug=False)
        server_info.run("streamable-http")

        # Verify info log level
        mock_uvicorn.run.assert_called_with(
            mock_app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_sse_transport_initialization(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test SSE transport initialization."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_app = MagicMock()
        mock_server_instance.sse_app.return_value = mock_app
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(debug=True)

        # Test SSE transport
        server.run("sse", host="0.0.0.0", port=8080)

        # Verify uvicorn was called with correct parameters
        mock_uvicorn.run.assert_called_once_with(
            mock_app, host="0.0.0.0", port=8080, log_level="debug"
        )

        # Verify sse_app was called
        mock_server_instance.sse_app.assert_called_once()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_sse_transport_default_parameters(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test SSE transport with default parameters."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_app = MagicMock()
        mock_server_instance.sse_app.return_value = mock_app
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(debug=False)

        # Test SSE transport with defaults
        server.run("sse")

        # Verify uvicorn was called with default parameters
        mock_uvicorn.run.assert_called_once_with(
            mock_app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_sse_transport_custom_parameters(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test SSE transport with custom parameters."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_app = MagicMock()
        mock_server_instance.sse_app.return_value = mock_app
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(debug=True)

        # Test SSE transport with custom parameters
        server.run("sse", host="10.0.0.1", port=9090)

        # Verify uvicorn was called with custom parameters
        mock_uvicorn.run.assert_called_once_with(
            mock_app,
            host="10.0.0.1",
            port=9090,
            log_level="debug",
        )

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    def test_stdio_transport_uses_original_method(
        self,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test that stdio transport uses the original FastMCP run method."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer()

        # Test stdio transport
        server.run("stdio")

        # Verify the original run method was called
        mock_server_instance.run.assert_called_once_with("stdio")

        # Verify HTTP-specific methods were NOT called
        mock_server_instance.streamable_http_app.assert_not_called()
        mock_server_instance.sse_app.assert_not_called()

    @patch("zscaler_mcp.server.FastMCP")
    @patch("zscaler_mcp.client.get_zscaler_client")
    @patch("zscaler_mcp.server.uvicorn")
    def test_transport_methods_dont_interfere(
        self,
        mock_uvicorn,
        mock_get_client,
        mock_fastmcp,
    ):
        """Test that different transport methods don't interfere with each other."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        mock_server_instance = MagicMock()
        mock_streamable_app = MagicMock()
        mock_sse_app = MagicMock()
        mock_server_instance.streamable_http_app.return_value = mock_streamable_app
        mock_server_instance.sse_app.return_value = mock_sse_app
        mock_fastmcp.return_value = mock_server_instance

        # Create server
        server = ZscalerMCPServer(debug=True)

        # Test streamable-http transport
        server.run("streamable-http", host="0.0.0.0", port=8080)
        mock_uvicorn.run.assert_called_with(
            mock_streamable_app, host="0.0.0.0", port=8080, log_level="debug"
        )

        # Reset mock
        mock_uvicorn.reset_mock()

        # Test SSE transport
        server.run("sse", host="0.0.0.0", port=8080)
        mock_uvicorn.run.assert_called_with(
            mock_sse_app, host="0.0.0.0", port=8080, log_level="debug"
        )

        # Verify correct apps were called
        mock_server_instance.streamable_http_app.assert_called_once()
        mock_server_instance.sse_app.assert_called_once()


if __name__ == "__main__":
    unittest.main()
