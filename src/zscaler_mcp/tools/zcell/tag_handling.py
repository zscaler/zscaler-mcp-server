"""ZCell Tag Handling — agent-first v2 read tool.

Read-only surface over ``client.zcell.tag_handling``:

    * zcell_list_tags — one curated row per SIM tag defined for the customer
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
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


class TagView(AgentView):
    """A SIM tag defined for the customer."""

    id: Optional[str] = Field(default=None, description="Tag ID. Use when assigning tags to SIMs.")
    name: Optional[str] = Field(default=None, description="Tag name.")
    creation_time: Optional[Any] = Field(default=None, description="When the tag was created.")
    modified_by_user_id: Optional[str] = Field(
        default=None, description="User that last modified the tag."
    )
    tenant_id: Optional[str] = Field(default=None, description="Owning tenant ID.")
    mvno_customer_id: Optional[str] = Field(default=None, description="Owning MVNO customer ID.")


# =============================================================================
# SHAPER
# =============================================================================


def _shape_tag(raw: dict[str, Any]) -> TagView:
    return TagView(
        id=_opt_str(pick(raw, "id")),
        name=pick(raw, "name"),
        creation_time=pick(raw, "creation_time", "creationTime"),
        modified_by_user_id=_opt_str(pick(raw, "modified_by_user_id", "modifiedByUserId")),
        tenant_id=_opt_str(pick(raw, "tenant_id", "tenantId")),
        mvno_customer_id=_opt_str(pick(raw, "mvno_customer_id", "mvnoCustomerId")),
    )


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
    output_view=TagView,
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
    return shape_many(as_dicts(tags), _shape_tag)
