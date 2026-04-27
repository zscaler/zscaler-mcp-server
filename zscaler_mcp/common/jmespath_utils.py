"""
JMESPath client-side filtering for MCP tool results.

Provides a shared helper that applies JMESPath expressions to SDK
results, enabling AI agents to filter and project data client-side
across all Zscaler services.
"""

from typing import Any, Optional


def apply_jmespath(
    data: Any,
    expression: Optional[str],
) -> Any:
    """
    Apply a JMESPath expression to SDK result data for client-side
    filtering and projection.

    Args:
        data: The SDK result data (list of dicts, dict, etc.).
        expression: A JMESPath expression string. If None/empty,
            returns data unchanged.

    Returns:
        Filtered/projected data. If the expression yields None,
        returns an empty list. Scalar results are wrapped in a list
        (e.g. ``length(@)`` over 19 rules returns ``[19]``, not ``19``).

    NOTE: Tools that pipe through this helper MUST declare their return
    type as ``Any`` (not ``List[dict]`` or ``List[str]``). The "happy
    path" element type only holds when the caller does not supply a
    ``query``; with a JMESPath expression the result can be a list of
    scalars, projected values, or other shapes. A strict ``List[dict]``
    annotation will trip the MCP/Pydantic output validator and force the
    AI agent to narrate around the error (exposing internal mechanics
    like JMESPath and validation failures to the end user). Use ``Any``
    and document the happy-path shape in the docstring instead.
    """
    if not expression:
        return data

    import jmespath

    try:
        filtered = jmespath.search(expression, data)
    except jmespath.exceptions.ParseError as e:
        return [{"error": f"Invalid JMESPath expression: {e}"}]

    if filtered is None:
        return []
    if isinstance(filtered, list):
        return filtered
    return [filtered]
