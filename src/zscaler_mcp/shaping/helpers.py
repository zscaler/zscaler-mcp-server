"""Shaper helpers — defensive SDK-dict field access used inside shapers.

SDK ``as_dict()`` output is inconsistent across resources: a relational field
may arrive as ``microtenant_id`` or ``microtenantId``, and Optional fields may
be absent entirely. These helpers let a shaper read defensively without
per-field branching, which is what keeps shapers resilient to SDK changes
(DESIGN.md §7).

Public API is re-exported from ``zscaler_mcp.shaping``; import from there.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from zscaler_mcp.shaping.views import AgentView

__all__ = ["pick", "coalesce", "shape_many"]


def pick(source: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-None value among ``keys`` in ``source``.

    SDK dicts are inconsistent about snake_case vs camelCase across resources
    (``microtenant_id`` vs ``microtenantId``). ``pick`` lets a shaper accept
    both without branching::

        pick(raw, "microtenant_id", "microtenantId")
    """
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return default


def coalesce(source: dict[str, Any], *keys: str) -> list[Any]:
    """Return the first present list among ``keys``, or ``[]``.

    Useful for relational fields the SDK may name differently or omit entirely
    (``app_segments`` / ``applications`` / missing).
    """
    for key in keys:
        value = source.get(key)
        if isinstance(value, list):
            return value
    return []


def shape_many(
    raw_items: Iterable[dict[str, Any]],
    shaper: Callable[[dict[str, Any]], AgentView],
) -> list[dict[str, Any]]:
    """Apply a single-item ``shaper`` across a list and dump to plain dicts.

    The tool layer returns plain dicts (what the encoder serializes), so each
    view is dumped via ``model_dump()`` after construction. Construction is what
    enforces the curated shape; the dump is just serialization.
    """
    return [shaper(item).model_dump() for item in raw_items]
