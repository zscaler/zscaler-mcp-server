"""Shared ZDX tool helpers (v2).

ZDX has a handful of cross-module conventions worth factoring out so the
per-resource modules stay focused on shaping:

* **Scope filters.** Most ZDX read endpoints accept the same optional
  ``location_id`` / ``department_id`` / ``geo_id`` scope filters plus a ``since``
  window expressed in HOURS. :func:`scope_query_params` builds the SDK
  ``query_params`` dict from those, omitting unset keys.
* **Wrapped-list unwrapping.** Several ZDX list endpoints return a single-element
  list wrapping an object whose real rows hang off a nested property
  (``devices_obj.devices``, ``alerts_obj.alerts``, ...). The exact property name
  differs per endpoint, so this module only provides :func:`unwrap_nested`, which
  takes the property name explicitly; each module passes its own.
* **Timestamp normalization.** Deep-trace payloads carry Unix epoch timestamps;
  :func:`convert_timestamps` mirrors v1's ``deeptrace_manage``/``list_deep_traces``
  behaviour (ISO string + ``*_epoch`` companion) so the agent reads ISO times.

These mirror the logic in v1's ``zscaler_mcp/tools/zdx/*`` modules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many

__all__ = [
    "scope_query_params",
    "unwrap_nested",
    "convert_timestamps",
    "TraceInput",
    "ProbeInput",
    "build_metric_tool",
]

# Keys whose (epoch) value should be normalized to ISO format in trace payloads.
_TIMESTAMP_KEYS = {
    "created",
    "started",
    "ended",
    "timestamp",
    "time",
    "created_at",
    "started_at",
    "ended_at",
}


def scope_query_params(
    *,
    location_id: list[str] | None = None,
    department_id: list[str] | None = None,
    geo_id: list[str] | None = None,
    since: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a ZDX ``query_params`` dict, omitting unset keys.

    ``since`` is in HOURS (the ZDX default is 2h when omitted). ``extra`` lets a
    caller add endpoint-specific filters (``offset``, ``limit``, ``emails``, ...)
    without re-implementing the omit-None dance.
    """
    qp: dict[str, Any] = {}
    if location_id:
        qp["location_id"] = location_id
    if department_id:
        qp["department_id"] = department_id
    if geo_id:
        qp["geo_id"] = geo_id
    if since is not None:
        qp["since"] = since
    for key, value in extra.items():
        if value is not None:
            qp[key] = value
    return qp


def unwrap_nested(results: list[Any] | None, prop: str) -> list[dict[str, Any]]:
    """Unwrap the ZDX single-element-list-wrapping-a-nested-list shape.

    Many ZDX list endpoints return ``[wrapper]`` where ``wrapper.<prop>`` is the
    real list of item models. Returns each item as a dict (``as_dict()`` when the
    item is an SDK model, otherwise the item itself).
    """
    if not results:
        return []
    wrapper = results[0]
    items = getattr(wrapper, prop, None) or []
    return [item.as_dict() if hasattr(item, "as_dict") else item for item in items]


def _convert_single(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    converted: dict[str, Any] = {}
    for key, value in item.items():
        if isinstance(value, (int, str)) and key.lower() in _TIMESTAMP_KEYS:
            try:
                epoch = int(value)
                converted[key] = datetime.fromtimestamp(epoch).isoformat()
                converted[f"{key}_epoch"] = epoch
            except (ValueError, TypeError, OSError):
                converted[key] = value
        elif isinstance(value, dict):
            converted[key] = _convert_single(value)
        elif isinstance(value, list):
            converted[key] = [_convert_single(v) if isinstance(v, dict) else v for v in value]
        else:
            converted[key] = value
    return converted


def convert_timestamps(data: Any) -> Any:
    """Convert Unix-epoch timestamp fields to ISO strings (recursively).

    Mirrors v1's deep-trace timestamp handling: each recognized timestamp key is
    rewritten to an ISO-8601 string and a companion ``<key>_epoch`` preserves the
    original numeric value. Non-timestamp data passes through unchanged.
    """
    if isinstance(data, list):
        return [_convert_single(item) for item in data]
    return _convert_single(data)


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _as_dicts(result: list[Any] | None) -> list[dict[str, Any]]:
    """Normalize a list of SDK models (or dicts) into plain dicts."""
    return [item.as_dict() if hasattr(item, "as_dict") else item for item in (result or [])]


# =============================================================================
# Shared deep-trace inputs / views / shapers
# =============================================================================
#
# The deep-trace metric/event readers (web-probe, cloud-path, cloud-path
# metrics, health metrics, events) all take the same device+trace input and
# return the same nested time-series view. v1 keeps one file per metric; to honor
# that layout without copying the factory five times, the shared machinery lives
# here and each per-metric module is a thin ``build_metric_tool(...)`` call.


class TraceInput(BaseModel):
    """Inputs for a device + trace pair (get / metrics / events)."""

    device_id: Annotated[str, Field(description="ZDX device ID (string, even if numeric).")]
    trace_id: Annotated[str, Field(description="Deep-trace session ID (string, even if numeric).")]


def build_metric_tool(sdk_method_name: str, label: str, *, name: str, description: str):
    """Build + register a device+trace metric reader bound to an SDK method.

    Each ZDX deep-trace metric module (``deeptrace_webprobe_metrics.py``,
    ``deeptrace_cloudpath.py``, ...) calls this once. The ``@tool`` registration
    fires at call time, so the tool is owned by the module that invokes it —
    preserving v1's one-file-per-metric layout.
    """

    def _run(args: TraceInput) -> list[dict[str, Any]]:
        if not args.device_id or not args.trace_id:
            raise ValueError("device_id and trace_id are required")
        client = get_zscaler_client(service="zdx")
        method = getattr(client.zdx.troubleshooting, sdk_method_name)
        result, _, err = method(args.device_id, args.trace_id)
        if err:
            raise RuntimeError(f"Failed to get ZDX {label}: {err}")
        return shape_many(_as_dicts(result))

    return tool(
        action=READ,
        service="zdx",
        toolset="zdx_troubleshooting",
        input_model=TraceInput,
        is_list=True,
        wire_format=WireFormat.JSON,
        name=name,
        description=description,
    )(_run)


# =============================================================================
# Shared device-probe input / view / shaper (web + cloud-path probes)
# =============================================================================


class ProbeInput(BaseModel):
    """Inputs for listing web / cloudpath probes for an app on a device."""

    device_id: Annotated[str, Field(description="ZDX device ID (string, even if numeric).")]
    app_id: Annotated[str, Field(description="Application ID (string, even if numeric).")]
    since: Annotated[
        Optional[int],
        Field(default=None, ge=1, description="Look-back window in HOURS (ZDX default 2h)."),
    ] = None
