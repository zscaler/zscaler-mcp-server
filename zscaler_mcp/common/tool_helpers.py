"""Helper functions for tool registration."""

from typing import Callable, Dict, List, Optional, Set
from mcp.types import ToolAnnotations
from zscaler_mcp.common.logging import get_logger

logger = get_logger(__name__)


def register_read_tools(
    server,
    tools: List[Dict[str, any]],
    enabled_tools: Optional[Set[str]] = None
) -> int:
    """Register read-only tools.
    
    Read-only tools are always registered regardless of write mode settings.
    These tools perform safe operations that only retrieve information.
    
    Args:
        server: The MCP server instance
        tools: List of tool definitions with 'func', 'name', 'description'
        enabled_tools: Set of enabled tool names (if None, all tools are enabled)
        
    Returns:
        Number of tools registered
        
    Example:
        read_tools = [
            {
                "func": zpa_list_application_segments,
                "name": "zpa_list_application_segments",
                "description": "List ZPA application segments (read-only)"
            }
        ]
        count = register_read_tools(server, read_tools)
    """
    count = 0
    for tool_def in tools:
        tool_name = tool_def["name"]
        
        # Skip if not in enabled_tools (when enabled_tools is specified)
        if enabled_tools and tool_name not in enabled_tools:
            logger.debug(f"Skipping read tool (not enabled): {tool_name}")
            continue
            
        server.add_tool(
            tool_def["func"],
            name=tool_name,
            description=tool_def["description"],
            annotations=ToolAnnotations(readOnlyHint=True)  # Mark as read-only for AI agent permission frameworks
        )
        logger.debug(f"✅ Registered read-only tool: {tool_name}")
        count += 1
    
    return count


def register_write_tools(
    server,
    tools: List[Dict[str, any]],
    enabled_tools: Optional[Set[str]] = None,
    enable_write_tools: bool = False
) -> int:
    """Register write tools (only if enable_write_tools is True).
    
    Write tools are only registered when explicitly enabled via the
    --enable-write-tools flag. This provides a critical safety layer
    to prevent accidental modifications in autonomous agent scenarios.
    
    Args:
        server: The MCP server instance
        tools: List of tool definitions with 'func', 'name', 'description'
        enabled_tools: Set of enabled tool names (if None, all tools are enabled)
        enable_write_tools: Enable write operations (default: False)
        
    Returns:
        Number of tools registered
        
    Example:
        write_tools = [
            {
                "func": zpa_create_application_segment,
                "name": "zpa_create_application_segment",
                "description": "Create a new ZPA application segment (write operation)"
            }
        ]
        count = register_write_tools(server, write_tools, enable_write_tools=True)
    """
    if not enable_write_tools:
        logger.info(f"🔒 Write tools disabled - skipping {len(tools)} write tools for safety")
        logger.info("   To enable write operations, use --enable-write-tools flag")
        return 0
    
    logger.warning(f"⚠️  Write tools enabled - registering {len(tools)} write tools")
    
    count = 0
    for tool_def in tools:
        tool_name = tool_def["name"]
        
        # Skip if not in enabled_tools (when enabled_tools is specified)
        if enabled_tools and tool_name not in enabled_tools:
            logger.debug(f"Skipping write tool (not enabled): {tool_name}")
            continue
            
        server.add_tool(
            tool_def["func"],
            name=tool_name,
            description=tool_def["description"],
            annotations=ToolAnnotations(destructiveHint=True)  # Mark as destructive/write operation for AI agent permission frameworks
        )
        logger.debug(f"⚠️  Registered write tool: {tool_name}")
        count += 1
    
    return count

