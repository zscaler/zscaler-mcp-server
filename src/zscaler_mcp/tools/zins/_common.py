"""Z-Insights (ZINS) shared helpers — private to the ``tools/zins`` package.

ZINS is a GraphQL analytics API (aggregated metrics, time-series, grouped
buckets), not a CRUD surface. The v1 server centralized a handful of cross-tool
concerns in ``zscaler_mcp/tools/zins/common.py``; this module replicates the
SUBSET the v2 tools actually need, ported (NOT imported) from v1:

- **Time-param resolution** — every analytics query is bounded by a time range.
  The API requires intervals of *exactly* 7 or 14 days; callers may give either
  epoch-millisecond timestamps or a relative ``*_days_ago`` window, so
  :func:`resolve_time_params` normalizes both to an epoch-ms ``(start, end)``
  pair and snaps free-form windows onto the nearest valid interval.
- **GraphQL error checking** — the ZINS GraphQL endpoint can return HTTP 200
  with GraphQL-level ``errors`` in the body. :func:`raise_for_graphql_errors`
  surfaces those as a ``RuntimeError`` so the tool layer's normal
  ``raise RuntimeError`` contract (mirroring the SDK-``err`` path) holds.
- **SDK-result coercion** — :func:`as_dicts` turns the SDK's list of model
  objects (or already-plain dicts) into plain dicts for the shapers.

Mirrors v1 paths: ``zscaler_mcp/tools/zins/common.py``.
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Iterable, Optional

from pydantic import BaseModel, Field

__all__ = [
    "VALID_TRAFFIC_UNITS",
    "VALID_TREND_INTERVALS",
    "VALID_ACTION_FILTERS",
    "VALID_DLP_ENGINE_FILTERS",
    "VALID_INCIDENTS_CATEGORIZE_BY",
    "VALID_INCIDENTS_CATEGORIZE_BY_WITH_ID",
    "TimeWindowInput",
    "calculate_epoch_ms",
    "resolve_time_params",
    "resolve_window",
    "validate_time_range",
    "raise_for_graphql_errors",
    "as_dicts",
]

# =============================================================================
# Enumerations (ported from v1 zins/common.py — surfaced in input field docs)
# =============================================================================

VALID_TRAFFIC_UNITS = ("TRANSACTIONS", "BYTES")
VALID_TREND_INTERVALS = ("DAY", "HOUR")
VALID_ACTION_FILTERS = ("ALLOW", "BLOCK")
VALID_DLP_ENGINE_FILTERS = (
    "ANY",
    "NONE",
    "HIPAA",
    "CYBER_BULLY_ENG",
    "GLBA",
    "PCI",
    "OFFENSIVE_LANGUAGE",
    "EXTERNAL",
)
# Cyber-incident categorization (multi-select grouping, no id returned).
VALID_INCIDENTS_CATEGORIZE_BY = (
    "THREAT_CATEGORY_ID",
    "APP_ID",
    "USER_ID",
    "TIME",
    "SRC_COUNTRY",
)
# Cyber-incident categorization that returns an id alongside the name.
VALID_INCIDENTS_CATEGORIZE_BY_WITH_ID = (
    "LOCATION_ID",
    "APP_ID",
    "USER_ID",
    "DEPARTMENT_ID",
)

_MS_PER_DAY = 24 * 60 * 60 * 1000


# =============================================================================
# Shared time-window input (every analytics query is time-bounded)
# =============================================================================


class TimeWindowInput(BaseModel):
    """Reusable time-window inputs shared by every ZINS analytics tool.

    Z-Insights serves only HISTORICAL data with a 24-48h processing delay, and
    the API requires the window to be an interval of *exactly* 7 or 14 days.
    Two ways to express the window:

    * **Relative (recommended):** ``start_days_ago`` / ``end_days_ago``. A
      free-form span is auto-snapped to the nearest valid 7- or 14-day interval.
    * **Absolute:** ``start_time`` / ``end_time`` in epoch milliseconds — wins
      over the relative params and is used verbatim (no auto-snapping).

    Defaults give a 7-day window ending 2 days ago.
    """

    start_days_ago: Annotated[
        int,
        Field(
            default=9,
            ge=1,
            description=(
                "Days ago for the window start (relative mode). Default 9, which "
                "with end_days_ago=2 yields a valid 7-day interval. Use 16 for a "
                "14-day interval. The API only accepts 7- or 14-day intervals; "
                "free-form spans are auto-snapped to the nearest valid one."
            ),
        ),
    ] = 9
    end_days_ago: Annotated[
        int,
        Field(
            default=2,
            ge=1,
            description=(
                "Days ago for the window end (relative mode). Default 2 — data "
                "lags 24-48h so the end must be at least 1 day in the past."
            ),
        ),
    ] = 2
    start_time: Annotated[
        Optional[int],
        Field(
            default=None,
            description=(
                "Absolute window start as a Unix epoch in MILLISECONDS. Overrides "
                "start_days_ago. Only use when you have a specific timestamp."
            ),
        ),
    ] = None
    end_time: Annotated[
        Optional[int],
        Field(
            default=None,
            description=(
                "Absolute window end as a Unix epoch in MILLISECONDS. Overrides "
                "end_days_ago. Only use when you have a specific timestamp."
            ),
        ),
    ] = None


def resolve_window(args: TimeWindowInput, **kwargs: Any) -> tuple[int, int]:
    """Resolve + validate a :class:`TimeWindowInput` into ``(start_ms, end_ms)``.

    Convenience wrapper that threads the four window fields through
    :func:`resolve_time_params` and then :func:`validate_time_range`. Extra
    keyword args (e.g. ``default_start_days=16``) pass through to
    :func:`resolve_time_params`.
    """
    start_ms, end_ms = resolve_time_params(
        args.start_time, args.end_time, args.start_days_ago, args.end_days_ago, **kwargs
    )
    validate_time_range(start_ms, end_ms)
    return start_ms, end_ms


# =============================================================================
# Time-parameter resolution
# =============================================================================


def calculate_epoch_ms(days_ago: int) -> int:
    """Return the epoch-millisecond timestamp ``days_ago`` days in the past."""
    return int(time.time() * 1000) - (days_ago * _MS_PER_DAY)


def resolve_time_params(
    start_time: Optional[int],
    end_time: Optional[int],
    start_days_ago: Optional[int],
    end_days_ago: Optional[int],
    *,
    default_start_days: int = 9,
    default_end_days: int = 2,
    auto_adjust_interval: bool = True,
) -> tuple[int, int]:
    """Normalize the time window to an epoch-ms ``(start, end)`` pair.

    Callers can express the window two ways: explicit epoch-ms ``start_time`` /
    ``end_time`` (wins when present), or a relative ``start_days_ago`` /
    ``end_days_ago`` window. When nothing is supplied, the defaults give a
    7-day window ending 2 days ago (ZINS data lags 24-48h).

    When ``auto_adjust_interval`` is set and the window came from the relative
    params, a free-form interval is snapped onto the nearest valid 7- or 14-day
    interval (the ZINS API rejects anything else).
    """
    if start_time is not None:
        resolved_start = start_time
    elif start_days_ago is not None:
        resolved_start = calculate_epoch_ms(start_days_ago)
    else:
        resolved_start = calculate_epoch_ms(default_start_days)

    if end_time is not None:
        resolved_end = end_time
    elif end_days_ago is not None:
        resolved_end = calculate_epoch_ms(end_days_ago)
    else:
        resolved_end = calculate_epoch_ms(default_end_days)

    if auto_adjust_interval and start_time is None and end_time is None:
        interval_days = (resolved_end - resolved_start) / _MS_PER_DAY
        if abs(interval_days - 7) > 0.5 and abs(interval_days - 14) > 0.5:
            span = 7 if interval_days < 10.5 else 14
            resolved_start = resolved_end - (span * _MS_PER_DAY)

    return (resolved_start, resolved_end)


def validate_time_range(start_time: int, end_time: int) -> None:
    """Reject windows ZINS cannot answer (non-historical / inverted).

    ZINS only serves historical data with a 24-48h processing lag, so the end
    of the window must be at least a day in the past and strictly after the
    start.
    """
    now_ms = int(time.time() * 1000)
    if start_time >= end_time:
        raise ValueError("start_time must be less than end_time")
    if end_time >= now_ms:
        raise ValueError("end_time must be in the past — Z-Insights only serves historical data.")
    if end_time > (now_ms - _MS_PER_DAY):
        raise ValueError(
            "end_time should be at least 1 day in the past for data availability "
            "(Z-Insights has a 24-48 hour processing delay)."
        )


# =============================================================================
# GraphQL response handling
# =============================================================================


def raise_for_graphql_errors(response: Any, operation: str = "Z-Insights query") -> None:
    """Raise ``RuntimeError`` if the GraphQL body carries ``errors``.

    The ZINS endpoint can return HTTP 200 with GraphQL-level errors embedded in
    the body. We translate those into the same ``RuntimeError`` contract the
    tool layer uses for SDK ``err`` values, with a clearer message for the
    common ``INTERNAL_ERROR`` (usually: the feature is not licensed / no data)
    and ``BAD_REQUEST`` (usually: invalid time range) classifications.
    """
    if not response or not hasattr(response, "get_body"):
        return

    try:
        body = response.get_body()
    except AttributeError:
        return

    if not isinstance(body, dict):
        return

    errors = body.get("errors")
    if not errors:
        return

    messages: list[str] = []
    classifications: list[str] = []
    for err in errors:
        msg = err.get("message", "Unknown error")
        classification = err.get("classification", "")
        path = err.get("path", [])
        if classification:
            classifications.append(classification)
        if path:
            msg = f"{msg} at {'.'.join(str(p) for p in path)}"
        messages.append(msg)

    if "INTERNAL_ERROR" in classifications:
        detail = (
            "The Z-Insights API returned an internal error. This typically means no "
            "data is available for this query type, or Z-Insights / Business Insights "
            "is not licensed on this tenant."
        )
    elif "BAD_REQUEST" in classifications:
        detail = (
            f"Invalid request parameters: {'; '.join(messages)}. Check that the time "
            "range is a valid 7- or 14-day historical interval."
        )
    else:
        detail = f"API error: {'; '.join(messages)}"

    raise RuntimeError(f"{operation} failed: {detail}")


def as_dicts(entries: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Coerce SDK result entries into plain dicts for the shapers."""
    if not entries:
        return []

    out: list[dict[str, Any]] = []
    for entry in entries:
        if hasattr(entry, "as_dict"):
            out.append(entry.as_dict())
        elif isinstance(entry, dict):
            out.append(entry)
        else:
            try:
                out.append(dict(entry))
            except (TypeError, ValueError):
                out.append({"value": str(entry)})
    return out
