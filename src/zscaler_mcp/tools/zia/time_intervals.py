"""ZIA time intervals — list, get, create, update, delete.

Mirrors v1's ``client.zia.time_intervals`` SDK calls. Reusable schedule objects
referenced by rule ``time_windows``. Update is PUT-replace; the tool backfills
name/start_time/end_time/days_of_week when omitted. Writes are staged until
``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

_DAYS_DESC = "Days: EVERYDAY, SUN, MON, TUE, WED, THU, FRI, SAT. List or JSON string."
_TIME_DESC = "Minutes from midnight (0-1439). E.g. 480 = 08:00, 1020 = 17:00."


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on interval name.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, description="Page number.")] = None
    page_size: Annotated[Optional[int], Field(default=None, description="Items per page.")] = None


class GetInput(BaseModel):
    interval_id: Annotated[str, Field(description="Interval ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Interval name (ASCII letters/spaces only).")]
    start_time: Annotated[int, Field(description=_TIME_DESC)]
    end_time: Annotated[int, Field(description=_TIME_DESC)]
    days_of_week: Annotated[list[str], Field(description=_DAYS_DESC)]


class UpdateInput(BaseModel):
    interval_id: Annotated[str, Field(description="Interval ID to update.")]
    name: Annotated[Optional[str], Field(default=None, description="New name.")] = None
    start_time: Annotated[Optional[int], Field(default=None, description=_TIME_DESC)] = None
    end_time: Annotated[Optional[int], Field(default=None, description=_TIME_DESC)] = None
    days_of_week: Annotated[Optional[list[str]], Field(default=None, description=_DAYS_DESC)] = None


class DeleteInput(BaseModel):
    interval_id: Annotated[str, Field(description="Interval ID to delete.")]


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


@tool(
    action=READ,
    service="zia",
    toolset="zia_time_intervals",
    input_model=ListInput,
    is_list=True,
)
def zia_list_time_intervals(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA time intervals."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    intervals, _, err = client.zia.time_intervals.list_time_intervals(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list time intervals: {err}")
    return shape_many([i.as_dict() for i in (intervals or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_time_intervals",
    input_model=GetInput,
    is_list=False,
)
def zia_get_time_interval(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA time interval by ID."""
    client = get_zscaler_client(service="zia")
    interval, _, err = client.zia.time_intervals.get_time_intervals(args.interval_id)
    if err:
        raise RuntimeError(f"Failed to get time interval {args.interval_id}: {err}")
    return shape_one(interval.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_time_intervals",
    input_model=CreateInput,
    is_list=False,
)
def zia_create_time_interval(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA time interval (write). Activate after."""
    client = get_zscaler_client(service="zia")
    interval, _, err = client.zia.time_intervals.add_time_intervals(
        name=args.name,
        start_time=args.start_time,
        end_time=args.end_time,
        days_of_week=parse_list(args.days_of_week),
    )
    if err:
        raise RuntimeError(f"Failed to create time interval: {err}")
    return shape_one(interval.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_time_intervals",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_time_interval(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA time interval (PUT-replace; backfills omitted fields). Activate after."""
    payload: dict[str, Any] = {}
    if args.name is not None:
        payload["name"] = args.name
    if args.start_time is not None:
        payload["start_time"] = args.start_time
    if args.end_time is not None:
        payload["end_time"] = args.end_time
    if args.days_of_week is not None:
        payload["days_of_week"] = parse_list(args.days_of_week)

    client = get_zscaler_client(service="zia")
    api = client.zia.time_intervals
    required = ("name", "start_time", "end_time", "days_of_week")
    if any(f not in payload for f in required):
        existing, _, ferr = api.get_time_intervals(args.interval_id)
        if ferr:
            raise RuntimeError(
                f"Failed to fetch time interval {args.interval_id} for backfill: {ferr}"
            )
        ed = existing.as_dict()
        for f in required:
            if f not in payload and ed.get(f) is not None:
                payload[f] = ed[f]

    updated, _, err = api.update_time_intervals(args.interval_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update time interval {args.interval_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_time_intervals",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_time_interval(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA time interval (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.time_intervals.delete_time_intervals(args.interval_id)
    if err:
        raise RuntimeError(f"Failed to delete time interval {args.interval_id}: {err}")
    return OperationResult(
        success=True, message=f"Time interval {args.interval_id} deleted successfully."
    ).model_dump()
