"""ZPA application segments by type — read-only lookup.

Mirrors v1's ``get_segments_by_type.py``. Registered under the exact v1 tool
name ``get_zpa_app_segments_by_type``: retrieves application segments filtered
by application type (BROWSER_ACCESS / INSPECT / SECURE_REMOTE_ACCESS). Output is
a lean curated row to keep token usage low.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class SegmentsByTypeInput(BaseModel):
    """Inputs for retrieving application segments filtered by application type."""

    application_type: Annotated[
        str,
        Field(
            pattern="^(BROWSER_ACCESS|INSPECT|SECURE_REMOTE_ACCESS)$",
            description="One of BROWSER_ACCESS, INSPECT, SECURE_REMOTE_ACCESS.",
        ),
    ]
    expand_all: Annotated[bool, Field(default=False, description="Expand related data.")] = False
    search: Annotated[
        Optional[str], Field(default=None, description="Server-side name substring match.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=500, description="Per page.")
    ] = None


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    name="get_zpa_app_segments_by_type",
    input_model=SegmentsByTypeInput,
    is_list=True,
)
def get_zpa_app_segments_by_type(args: SegmentsByTypeInput) -> list[dict[str, Any]]:
    """Retrieve ZPA application segments filtered by application type (read-only).

    `application_type` must be BROWSER_ACCESS, INSPECT, or SECURE_REMOTE_ACCESS.
    """
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    segments, _, err = client.zpa.app_segment_by_type.get_segments_by_type(
        application_type=args.application_type,
        expand_all=args.expand_all,
        query_params=qp,
    )
    if err:
        raise RuntimeError(f"Failed to retrieve application segments by type: {err}")
    return shape_many([s.as_dict() for s in (segments or [])])
