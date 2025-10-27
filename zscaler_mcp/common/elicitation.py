"""Confirmation prompts for write operations.

This module provides a simpler confirmation system for write operations,
adding an additional security layer for create, update, and delete actions.

Instead of complex MCP elicitation protocol, we add a `confirmed` parameter
to all write tools. The AI agent must explicitly pass confirmed=True after
getting user approval.
"""

import json
import os
from typing import Any, Dict

from zscaler_mcp.common.logging import get_logger

logger = get_logger(__name__)


def extract_confirmed_from_kwargs(kwargs_value: Any) -> bool:
    """Extract confirmed value from kwargs parameter (handles both dict and JSON string).
    
    In MCP/FastMCP context, **kwargs is treated as a literal parameter that may receive:
    - A dict: {"confirmed": True}
    - A JSON string: '{"confirmed": true}'
    - An empty string/dict: "" or {}
    
    Args:
        kwargs_value: The value passed as the kwargs parameter
        
    Returns:
        bool: The confirmed value (defaults to False if not found)
    """
    if isinstance(kwargs_value, dict):
        return kwargs_value.get("confirmed", False)
    
    if isinstance(kwargs_value, str):
        if not kwargs_value or kwargs_value == "{}":
            return False
        try:
            parsed = json.loads(kwargs_value)
            if isinstance(parsed, dict):
                # Check for various spellings AI might use
                return parsed.get("confirmed", parsed.get("confirm", False))
        except (json.JSONDecodeError, ValueError):
            return False
    
    return False


def should_skip_confirmations() -> bool:
    """Check if confirmations should be skipped (for automation/CI/CD)."""
    return os.environ.get("ZSCALER_MCP_SKIP_CONFIRMATIONS", "").lower() == "true"


def generate_confirmation_message(tool_name: str, params: Dict[str, Any]) -> str:
    """Generate a user-friendly confirmation message.
    
    This message is returned when a write operation is called without confirmation.
    The AI agent should present this to the user and retry with confirmed=True.
    
    Args:
        tool_name: Name of the tool being called
        params: Tool parameters (excluding 'confirmed')
        
    Returns:
        Formatted confirmation message
    """
    # Remove internal/confirmation parameters from display
    display_params = {k: v for k, v in params.items() 
                     if k not in ["confirmed", "use_legacy", "service"] and not k.startswith("_")}
    
    # Determine operation type and generate appropriate message
    if "delete_" in tool_name:
        resource_type = tool_name.replace("delete_", "").replace("_", " ").title()
        resource_id = params.get("id") or params.get("name") or "unknown"
        
        return (
            f"⚠️  DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: DELETE {resource_type}\n"
            f"Resource ID/Name: {resource_id}\n\n"
            f"⚠️  WARNING: This action CANNOT be undone!\n\n"
            f"To proceed, please confirm that you want to delete this resource.\n"
            f"To proceed, retry this tool call with: kwargs='{{\"confirmed\": true}}'"
        )
    
    elif "create_" in tool_name:
        resource_type = tool_name.replace("create_", "").replace("_", " ").title()
        name = params.get("name") or "new resource"
        
        msg = (
            f"📝 CREATE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: CREATE {resource_type}\n"
            f"Resource Name: {name}\n"
        )
        
        # Add key configuration parameters
        if len(display_params) > 1:
            msg += "\nConfiguration:\n"
            for key, value in list(display_params.items())[:8]:  # Show first 8 params
                if key != "name":
                    value_str = str(value)[:80] + ('...' if len(str(value)) > 80 else '')
                    msg += f"  • {key}: {value_str}\n"
        
        msg += "\nPlease confirm that you want to create this resource.\n"
        msg += "To proceed, retry this tool call with: kwargs='{\"confirmed\": true}'"
        return msg
    
    elif "update_" in tool_name:
        resource_type = tool_name.replace("update_", "").replace("_", " ").title()
        resource_id = params.get("id") or params.get("name") or "resource"
        
        msg = (
            f"✏️  UPDATE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: UPDATE {resource_type}\n"
            f"Resource ID/Name: {resource_id}\n"
        )
        
        # Show what's being changed
        if len(display_params) > 1:
            msg += "\nChanges to be applied:\n"
            for key, value in list(display_params.items())[:8]:
                if key not in ["id"]:
                    value_str = str(value)[:80] + ('...' if len(str(value)) > 80 else '')
                    msg += f"  • {key}: {value_str}\n"
        
        msg += "\nPlease confirm that you want to update this resource.\n"
        msg += "To proceed, retry this tool call with: kwargs='{\"confirmed\": true}'"
        return msg
    
    else:
        # Generic confirmation message
        return (
            f"⚠️  WRITE OPERATION - CONFIRMATION REQUIRED\n\n"
            f"Operation: {tool_name}\n\n"
            f"Parameters:\n{json.dumps(display_params, indent=2)}\n\n"
            f"Please confirm that you want to proceed with this operation."
        )


def check_confirmation(tool_name: str, confirmed: bool, params: Dict[str, Any]) -> str:
    """Check if confirmation is provided for write operations.
    
    This function should be called at the start of all write operations.
    If confirmation is not provided and not skipped via env var, it returns
    a confirmation message. Otherwise, returns None to proceed.
    
    Args:
        tool_name: Name of the tool being called
        confirmed: Whether the operation is confirmed by the user
        params: All tool parameters (for generating the confirmation message)
        
    Returns:
        Dict with error message if confirmation needed, None to proceed
        
    Example:
        def zpa_delete_application_segment(id: str, confirmed: bool = False):
            # Check for confirmation
            confirmation_check = check_confirmation(
                "zpa_delete_application_segment",
                confirmed,
                {"id": id}
            )
            if confirmation_check:
                return confirmation_check
            
            # Proceed with deletion
            ...
    """
    # Skip confirmation if environment variable is set (for automation)
    if should_skip_confirmations():
        logger.debug(f"Skipping confirmation for {tool_name} (ZSCALER_MCP_SKIP_CONFIRMATIONS=true)")
        return None
    
    # If not confirmed, return confirmation message
    if not confirmed:
        logger.info(f"⚠️  Confirmation required for {tool_name}")
        return generate_confirmation_message(tool_name, params)
    
    # Confirmed, proceed with operation
    logger.info(f"✅ Confirmed: {tool_name}")
    return None

