"""ZCell Tag Handling — agent-first v2 read tool.

Read-only surface over ``client.zcell.tag_handling``:

    * zcell_list_tags — one curated row per SIM tag defined for the customer
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zcell._common import as_dicts

# =============================================================================
# INPUT MODEL
# =============================================================================


class ListTagsInput(BaseModel):
    """Inputs for listing SIM tags."""

    name: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Server-side substring match on the tag `name`. An empty result "
                "means no tag name contains this string — do not retry with "
                "split keywords."
            ),
        ),
    ] = None
    page: Annotated[
        Optional[int], Field(default=None, ge=0, description="Page number (0-based).")
    ] = None
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


# =============================================================================
# OUTPUT VIEW
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _query(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in pairs if value is not None}


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_tag_handling",
    input_model=ListTagsInput,
    is_list=True,
)
def zcell_list_tags(args: ListTagsInput) -> list[dict[str, Any]]:
    """List the Zscaler Cellular SIM tags defined for the customer.

    Read-only. Returns one row per tag (id, name, provenance). Use the returned
    tag `id` when assigning tags to SIMs.
    """
    client = get_zscaler_client(service="zcell")

    tags, _, err = client.zcell.tag_handling.list_tag(
        query_params=_query(("name", args.name), ("page", args.page), ("size", args.size))
    )
    if err:
        raise RuntimeError(f"Failed to list tags: {err}")
    return shape_many(as_dicts(tags))
