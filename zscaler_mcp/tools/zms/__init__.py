# ZMS (Zscaler Microsegmentation) MCP Tools

from typing import Any, Dict, List, Optional

from zscaler_mcp.common.jmespath_utils import apply_jmespath


def apply_jmespath_query(
    result: Any,
    expression: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Apply a JMESPath expression to the SDK result for client-side
    filtering and projection. ZMS-specific wrapper that preserves
    the [result] envelope when no expression is given.
    """
    if not expression:
        return [result]
    return apply_jmespath(result, expression)
