"""
Zscaler MCP Server - Main entry point

This module provides the main server class for the Zscaler MCP server
and serves as the entry point for the application.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

import asyncio
from .registry import register_all_tools
from . import app  # relative import since app is in the same package
from typing import Dict, List, Optional, Set

register_all_tools(app)

async def _run():
    print("🚀 Initializing Zscaler MCP Server...", file=sys.stderr, flush=True)
    await app.run_stdio_async()

def cli_entry():
    asyncio.run(_run())

# class ZscalerMCPServer:
#     """Main server class for the Zscaler MCP server."""

#     def __init__(
#         self,
#         debug: bool = False,
#         enabled_modules: Optional[Set[str]] = None,
#         user_agent_comment: Optional[str] = None,
#     ):