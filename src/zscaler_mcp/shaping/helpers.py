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

__all__ = ["pick", "coalesce", "shape_many", "shape_one"]


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


def _as_record(raw: Any) -> dict[str, Any]:
    """Coerce a shaper input into a plain dict of every attribute it carries.

    Tools hand shapers either an already-``as_dict()``-ed record (the common
    case) or, occasionally, the raw SDK model object itself (e.g. settings
    singletons call ``to_settings(settings)``). Normalize both to a full dict so
    the merge never drops fields and never blows up on ``{**obj}`` for a
    non-mapping SDK object.
    """
    if isinstance(raw, dict):
        return dict(raw)
    as_dict = getattr(raw, "as_dict", None)
    if callable(as_dict):
        return as_dict()
    # Last resort: best-effort attribute scrape (skip private/callables).
    return (
        {k: v for k, v in vars(raw).items() if not k.startswith("_")}
        if hasattr(raw, "__dict__")
        else {}
    )


def shape_one(
    raw: Any,
    shaper: Callable[[Any], AgentView] | None = None,
) -> dict[str, Any]:
    """Return the FULL record with the shaper's highlighted fields merged on top.

    This is the single-object counterpart to :func:`shape_many`. The result is
    ``{**full_record, **shaper(raw).model_dump()}`` — i.e. every attribute the
    SDK returned, with the view's normalized/computed fields (cast ids,
    flattened enums, relational counts, …) overlaid on the important ones.
    Nothing is dropped; the shaper can only ADD to or NORMALIZE the record,
    never restrict it. See :class:`AgentView` for why this replaced the old
    whitelist behavior (issue #88).

    ``raw`` may be a dict (already ``as_dict()``-ed) or an SDK model object; both
    are coerced to the full record via :func:`_as_record`. ``shaper`` is
    optional: when ``None`` the full record is returned unchanged (a plain
    passthrough), which is what tools with no meaningful normalization want.
    """
    record = _as_record(raw)
    if shaper is None:
        return record
    # Hand the shaper the coerced dict (not the original object) so every shaper
    # can assume a plain mapping — dict-based shapers are the overwhelming
    # majority, and the few that accept an SDK object (e.g. ZIA ``to_settings``)
    # handle a dict too.
    return {**record, **shaper(record).model_dump()}


def shape_many(
    raw_items: Iterable[dict[str, Any]],
    shaper: Callable[[dict[str, Any]], AgentView] | None = None,
) -> list[dict[str, Any]]:
    """Shape a list, preserving every attribute of every record.

    Each item becomes ``{**raw, **shaper(raw).model_dump()}`` — the full SDK
    record with the view's highlighted fields merged on top (see
    :func:`shape_one`). The shaper NORMALIZES and ANNOTATES; it never strips.
    Token efficiency for large lists comes from the CSV wire format (columns
    stated once), not from dropping fields.
    """
    return [shape_one(item, shaper) for item in raw_items]
