"""Concrete MCP prompt catalog.

Every module under this package registers one or more prompts via the ``@prompt``
decorator. :func:`zscaler_mcp.prompts.discovery.discover_prompts` walks this tree at
server startup. Grouped by service, mirroring ``zscaler_mcp.tools``.
"""
