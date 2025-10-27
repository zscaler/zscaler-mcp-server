"""Helper functions for tool registration."""

import fnmatch
from typing import Dict, List, Optional, Set

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
    enable_write_tools: bool = False,
    write_tools: Optional[Set[str]] = None
) -> int:
    """Register write tools (only if enable_write_tools is True).
    
    Write tools are only registered when explicitly enabled via the
    --enable-write-tools flag. When write_tools allowlist is provided,
    only tools matching the allowlist patterns will be registered.
    This provides defense-in-depth security.
    
    Args:
        server: The MCP server instance
        tools: List of tool definitions with 'func', 'name', 'description'
        enabled_tools: Set of enabled tool names (if None, all tools are enabled)
        enable_write_tools: Enable write operations (default: False)
        write_tools: Explicit allowlist of write tools (supports wildcards like 'zpa_create_*')
        
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
        # Register all write tools
        count = register_write_tools(server, write_tools, enable_write_tools=True)
        
        # Register only allowlisted write tools
        count = register_write_tools(server, write_tools, enable_write_tools=True, 
                                     write_tools={'zpa_create_*', 'zpa_delete_*'})
    """
    if not enable_write_tools:
        logger.info(f"🔒 Write tools disabled - skipping {len(tools)} write tools for safety")
        logger.info("   To enable write operations, use --enable-write-tools flag")
        return 0
    
    # Allowlist is MANDATORY when write tools are enabled
    if not write_tools or len(write_tools) == 0:
        logger.warning("⚠️  SECURITY: --enable-write-tools flag is set")
        logger.warning("⚠️  However, NO write tools allowlist specified (--write-tools)")
        logger.warning("⚠️  For security, 0 write tools will be registered")
        logger.info(f"🔒 Blocked {len(tools)} write tools (allowlist required)")
        logger.info("   To enable specific write tools, use: --write-tools 'pattern1,pattern2'")
        logger.info("   Example: --write-tools 'zpa_create_*,zia_delete_*'")
        return 0
    
    # Explicit allowlist is active
    logger.warning(f"⚠️  Write tools enabled with explicit allowlist ({len(write_tools)} patterns)")
    logger.warning(f"⚠️  Allowlist patterns: {', '.join(sorted(write_tools))}")
    
    count = 0
    skipped = 0
    
    for tool_def in tools:
        tool_name = tool_def["name"]
        
        # Skip if not in enabled_tools (when enabled_tools is specified)
        if enabled_tools and tool_name not in enabled_tools:
            logger.debug(f"Skipping write tool (not in enabled_tools): {tool_name}")
            continue
        
        # Check write_tools allowlist (supports wildcards)
        if write_tools:
            # Check if tool matches any pattern in the allowlist
            matched = any(fnmatch.fnmatch(tool_name, pattern) for pattern in write_tools)
            
            if not matched:
                logger.debug(f"🔒 Skipping write tool (not in allowlist): {tool_name}")
                skipped += 1
                continue
            else:
                logger.debug(f"✅ Tool matches allowlist: {tool_name}")
            
        server.add_tool(
            tool_def["func"],
            name=tool_name,
            description=tool_def["description"],
            annotations=ToolAnnotations(destructiveHint=True)  # Mark as destructive/write operation for AI agent permission frameworks
        )
        logger.debug(f"⚠️  Registered write tool: {tool_name}")
        count += 1
    
    if write_tools and skipped > 0:
        logger.info(f"🔒 Security: {skipped} write tools blocked by allowlist, {count} allowed")
    
    return count

