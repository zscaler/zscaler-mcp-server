"""ZIA network services — list/get/create/update/delete.

Mirrors v1's ``network_services.py``. Backed by ``client.zia.cloud_firewall``.
Writes are staged until ``zia_activate_configuration``.

Ports use v1's tuple grammar: ``[["src"|"dest", "tcp"|"udp", start, end?]]``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one


class ListServicesInput(BaseModel):
    name: Annotated[
        Optional[str],
        Field(default=None, description="Case-insensitive substring match on the service name."),
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Server-side query (case-sensitive).")
    ] = None
    protocol: Annotated[
        Optional[str],
        Field(default=None, description="Filter by protocol: ICMP, TCP, UDP, GRE, ESP, OTHER."),
    ] = None


class GetServiceInput(BaseModel):
    service_id: Annotated[str, Field(description="Network service ID (string, even if numeric).")]


class CreateServiceInput(BaseModel):
    name: Annotated[str, Field(description="Name for the network service.")]
    ports: Annotated[
        list[list[str]],
        Field(
            description=(
                'Port tuples: [["src"|"dest", "tcp"|"udp", start, end?]]. '
                'E.g. [["dest","tcp","443"]] or [["dest","tcp","80","443"]].'
            )
        ),
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class UpdateServiceInput(BaseModel):
    service_id: Annotated[str, Field(description="Service ID to update.")]
    name: Annotated[str, Field(description="Name (required by API on update).")]
    ports: Annotated[
        Optional[list[list[str]]],
        Field(default=None, description="Port tuples; if provided REPLACES existing ports."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class DeleteServiceInput(BaseModel):
    service_id: Annotated[str, Field(description="Service ID to delete.")]


class PortRange(BaseModel):
    start: Optional[int] = Field(default=None, description="Start port.")
    end: Optional[int] = Field(default=None, description="End port (range only).")


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _ports(ports: Optional[list[list[str]]]) -> Optional[list[tuple]]:
    parsed = parse_list(ports) if ports is not None else None
    if parsed is None:
        return None
    return [tuple(p) if isinstance(p, list) else p for p in parsed]


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=ListServicesInput,
    is_list=True,
)
def zia_list_network_services(args: ListServicesInput) -> list[dict[str, Any]]:
    """List ZIA network services. Use `name` for case-insensitive find-by-name."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.name is None and args.search:
        qp["search"] = args.search
    if args.protocol:
        qp["protocol"] = args.protocol.upper()
    services, _, err = client.zia.cloud_firewall.list_network_services(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list network services: {err}")
    rows = [s.as_dict() for s in (services or [])]
    if args.name:
        needle = args.name.strip().lower()
        rows = [r for r in rows if needle in str(r.get("name", "")).lower()]
    return shape_many(rows)


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetServiceInput,
    is_list=False,
)
def zia_get_network_service(args: GetServiceInput) -> dict[str, Any]:
    """Get a single ZIA network service by ID with its port definitions."""
    client = get_zscaler_client(service="zia")
    svc, _, err = client.zia.cloud_firewall.get_network_service(args.service_id)
    if err:
        raise RuntimeError(f"Failed to get network service {args.service_id}: {err}")
    return shape_one(svc.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=CreateServiceInput,
    is_list=False,
)
def zia_create_network_service(args: CreateServiceInput) -> dict[str, Any]:
    """Create a custom ZIA network service (write). Activate after."""
    client = get_zscaler_client(service="zia")
    kwargs: dict[str, Any] = {"name": args.name}
    if args.description:
        kwargs["description"] = args.description
    svc, _, err = client.zia.cloud_firewall.add_network_service(ports=_ports(args.ports), **kwargs)
    if err:
        raise RuntimeError(f"Failed to create network service: {err}")
    return shape_one(svc.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=UpdateServiceInput,
    is_list=False,
)
def zia_update_network_service(args: UpdateServiceInput) -> dict[str, Any]:
    """Update a ZIA network service (write). Ports, if given, replace existing. Activate after."""
    client = get_zscaler_client(service="zia")
    kwargs: dict[str, Any] = {"name": args.name}
    if args.description is not None:
        kwargs["description"] = args.description
    if args.ports is not None:
        kwargs["ports"] = _ports(args.ports)
    svc, _, err = client.zia.cloud_firewall.update_network_service(args.service_id, **kwargs)
    if err:
        raise RuntimeError(f"Failed to update network service {args.service_id}: {err}")
    return shape_one(svc.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=DeleteServiceInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_network_service(args: DeleteServiceInput) -> dict[str, Any]:
    """Delete a ZIA network service (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.cloud_firewall.delete_network_service(args.service_id)
    if err:
        raise RuntimeError(f"Failed to delete network service {args.service_id}: {err}")
    return OperationResult(
        success=True, message=f"Network service {args.service_id} deleted successfully."
    ).model_dump()
