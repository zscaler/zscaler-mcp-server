"""ZPA SAML Attributes — read-only lookup.

Mirrors v1's ``get_saml_attributes.py``. Registered under the exact v1 tool
name ``get_zpa_saml_attribute``: lists all SAML attributes, or scopes to a
named IdP (resolved to its ID internally). Output is the curated ``RefItem``
view (id + name).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zpa._refs import resolve_idp_id


class SamlAttributeInput(BaseModel):
    """Inputs for reading ZPA SAML attributes."""

    idp_name: Annotated[
        Optional[str],
        Field(default=None, description="Optional IdP display name to scope attributes to."),
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
    name="get_zpa_saml_attribute",
    input_model=SamlAttributeInput,
    is_list=True,
)
def get_zpa_saml_attribute(args: SamlAttributeInput) -> list[dict[str, Any]]:
    """List ZPA SAML attributes, optionally scoped to a named IdP (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    if args.idp_name:
        idp_id = resolve_idp_id(client, args.idp_name)
        attrs, _, err = client.zpa.saml_attributes.list_saml_attributes_by_idp(
            idp_id, query_params=qp
        )
    else:
        attrs, _, err = client.zpa.saml_attributes.list_saml_attributes(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list SAML attributes: {err}")
    return shape_many([a.as_dict() for a in (attrs or [])])
