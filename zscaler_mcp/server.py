"""
Zscaler Integrations MCP Server - Main entry point

This module provides the main server class for the Zscaler Integrations MCP Server
and serves as the entry point for the application.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional, Set

import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from zscaler_mcp import services
from zscaler_mcp.common.logging import configure_logging, get_logger

# Import version from package metadata
try:
    from importlib.metadata import version
    __version__ = version("zscaler-mcp")
except ImportError:
    # Fallback for Python < 3.8
    try:
        from importlib_metadata import version
        __version__ = version("zscaler-mcp")
    except ImportError:
        # Final fallback - read from pyproject.toml or use a default
        __version__ = "0.2.2"

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)


class ZscalerMCPServer:
    """Main server class for the Zscaler Integrations MCP Server."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        customer_id: Optional[str] = None,
        vanity_domain: Optional[str] = None,
        cloud: Optional[str] = None,
        debug: bool = False,
        enabled_services: Optional[Set[str]] = None,
        enabled_tools: Optional[Set[str]] = None,
        user_agent_comment: Optional[str] = None,
        enable_write_tools: bool = False,
        write_tools: Optional[Set[str]] = None,
    ):
        """Initialize the Zscaler Integrations MCP Server.

        Args:
            client_id: Zscaler OAuth client ID
            client_secret: Zscaler OAuth client secret
            customer_id: Zscaler customer ID
            vanity_domain: Zscaler vanity domain
            cloud: Zscaler cloud environment (e.g., 'beta', 'zscalertwo')
            debug: Enable debug logging
            enabled_services: Set of service names to enable (defaults to all services)
            enabled_tools: Set of tool names to enable (defaults to all tools)
            user_agent_comment: Additional information to include in the User-Agent comment section
            enable_write_tools: Enable write operations (create, update, delete). Default: False for safety.
            write_tools: Explicit allowlist of write tools to enable. Supports wildcards. Requires enable_write_tools=True.
        """
        # Store configuration
        self.client_id = client_id
        self.client_secret = client_secret
        self.customer_id = customer_id
        self.vanity_domain = vanity_domain
        self.cloud = cloud
        self.debug = debug
        self.user_agent_comment = user_agent_comment

        self.enabled_services = enabled_services or set(services.get_service_names())
        self.enabled_tools = enabled_tools or set()
        self.enable_write_tools = enable_write_tools
        self.write_tools = write_tools  # Explicit allowlist for write tools

        # Configure logging - use stderr for stdio transport to avoid interfering with MCP protocol
        configure_logging(debug=self.debug, use_stderr=True)
        logger = get_logger(__name__)
        
        # Log security posture
        logger.info("Initializing Zscaler Integrations MCP Server")
        if self.enable_write_tools:
            logger.warning("=" * 80)
            logger.warning("⚠️  WRITE TOOLS MODE ENABLED")
            if self.write_tools:
                logger.warning("⚠️  Explicit allowlist provided - only listed write tools will be registered")
                logger.warning(f"⚠️  Allowed patterns: {', '.join(sorted(self.write_tools))}")
                logger.warning("⚠️  Server can CREATE, MODIFY, and DELETE Zscaler resources")
                logger.warning("⚠️  Ensure this is intentional and appropriate for your use case")
            else:
                logger.warning("⚠️  NO allowlist provided - 0 write tools will be registered")
                logger.warning("⚠️  Read-only tools will still be available")
                logger.warning("⚠️  To enable write operations, add: --write-tools 'pattern'")
            logger.warning("=" * 80)
        else:
            logger.info("=" * 80)
            logger.info("🔒 Server running in READ-ONLY mode (safe default)")
            logger.info("   Only list and get operations are available")
            logger.info("   To enable write operations, use --enable-write-tools AND --write-tools flags")
            logger.info("=" * 80)

        # Don't initialize the Zscaler client during server startup to avoid pickle issues
        # Clients will be created on-demand when tools are called
        self.zscaler_client = None
        logger.info("Client initialization deferred to tool execution")

        # Initialize the MCP server
        self.server = FastMCP(
            name="Zscaler Integrations MCP Server",
            instructions="This server provides access to Zscaler capabilities across ZIA, ZPA, ZDX, ZCC and ZIdentity services.",
            debug=self.debug,
            log_level="DEBUG" if self.debug else "INFO",
        )

        # Initialize and register services
        self.services = {}
        available_services = services.get_available_services()
        for service_name in self.enabled_services:
            if service_name in available_services:
                service_class = available_services[service_name]
                # Pass None as client - tools will create their own clients on-demand
                self.services[service_name] = service_class(None)
                logger.debug("Initialized service: %s", service_name)

        # Register tools and resources from services
        tool_count = self._register_tools()
        tool_word = "tool" if tool_count == 1 else "tools"

        resource_count = self._register_resources()
        resource_word = "resource" if resource_count == 1 else "resources"

        # Count services and tools with proper grammar
        service_count = len(self.services)
        service_word = "service" if service_count == 1 else "services"

        logger.info(
            "Initialized %d %s with %d %s and %d %s",
            service_count,
            service_word,
            tool_count,
            tool_word,
            resource_count,
            resource_word,
        )

    def _register_tools(self) -> int:
        """Register tools from all services.

        Returns:
            int: Number of tools registered
        """
        # Register core tools directly
        self.server.add_tool(
            self.zscaler_check_connectivity,
            name="zscaler_check_connectivity",
            description="Check connectivity to the Zscaler API.",
            annotations=ToolAnnotations(readOnlyHint=True)  # Read-only diagnostic tool
        )

        self.server.add_tool(
            self.get_available_services,
            name="zscaler_get_available_services",
            description="Get information about available services.",
            annotations=ToolAnnotations(readOnlyHint=True)  # Read-only informational tool
        )

        tool_count = 2  # the tools added above

        # Register tools from services
        for service in self.services.values():
            try:
                # Register tools with write mode flag and allowlist
                if self.enabled_tools:
                    service.register_tools(
                        self.server,
                        enabled_tools=self.enabled_tools,
                        enable_write_tools=self.enable_write_tools,
                        write_tools=self.write_tools
                    )
                else:
                    service.register_tools(
                        self.server,
                        enable_write_tools=self.enable_write_tools,
                        write_tools=self.write_tools
                    )
                
                # Count tools (read + write)
                if hasattr(service, "read_tools"):
                    tool_count += len(service.read_tools)
                if hasattr(service, "write_tools") and self.enable_write_tools:
                    tool_count += len(service.write_tools)
                elif hasattr(service, "tools"):
                    # Fallback for services not yet migrated
                    tool_count += len(service.tools)
            except Exception as e:
                logger.warning(f"Failed to register tools for service: {e}")
                # Still count the tools even if registration fails
                if hasattr(service, "read_tools"):
                    tool_count += len(service.read_tools)
                if hasattr(service, "write_tools"):
                    tool_count += len(service.write_tools)
                elif hasattr(service, "tools"):
                    tool_count += len(service.tools)

        return tool_count

    def _register_resources(self) -> int:
        """Register resources from all services.

        Returns:
            int: Number of resources registered
        """
        # Register resources from services
        for service in self.services.values():
            # Check if the service has a register_resources method
            if hasattr(service, "register_resources") and callable(
                service.register_resources
            ):
                service.register_resources(self.server)

        # Count resources from services
        resource_count = 0
        for service in self.services.values():
            if hasattr(service, "resources"):
                resource_count += len(service.resources)
        return resource_count

    def zscaler_check_connectivity(self) -> Dict[str, bool]:
        """Check connectivity to the Zscaler API.

        Returns:
            Dict[str, bool]: Connectivity status
        """
        try:
            # Try to make a simple API call to test connectivity
            # This is a placeholder - you might want to implement a specific test
            return {"connected": True}
        except Exception as e:
            logger.error("Connectivity check failed: %s", e)
            return {"connected": False}

    def get_available_services(self) -> Dict[str, List[str]]:
        """Get information about available services.

        Returns:
            Dict[str, List[str]]: Available services
        """
        return {"services": services.get_service_names()}

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        """Run the MCP server.

        Args:
            transport: Transport protocol to use ("stdio", "sse", or "streamable-http")
            host: Host to bind to for HTTP transports (default: 127.0.0.1)
            port: Port to listen on for HTTP transports (default: 8000)
        """
        if transport == "streamable-http":
            # For streamable-http, use uvicorn directly for custom host/port
            logger.info("Starting streamable-http server on %s:%d", host, port)

            # Get the ASGI app from FastMCP (handles /mcp path automatically)
            app = self.server.streamable_http_app()

            # Run with uvicorn for custom host/port configuration
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info" if not self.debug else "debug",
            )
        elif transport == "sse":
            # For sse, use uvicorn directly for custom host/port (same pattern as streamable-http)
            logger.info("Starting sse server on %s:%d", host, port)

            # Get the ASGI app from FastMCP
            app = self.server.sse_app()

            # Run with uvicorn for custom host/port configuration
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info" if not self.debug else "debug",
            )
        else:
            # For stdio, use the default FastMCP run method (no host/port needed)
            self.server.run(transport)


def list_available_tools(selected_services=None, enabled_tools=None):
    """Print all available tool metadata names and descriptions, optionally filtered by services and tools."""
    from zscaler_mcp import services as svc_mod

    available_services = svc_mod.get_available_services()
    if selected_services:
        available_services = {
            k: v for k, v in available_services.items() if k in selected_services
        }
    logger.info("Available tools:")
    for service_name, service_class in available_services.items():
        service = service_class(None)
        # Get tool metadata from the service's register_tools method
        if hasattr(service, "tools") and hasattr(service, "register_tools"):
            # Create a mock server to capture the tool metadata
            class MockServer:
                def __init__(self):
                    self.tools = []

                def add_tool(self, tool, name=None, description=None, annotations=None):
                    self.tools.append(
                        {
                            "tool": tool,
                            "name": name or tool.__name__,
                            "description": description or (tool.__doc__ or ""),
                            "annotations": annotations,
                        }
                    )

            mock_server = MockServer()
            service.register_tools(mock_server, enabled_tools=enabled_tools)

            for tool_info in mock_server.tools:
                logger.info(
                    f"  [{service_name}] {tool_info['name']}: {tool_info['description']}"
                )


def parse_services_list(services_string):
    """Parse and validate comma-separated service list.

    Args:
        services_string: Comma-separated string of service names

    Returns:
        List of validated service names (returns all available services if empty string)

    Raises:
        argparse.ArgumentTypeError: If any service names are invalid
    """
    # Get available services
    available_services = services.get_service_names()

    # If empty string, return all available services (default behavior)
    if not services_string:
        return available_services

    # Split by comma and clean up whitespace
    service_list = [s.strip() for s in services_string.split(",") if s.strip()]

    # Validate against available services
    invalid_services = [s for s in service_list if s not in available_services]
    if invalid_services:
        raise argparse.ArgumentTypeError(
            f"Invalid services: {', '.join(invalid_services)}. "
            f"Available services: {', '.join(available_services)}"
        )

    return service_list


def parse_tools_list(tools_string):
    """Parse and validate comma-separated tool list.

    Args:
        tools_string: Comma-separated string of tool names

    Returns:
        List of validated tool names (returns empty list if empty string)

    Raises:
        argparse.ArgumentTypeError: If any tool names are invalid
    """
    # If empty string, return empty list (no tools selected)
    if not tools_string:
        return []

    # Split by comma and clean up whitespace
    tool_list = [t.strip() for t in tools_string.split(",") if t.strip()]

    # Get all available tools from all services for validation
    available_services = services.get_available_services()
    all_available_tools = []

    for service_name, service_class in available_services.items():
        service_instance = service_class(None)  # Create instance to get tools

        # Create a mock server to capture the tool metadata names
        class MockServer:
            def __init__(self):
                self.tools = []

            def add_tool(self, tool, name=None, description=None, annotations=None):
                self.tools.append(
                    {
                        "tool": tool,
                        "name": name or tool.__name__,
                        "description": description or (tool.__doc__ or ""),
                        "annotations": annotations,
                    }
                )

        mock_server = MockServer()
        service_instance.register_tools(mock_server)

        for tool_info in mock_server.tools:
            all_available_tools.append(tool_info["name"])

    # Validate against available tools
    invalid_tools = [t for t in tool_list if t not in all_available_tools]
    if invalid_tools:
        raise argparse.ArgumentTypeError(
            f"Invalid tools: {', '.join(invalid_tools)}. "
            f"Available tools: {', '.join(all_available_tools)}"
        )

    return tool_list


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Zscaler Integrations MCP Server")

    # Transport options
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("ZSCALER_MCP_TRANSPORT", "stdio"),
        help="Transport protocol to use (default: stdio, env: ZSCALER_MCP_TRANSPORT)",
    )

    # Service selection
    available_services = services.get_service_names()

    parser.add_argument(
        "--services",
        "-s",
        type=parse_services_list,
        default=parse_services_list(os.environ.get("ZSCALER_MCP_SERVICES", "")),
        metavar="SERVICE1,SERVICE2,...",
        help=f"Comma-separated list of services to enable. Available: [{', '.join(available_services)}] "
        f"(default: all services, env: ZSCALER_MCP_SERVICES)",
    )

    # Tool selection
    parser.add_argument(
        "--tools",
        type=parse_tools_list,
        default=parse_tools_list(os.environ.get("ZSCALER_MCP_TOOLS", "")),
        metavar="TOOL1,TOOL2,...",
        help="Comma-separated list of specific tools to enable (if not specified, all tools from selected services are enabled, env: ZSCALER_MCP_TOOLS)",
    )

    # Debug mode
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        default=os.environ.get("ZSCALER_MCP_DEBUG", "").lower() == "true",
        help="Enable debug logging (env: ZSCALER_MCP_DEBUG)",
    )

    # Write tools enablement (NEW)
    parser.add_argument(
        "--enable-write-tools",
        action="store_true",
        default=os.environ.get("ZSCALER_MCP_WRITE_ENABLED", "").lower() == "true",
        help="Enable write operations (create, update, delete). "
             "By default, only read-only operations are available for safety. "
             "(env: ZSCALER_MCP_WRITE_ENABLED)",
    )

    parser.add_argument(
        "--write-tools",
        default=os.environ.get("ZSCALER_MCP_WRITE_TOOLS"),
        help="Comma-separated list of write tools to explicitly allow. "
             "Supports wildcards (e.g., 'zpa_create_*,zpa_delete_*'). "
             "Requires --enable-write-tools to be set. "
             "(env: ZSCALER_MCP_WRITE_TOOLS)",
    )

    # Zscaler API configuration
    parser.add_argument(
        "--client-id",
        default=os.environ.get("ZSCALER_CLIENT_ID"),
        help="Zscaler OAuth client ID (env: ZSCALER_CLIENT_ID)",
    )

    parser.add_argument(
        "--client-secret",
        default=os.environ.get("ZSCALER_CLIENT_SECRET"),
        help="Zscaler OAuth client secret (env: ZSCALER_CLIENT_SECRET)",
    )

    parser.add_argument(
        "--customer-id",
        default=os.environ.get("ZSCALER_CUSTOMER_ID"),
        help="Zscaler customer ID (env: ZSCALER_CUSTOMER_ID)",
    )

    parser.add_argument(
        "--vanity-domain",
        default=os.environ.get("ZSCALER_VANITY_DOMAIN"),
        help="Zscaler vanity domain (env: ZSCALER_VANITY_DOMAIN)",
    )

    parser.add_argument(
        "--cloud",
        default=os.environ.get("ZSCALER_CLOUD"),
        help="Zscaler cloud environment (env: ZSCALER_CLOUD)",
    )

    # HTTP transport configuration
    parser.add_argument(
        "--host",
        default=os.environ.get("ZSCALER_MCP_HOST", "127.0.0.1"),
        help="Host to bind to for HTTP transports (default: 127.0.0.1, env: ZSCALER_MCP_HOST)",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.environ.get("ZSCALER_MCP_PORT", "8000")),
        help="Port to listen on for HTTP transports (default: 8000, env: ZSCALER_MCP_PORT)",
    )

    parser.add_argument(
        "--user-agent-comment",
        default=os.environ.get("ZSCALER_MCP_USER_AGENT_COMMENT"),
        help="Additional information to include in the User-Agent comment section (env: ZSCALER_MCP_USER_AGENT_COMMENT)",
    )

    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tool names and descriptions, then exit.",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"Zscaler MCP Server version {__version__}",
        help="Show version information and exit.",
    )

    return parser.parse_args()


def main():
    """Main entry point for the Zscaler Integrations MCP Server."""
    # Load environment variables
    load_dotenv()

    # Parse command line arguments (includes environment variable defaults)
    args = parse_args()

    if getattr(args, "list_tools", False):
        list_available_tools(
            selected_services=args.services,
            enabled_tools=set(args.tools) if args.tools else None,
        )
        sys.exit(0)

    try:
        # Parse write_tools into a set
        write_tools = None
        if args.write_tools:
            write_tools = set(t.strip() for t in args.write_tools.split(","))
        
        # Create and run the server
        server = ZscalerMCPServer(
            client_id=args.client_id,
            client_secret=args.client_secret,
            customer_id=args.customer_id,
            vanity_domain=args.vanity_domain,
            cloud=args.cloud,
            debug=args.debug,
            enabled_services=set(args.services),
            enabled_tools=set(args.tools),
            user_agent_comment=args.user_agent_comment,
            enable_write_tools=args.enable_write_tools,
            write_tools=write_tools,
        )
        logger.info("Starting server with %s transport", args.transport)
        server.run(args.transport, host=args.host, port=args.port)
    except RuntimeError as e:
        logger.error("Runtime error: %s", e)
        sys.exit(1)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        # Catch any other exceptions to ensure graceful shutdown
        logger.error("Unexpected error running server: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
