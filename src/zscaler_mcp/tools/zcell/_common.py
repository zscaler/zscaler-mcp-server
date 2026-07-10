"""ZCell (Zscaler Cellular) shared helpers — private to the ``tools/zcell`` package.

ZCell is a read-only OneAPI surface across nine resource families. The tools
share two small concerns, consolidated here per the helper-file convention (one
``_common.py`` per service package):

- **Time-window input** — several ZCell endpoints require an epoch-seconds time
  window (anomaly policies/violations, SIM usage analytics, audit search,
  network events). The SDK exposes a ``days`` shorthand (``@zcell_params``) that
  turns ``days=7`` into a ``[now - 7d, now]`` window in whichever spot the
  endpoint expects (query / body / path). :class:`WindowInput` surfaces that one
  knob to the agent.
- **SDK-result coercion** — :func:`as_dicts` turns the SDK's list of model
  objects (or already-plain dicts) into plain dicts for the shapers, matching
  the ZINS ``as_dicts`` helper.

The ZCell customer id is NOT a tool parameter: it is resolved once by the client
factory from ``ZCELL_CUSTOMER_ID`` and injected into the SDK config, so every
tool calls ``client.zcell.<domain>.<method>()`` without an ``id`` argument.
"""

from __future__ import annotations

from typing import Annotated, Any, Iterable

from pydantic import BaseModel, Field

__all__ = [
    "WindowInput",
    "as_dicts",
    "as_dict",
]


class WindowInput(BaseModel):
    """Reusable lookback window shared by time-bounded ZCell reads.

    Zscaler Cellular time-bounded endpoints (anomaly policies, SIM usage
    analytics, audit search, network events) take an epoch-seconds window. The
    SDK's ``days`` shorthand fills that window with ``[now - days, now]`` in
    whichever location the endpoint expects (query string, request body, or URL
    path), so callers only need to say "how far back".
    """

    days: Annotated[
        int,
        Field(
            default=7,
            ge=1,
            le=365,
            description=(
                "Lookback window in DAYS. Resolves to a [now - days, now] "
                "epoch-seconds range on the server. Default 7."
            ),
        ),
    ] = 7


def as_dict(entry: Any) -> dict[str, Any]:
    """Coerce a single SDK model (or dict) into a plain dict for the shapers."""
    if entry is None:
        return {}
    if hasattr(entry, "as_dict"):
        return entry.as_dict()
    if isinstance(entry, dict):
        return entry
    try:
        return dict(entry)
    except (TypeError, ValueError):
        return {"value": str(entry)}


def as_dicts(entries: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Coerce a list of SDK model entries into plain dicts for the shapers."""
    if not entries:
        return []
    return [as_dict(entry) for entry in entries]
