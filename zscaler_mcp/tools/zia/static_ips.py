from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List
from pydantic import Field


def static_ip_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', or 'delete'."
        ),
    ],
    static_ip_id: Annotated[
        int, Field(description="Static IP ID for read, update, or delete operations.")
    ] = None,
    ip_address: Annotated[
        str, Field(description="IP address (required for create).")
    ] = None,
    comment: Annotated[
        str, Field(description="Optional comment for the static IP.")
    ] = None,
    geo_override: Annotated[
        bool, Field(description="Whether to override geolocation.")
    ] = None,
    routable_ip: Annotated[
        bool, Field(description="Whether the IP is routable.")
    ] = None,
    latitude: Annotated[
        float, Field(description="Latitude for geolocation override.")
    ] = None,
    longitude: Annotated[
        float, Field(description="Longitude for geolocation override.")
    ] = None,
    query_params: Annotated[
        dict, Field(description="Optional query parameters for filtering results.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing ZIA Static IP addresses.

    Supported actions:
    - create: Requires ip_address. Optional: comment, geo_override, routable_ip, latitude, longitude.
    - read: List all or retrieve one by static_ip_id.
    - update: Requires static_ip_id. IP address cannot be changed.
    - delete: Requires static_ip_id.

    Deletion behavior:
    - If this resource is associated with a vpn credential or a GRE Tunnel,
      the GRE Tunnel must be deleted first.

    Returns:
        dict | list[dict] | str
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    api = client.zia.traffic_static_ip

    if action == "create":
        if not ip_address:
            raise ValueError("ip_address is required for creating a static IP")

        payload = {
            "ip_address": ip_address,
            "comment": comment,
            "geo_override": geo_override,
            "routable_ip": routable_ip,
            "latitude": latitude,
            "longitude": longitude,
        }

        created, _, err = api.add_static_ip(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if static_ip_id:
            result, _, err = api.get_static_ip(static_ip_id)
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            results, _, err = api.list_static_ips(query_params=query_params)
            if err:
                raise Exception(f"List failed: {err}")
            return [r.as_dict() for r in results]

    elif action == "update":
        if not static_ip_id:
            raise ValueError("static_ip_id is required for update")

        update_data = {
            "comment": comment,
            "geo_override": geo_override,
            "routable_ip": routable_ip,
            "latitude": latitude,
            "longitude": longitude,
        }

        updated, _, err = api.update_static_ip(static_ip_id, **update_data)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not static_ip_id:
            raise ValueError("static_ip_id is required for deletion")

        _, _, err = api.delete_static_ip(static_ip_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted static IP {static_ip_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
