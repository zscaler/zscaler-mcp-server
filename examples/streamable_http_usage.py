#!/usr/bin/env python3
"""
Streamable HTTP transport example for Zscaler Integrations MCP Server.

This script demonstrates how to initialize and run the Zscaler Integrations MCP Server
with streamable-http transport for custom integrations and web-based deployments.
"""

import os

from dotenv import load_dotenv

from zscaler_mcp.server import ZscalerMCPServer


def main():
    """Run the Zscaler Integrations MCP Server with streamable-http transport."""
    # Load environment variables from .env file
    load_dotenv()

    # Create and run the server with streamable-http transport
    server = ZscalerMCPServer(
        # Optional: Override credentials from environment variables
        # client_id="your_client_id",
        # client_secret="your_client_secret",
        # customer_id="your_customer_id",
        # vanity_domain="your_vanity_domain",
        # cloud="beta",
        debug=os.environ.get("ZSCALER_MCP_DEBUG", "").lower() == "true",
        enabled_services={"zia", "zpa", "zdx", "zcc"},  # Optional: enable specific services
        user_agent_comment="Streamable HTTP Example"  # Optional: custom User-Agent
    )

    # Example 1: Run with default settings (port 8000, localhost)
    print("Example 1: Default streamable-http configuration")
    print("  - Host: 127.0.0.1 (localhost only)")
    print("  - Port: 8000")
    print("  - Path: /mcp")
    print("  - URL: http://127.0.0.1:8000/mcp")
    print()

    # Uncomment to run with defaults:
    # server.run("streamable-http")

    # Example 2: Custom configuration
    print("Example 2: Custom configuration")
    print("  - Host: 0.0.0.0 (external access)")
    print("  - Port: 8080")
    print("  - URL: http://0.0.0.0:8080/mcp")
    print()

    # Run with custom requirements
    server.run("streamable-http", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
