"""ZMS agent groups — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/agent_groups.py``:

    zms_list_agent_groups, zms_get_agent_group_totp_secrets

``list_agent_groups`` returns a connection ``{nodes, page_info}``;
``get_agent_group_totp_secrets`` returns the (sensitive) TOTP secret bundle for
one group keyed by ``eyez_id``. Requires ZSCALER_CUSTOMER_ID.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, shape_many
from zscaler_mcp.tools.zms._common import nodes_of, require_customer_id

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListAgentGroupsInput(BaseModel):
    """Inputs for listing ZMS agent groups."""

    page: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    search: Annotated[Optional[str], Field(default=None, description="Search filter.")] = None
    sort: Annotated[Optional[str], Field(default=None, description="Sort field (e.g. 'name').")] = (
        None
    )
    sort_dir: Annotated[
        Optional[str], Field(default=None, description="Sort direction: ASC or DESC.")
    ] = None


class AgentGroupTotpInput(BaseModel):
    """Inputs for fetching a ZMS agent group's TOTP secrets."""

    eyez_id: Annotated[str, Field(description="Agent group eyez_id (the canonical identifier).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class TotpSecrets(AgentView):
    """ZMS agent-group TOTP secrets — SENSITIVE; nested payload."""

    eyez_id: Optional[str] = Field(default=None, description="Agent group eyez_id (echoed).")
    data: dict = Field(
        default_factory=dict, description="TOTP secret bundle (treat as sensitive credentials)."
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListAgentGroupsInput,
    is_list=True,
)
def zms_list_agent_groups(args: ListAgentGroupsInput) -> list[dict[str, Any]]:
    """List ZMS agent groups.

    Read-only. Returns one row per group (eyez_id, name, type, cloud provider,
    agent count, policy/tamper status). Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page": args.page,
        "page_size": args.page_size,
    }
    if args.search is not None:
        kwargs["search"] = args.search
    if args.sort is not None:
        kwargs["sort"] = args.sort
    if args.sort_dir is not None:
        kwargs["sort_dir"] = args.sort_dir

    result, _, err = client.zms.agent_groups.list_agent_groups(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS agent groups: {err}")
    return shape_many(nodes_of(result))


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=AgentGroupTotpInput,
    output_view=TotpSecrets,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zms_get_agent_group_totp_secrets(args: AgentGroupTotpInput) -> dict[str, Any]:
    """Get the TOTP secrets for a ZMS agent group (full record).

    Read-only API call, but the returned values ARE sensitive enrollment
    credentials — treat them like secrets. Keyed by `eyez_id`. Requires
    ZSCALER_CUSTOMER_ID.
    """
    if not args.eyez_id:
        raise ValueError("eyez_id is required")
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    result, _, err = client.zms.agent_groups.get_agent_group_totp_secrets(
        customer_id=customer_id, eyez_id=args.eyez_id
    )
    if err:
        raise RuntimeError(f"Failed to get ZMS agent group TOTP secrets: {err}")
    return TotpSecrets(
        eyez_id=args.eyez_id, data=result if isinstance(result, dict) else {}
    ).model_dump()
