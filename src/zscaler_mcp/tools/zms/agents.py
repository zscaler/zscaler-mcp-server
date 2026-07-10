"""ZMS agents — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/agents.py``:

    zms_list_agents, zms_get_agent_connection_status_statistics,
    zms_get_agent_version_statistics

ZMS is GraphQL: ``list_agents`` returns a connection ``{nodes, page_info}``; the
two statistics tools return a single aggregate dict. ``eyez_id`` is the canonical
agent identifier (not a numeric id). Every call needs ``ZSCALER_CUSTOMER_ID``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zms._common import nodes_of, require_customer_id

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListAgentsInput(BaseModel):
    """Inputs for listing ZMS agents."""

    page: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    search: Annotated[
        Optional[str], Field(default=None, description="Search by name, IP, etc.")
    ] = None
    sort: Annotated[Optional[str], Field(default=None, description="Sort field (e.g. 'name').")] = (
        None
    )
    sort_dir: Annotated[
        Optional[str], Field(default=None, description="Sort direction: ASC or DESC.")
    ] = None


class AgentStatsInput(BaseModel):
    """Inputs for the ZMS agent statistics queries."""

    search: Annotated[Optional[str], Field(default=None, description="Optional search filter.")] = (
        None
    )


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class AgentSummary(AgentView):
    """Lean view — one ZMS agent row."""

    eyez_id: str = Field(description="Agent eyez_id — the canonical identifier.")
    name: Optional[str] = Field(default=None, description="Agent name.")
    connection_status: Optional[str] = Field(
        default=None, description="CONNECTED / DISCONNECTED (decision-bearing)."
    )
    version: Optional[str] = Field(default=None, description="Agent software version.")
    os_type: Optional[str] = Field(default=None, description="Operating system type.")
    ip_address: Optional[str] = Field(default=None, description="Primary IP address.")


class AgentStats(AgentView):
    """ZMS agent fleet statistics — aggregate, kept as a nested payload."""

    total: Optional[int] = Field(default=None, description="Total agent count, if reported.")
    data: dict = Field(default_factory=dict, description="Full aggregate statistics payload.")


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_agent(raw: dict[str, Any]) -> AgentSummary:
    ips = pick(raw, "ip_addresses", "ipAddresses", default=None)
    ip = None
    if isinstance(ips, list) and ips:
        ip = str(ips[0])
    elif isinstance(ips, str):
        ip = ips
    return AgentSummary(
        eyez_id=str(pick(raw, "eyez_id", "eyezId", "id", default="")),
        name=pick(raw, "name"),
        connection_status=pick(raw, "connection_status", "connectionStatus"),
        version=pick(raw, "version", "agent_version", "agentVersion"),
        os_type=pick(raw, "os_type", "osType", "platform"),
        ip_address=ip or pick(raw, "ip_address", "ipAddress"),
    )


def _shape_stats(raw: dict[str, Any]) -> AgentStats:
    if not isinstance(raw, dict):
        raw = {}
    return AgentStats(total=pick(raw, "total", "total_count", "totalCount"), data=raw)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListAgentsInput,
    output_view=AgentSummary,
    is_list=True,
)
def zms_list_agents(args: ListAgentsInput) -> list[dict[str, Any]]:
    """List ZMS microsegmentation agents as curated, agent-facing views.

    Read-only. Returns one row per agent (eyez_id, name, connection status,
    version, OS, IP). Requires ZSCALER_CUSTOMER_ID. Use a returned `eyez_id` with
    the agent-group / nonce tools.
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

    result, _, err = client.zms.agents.list_agents(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS agents: {err}")
    return shape_many(nodes_of(result), _shape_agent)


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=AgentStatsInput,
    output_view=AgentStats,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zms_get_agent_connection_status_statistics(args: AgentStatsInput) -> dict[str, Any]:
    """Get ZMS agent connection-status statistics (curated aggregate view).

    Read-only. Returns connected vs disconnected counts / percentages for fleet
    health. Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {"customer_id": customer_id}
    if args.search is not None:
        kwargs["search"] = args.search
    result, _, err = client.zms.agents.get_agent_connection_status_statistics(**kwargs)
    if err:
        raise RuntimeError(f"Failed to get ZMS agent connection statistics: {err}")
    return _shape_stats(result or {}).model_dump()


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=AgentStatsInput,
    output_view=AgentStats,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zms_get_agent_version_statistics(args: AgentStatsInput) -> dict[str, Any]:
    """Get ZMS agent version statistics (curated aggregate view).

    Read-only. Returns the distribution of agent software versions across the
    fleet — useful for spotting outdated agents. Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {"customer_id": customer_id}
    if args.search is not None:
        kwargs["search"] = args.search
    result, _, err = client.zms.agents.get_agent_version_statistics(**kwargs)
    if err:
        raise RuntimeError(f"Failed to get ZMS agent version statistics: {err}")
    return _shape_stats(result or {}).model_dump()
