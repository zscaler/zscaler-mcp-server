#!/usr/bin/env python3
"""
SSE transport example for Zscaler MCP Server.

This script demonstrates how to initialize and run the Zscaler MCP Server
with Server-Sent Events (SSE) transport.
"""

import os

from dotenv import load_dotenv

from zscaler_mcp.server import ZscalerMCPServer


def main():
    """Run the Zscaler MCP Server with SSE transport."""
    # Load environment variables from .env file
    load_dotenv()

    # Create and run the server with SSE transport
    server = ZscalerMCPServer(
        # Optional: Override credentials from environment variables
        # client_id="your_client_id",
        # client_secret="your_client_secret", 
        # customer_id="your_customer_id",
        # vanity_domain="your_vanity_domain",
        # cloud="beta",
        debug=os.environ.get("ZSCALER_MCP_DEBUG", "").lower() == "true",
        enabled_services={"zia", "zpa"},  # Optional: enable specific services
        user_agent_comment="SSE Usage Example"  # Optional: custom User-Agent
    )

    # Run the server with SSE transport
    server.run("sse")


if __name__ == "__main__":
    main()
