from zscaler_mcp.sdk.python.zscaler_client import get_zscaler_client

def app_segment_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    segment_id: str = None,
    microtenant_id: str = None,
    name: str = None,
    description: str = None,
    enabled: bool = True,
    domain_names: list[str] = None,
    segment_group_id: str = None,
    server_group_ids: list[str] = None,
    tcp_port_range: list[dict] = None,
    udp_port_range: list[dict] = None,
    tcp_port_ranges: list[str] = None,
    udp_port_ranges: list[str] = None,
    bypass_type: str = None,
    health_check_type: str = None,
    health_reporting: str = None,
    is_cname_enabled: bool = None,
    passive_health_enabled: bool = None,
    clientless_app_ids: list[dict] = None,
    search: str = None,
    page: str = None,
    page_size: str = None,
) -> dict | list[dict] | str:
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

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    api = client.zpa.application_segment

    def validate_ports():
        if (tcp_port_range and tcp_port_ranges) or (udp_port_range and udp_port_ranges):
            raise ValueError("Use either structured port ranges (tcp_port_range/udp_port_range) or legacy string ranges (tcp_port_ranges/udp_port_ranges), not both.")
        if not any([tcp_port_range, udp_port_range, tcp_port_ranges, udp_port_ranges]):
            raise ValueError("At least one port configuration must be provided (TCP or UDP).")

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
            segment, _, err = api.get_segment(segment_id, query_params={"microtenant_id": microtenant_id})
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
