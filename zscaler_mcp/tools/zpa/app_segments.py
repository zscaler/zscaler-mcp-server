from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def app_segment_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', or 'delete'."
        ),
    ],
    segment_id: Annotated[
        str, Field(description="Segment ID for read, update, or delete operations.")
    ] = None,
    microtenant_id: Annotated[
        str, Field(description="Microtenant ID for scoping operations.")
    ] = None,
    name: Annotated[str, Field(description="Name of the application segment.")] = None,
    description: Annotated[
        str, Field(description="Description of the application segment.")
    ] = None,
    enabled: Annotated[
        bool, Field(description="Whether the segment is enabled.")
    ] = True,
    domain_names: Annotated[
        List[str], Field(description="List of domain names for the segment.")
    ] = None,
    segment_group_id: Annotated[
        str, Field(description="ID of the segment group.")
    ] = None,
    server_group_ids: Annotated[
        List[str], Field(description="List of server group IDs.")
    ] = None,
    tcp_port_range: Annotated[
        List[dict], Field(description="TCP port ranges in new format.")
    ] = None,
    udp_port_range: Annotated[
        List[dict], Field(description="UDP port ranges in new format.")
    ] = None,
    tcp_port_ranges: Annotated[
        List[str], Field(description="TCP port ranges in legacy string format.")
    ] = None,
    udp_port_ranges: Annotated[
        List[str], Field(description="UDP port ranges in legacy string format.")
    ] = None,
    bypass_type: Annotated[
        str, Field(description="Bypass type for the segment.")
    ] = None,
    health_check_type: Annotated[str, Field(description="Health check type.")] = None,
    health_reporting: Annotated[
        str, Field(description="Health reporting configuration.")
    ] = None,
    is_cname_enabled: Annotated[
        bool, Field(description="Whether CNAME is enabled.")
    ] = None,
    passive_health_enabled: Annotated[
        bool, Field(description="Whether passive health checking is enabled.")
    ] = None,
    clientless_app_ids: Annotated[
        List[dict], Field(description="List of clientless app IDs.")
    ] = None,
    search: Annotated[
        str, Field(description="Search term for filtering results.")
    ] = None,
    page: Annotated[str, Field(description="Page number for pagination.")] = None,
    page_size: Annotated[str, Field(description="Number of items per page.")] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[dict, List[dict], str]:
    """
    CRUD handler for ZPA Application Segments via the Python SDK.

    Required fields:
    - create: name, segment_group_id, at least one of tcp/udp port ranges
    - update: segment_id, at least one field to modify
    - delete: segment_id

    Port range options (mutually exclusive):
    - tcp_port_range / udp_port_range (new format)
    - tcp_port_ranges / udp_port_ranges (legacy string list format)

    You may specify only one format per protocol and only one protocol if desired.
    """

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    api = client.zpa.application_segment

    def validate_ports():
        if (tcp_port_range and tcp_port_ranges) or (udp_port_range and udp_port_ranges):
            raise ValueError(
                "Use either structured port ranges (tcp_port_range/udp_port_range) or legacy string ranges (tcp_port_ranges/udp_port_ranges), not both."
            )
        if not any([tcp_port_range, udp_port_range, tcp_port_ranges, udp_port_ranges]):
            raise ValueError(
                "At least one port configuration must be provided (TCP or UDP)."
            )

    if action == "create":
        if not segment_group_id:
            raise ValueError("segment_group_id is required for creation")
        validate_ports()

        body = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "domain_names": domain_names,
            "segment_group_id": segment_group_id,
            "server_group_ids": server_group_ids,
            "bypass_type": bypass_type,
            "health_check_type": health_check_type,
            "health_reporting": health_reporting,
            "is_cname_enabled": is_cname_enabled,
            "passive_health_enabled": passive_health_enabled,
            "clientless_app_ids": clientless_app_ids,
        }

        # Merge correct port fields
        if tcp_port_range:
            body["tcp_port_range"] = tcp_port_range
        elif tcp_port_ranges:
            body["tcp_port_ranges"] = tcp_port_ranges

        if udp_port_range:
            body["udp_port_range"] = udp_port_range
        elif udp_port_ranges:
            body["udp_port_ranges"] = udp_port_ranges

        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        created, _, err = api.add_segment(**body)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if segment_id:
            segment, _, err = api.get_segment(
                segment_id, query_params={"microtenant_id": microtenant_id}
            )
            if err:
                raise Exception(f"Read failed: {err}")
            return segment.as_dict()
        else:
            qp = {"microtenant_id": microtenant_id}
            if search:
                qp["search"] = search
            if page:
                qp["page"] = page
            if page_size:
                qp["page_size"] = page_size

            segments, _, err = api.list_segments(query_params=qp)
            if err:
                raise Exception(f"List failed: {err}")
            return [s.as_dict() for s in (segments or [])]

    elif action == "update":
        if not segment_id:
            raise ValueError("segment_id is required for update")
        validate_ports()

        body = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "domain_names": domain_names,
            "segment_group_id": segment_group_id,
            "server_group_ids": server_group_ids,
            "bypass_type": bypass_type,
            "health_check_type": health_check_type,
            "health_reporting": health_reporting,
            "is_cname_enabled": is_cname_enabled,
            "passive_health_enabled": passive_health_enabled,
            "clientless_app_ids": clientless_app_ids,
        }

        if tcp_port_range:
            body["tcp_port_range"] = tcp_port_range
        elif tcp_port_ranges:
            body["tcp_port_ranges"] = tcp_port_ranges

        if udp_port_range:
            body["udp_port_range"] = udp_port_range
        elif udp_port_ranges:
            body["udp_port_ranges"] = udp_port_ranges

        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        updated, _, err = api.update_segment(segment_id, **body)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not segment_id:
            raise ValueError("segment_id is required for delete")
        _, _, err = api.delete_segment(segment_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted segment {segment_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
