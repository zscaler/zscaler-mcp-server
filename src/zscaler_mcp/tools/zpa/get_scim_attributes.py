"""ZPA SCIM Attributes — read-only lookup.

Mirrors v1's ``get_scim_attributes.py``. Registered under the exact v1 tool
name ``get_zpa_scim_attribute``: requires a named IdP (resolved to its ID
internally); lists all SCIM attributes for it, or fetches one by ID. Output is
the curated ``RefItem`` view (id + name).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zpa._refs import resolve_idp_id


class ScimAttributeInput(BaseModel):
    """Inputs for reading ZPA SCIM attributes (IdP-scoped)."""

    idp_name: Annotated[str, Field(description="IdP display name (resolved to its ID internally).")]
    attribute_id: Annotated[
        Optional[str],
        Field(default=None, description="Optional SCIM attribute ID for direct lookup."),
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=500, description="Items per page (API default 20, max 500)."),
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_idp",
    name="get_zpa_scim_attribute",
    input_model=ScimAttributeInput,
    is_list=True,
)
def get_zpa_scim_attribute(args: ScimAttributeInput) -> list[dict[str, Any]]:
    """List ZPA SCIM attributes for a named IdP, or fetch one by ID (read-only)."""
    if not args.idp_name:
        raise ValueError("idp_name is required for SCIM attribute discovery.")
    client = get_zscaler_client(service="zpa")
    idp_id = resolve_idp_id(client, args.idp_name)
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    if args.attribute_id:
        attr, _, err = client.zpa.scim_attributes.get_scim_attribute(
            idp_id=idp_id, attribute_id=args.attribute_id, query_params=qp
        )
        if err:
            raise RuntimeError(f"Failed to fetch SCIM attribute by ID: {err}")
        return shape_many([attr.as_dict()])
    attrs, _, err = client.zpa.scim_attributes.list_scim_attributes(idp_id=idp_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list SCIM attributes for IdP {args.idp_name}: {err}")
    return shape_many([a.as_dict() for a in (attrs or [])])
