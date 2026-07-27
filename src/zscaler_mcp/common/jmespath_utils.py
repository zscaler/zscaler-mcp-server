"""JMESPath client-side filtering for list-tool results.

Every list tool accepts an optional ``query`` parameter carrying a
`JMESPath <https://jmespath.org/>`_ expression, applied to the result AFTER the
API call returns. This is the caller-opt-in counterpart to the server-side
``search`` / pagination filters: the agent — which knows the question being
asked — decides what to keep, instead of the server guessing which attributes
matter. (Guessing is what issue #88 was; see the response-shaping contract in
CLAUDE.md.)

Field names in expressions are whatever the Zscaler API returns, since records
are passed through verbatim.

The wiring is central: ``registry/fastmcp_bridge`` adds the parameter to every
``is_list`` tool and applies it, so no tool module opts in (or forgets to).
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = ["apply_jmespath"]


def apply_jmespath(data: Any, expression: Optional[str]) -> Any:
    """Apply a JMESPath ``expression`` to ``data`` for filtering/projection.

    Args:
        data: The tool result (list of records, or a single record).
        expression: A JMESPath expression. ``None``/empty returns ``data``
            unchanged, which is the default path for every call.

    Returns:
        The filtered/projected data. A ``None`` match becomes ``[]`` and a
        scalar match (``length(@)``, ``sum(...)``) is wrapped in a list, so a
        list tool keeps returning a list regardless of the expression shape.
        An invalid expression returns a single-item error record rather than
        raising — the agent sees what it did wrong and can correct it without
        the call failing.
    """
    if not expression:
        return data

    import jmespath

    try:
        filtered = jmespath.search(expression, data)
    except jmespath.exceptions.JMESPathError as exc:
        return [{"error": f"Invalid JMESPath expression: {exc}"}]

    if filtered is None:
        return []
    if isinstance(filtered, list):
        return filtered
    return [filtered]
