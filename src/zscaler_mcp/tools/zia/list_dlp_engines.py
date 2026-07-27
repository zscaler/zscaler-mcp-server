"""ZIA DLP engines — read-only manager.

Mirrors v1's ``list_dlp_engines.py`` exactly: a single multiplexed read tool
registered under the v1 name ``get_zia_dlp_engines`` (list all, list lite, or fetch
one by ID). Backed by ``client.zia.dlp_engine``.

The engine records are returned exactly as the ZIA API provides them
instead of the raw SDK dict, to keep token usage low.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class DlpEngineInput(BaseModel):
    """Inputs for reading ZIA DLP engines.

    Provide nothing to list all; provide ``engine_id`` to fetch one (returned as a
    single-item list); use ``action='read_lite'`` for the minimal id/name listing.
    """

    action: Annotated[
        Literal["read", "read_lite"],
        Field(default="read", description="'read' for full data, 'read_lite' for id/name only."),
    ] = "read"
    engine_id: Annotated[
        Optional[str], Field(default=None, description="Engine ID for direct lookup.")
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on name/description.")
    ] = None


@tool(
    action=READ,
    service="zia",
    toolset="zia_dlp",
    input_model=DlpEngineInput,
    is_list=True,
)
def get_zia_dlp_engines(args: DlpEngineInput) -> list[dict[str, Any]]:
    """Read ZIA DLP engines: list all/lite, or fetch one by ID (read-only)."""
    client = get_zscaler_client(service="zia")
    api = client.zia.dlp_engine
    qp = {"search": args.search} if args.search else {}

    if args.action == "read" and args.engine_id:
        engine, _, err = api.get_dlp_engines(args.engine_id)
        if err:
            raise RuntimeError(f"Failed to get DLP engine {args.engine_id}: {err}")
        return shape_many([engine.as_dict()])

    if args.action == "read_lite":
        engines, _, err = api.list_dlp_engines_lite(query_params=qp)
    else:
        engines, _, err = api.list_dlp_engines(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list DLP engines: {err}")
    return shape_many([e.as_dict() for e in (engines or [])])
