from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List
from pydantic import Field


def gre_tunnel_manager(
    action: Annotated[
        str, Field(description="Action to perform: 'create', 'read', or 'delete'.")
    ],
    tunnel_id: Annotated[
        int, Field(description="Tunnel ID for read or delete operations.")
    ] = None,
    static_ip_id: Annotated[
        int, Field(description="Static IP ID for delete operations.")
    ] = None,
    static_ip_address: Annotated[
        str, Field(description="Required to associate or create a static IP.")
    ] = None,
    internal_ip_range: Annotated[
        str, Field(description="Internal IP range for the GRE tunnel.")
    ] = None,
    ip_unnumbered: Annotated[
        bool,
        Field(
            description="If True, tunnel will be unnumbered; if False, a GRE IP range will be selected."
        ),
    ] = None,
    comment: Annotated[
        str, Field(description="Comment for the GRE tunnel or static IP.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing ZIA GRE Tunnels and associated static IPs.

    Supported actions:
    - create: Requires static_ip_address (existing or new). For numbered tunnels, the tool will fetch GRE ranges.
    - read: List all GRE tunnels or retrieve one by tunnel_id.
    - delete: Deletes GRE tunnel first, then static IP.

    Args:
        ip_unnumbered (bool): If True, tunnel will be unnumbered; if False, a GRE IP range will be selected.
        static_ip_address (str): Required to associate or create a static IP.

    Deletion behavior:
    - If this resource is associated with a static ip OR vpn credential,
      the GRE tunnel must be deleted first.

    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    gre_api = client.zia.gre_tunnel
    ip_api = client.zia.traffic_static_ip

    if action == "create":
        # Check or create static IP first
        existing_ips, _, err = ip_api.list_static_ips(
            query_params={"ip_address": static_ip_address}
        )
        if err:
            raise Exception(f"Failed to search static IP: {err}")

        if existing_ips:
            static_ip = existing_ips[0]
        else:
            static_ip, _, err = ip_api.add_static_ip(
                ip_address=static_ip_address, comment=comment
            )
            if err:
                raise Exception(f"Failed to create static IP: {err}")

        payload = {
            "source_ip": static_ip.ip_address,
            "ip_unnumbered": ip_unnumbered,
            "internal_ip_range": internal_ip_range,
            "comment": comment,
        }

        if not ip_unnumbered:
            gre_ranges, _, err = gre_api.list_gre_ranges(
                query_params={"static_ip": static_ip.ip_address}
            )
            if err:
                raise Exception(f"Failed to fetch GRE ranges: {err}")
            if not gre_ranges or "startIPAddress" not in gre_ranges[0]:
                raise Exception(
                    "No valid GRE internal IP ranges found in the response."
                )
            payload["internal_ip_range"] = gre_ranges[0]["startIPAddress"]

        tunnel, _, err = gre_api.add_gre_tunnel(**payload)
        if err:
            raise Exception(f"Failed to create GRE tunnel: {err}")
        return tunnel.as_dict()

    elif action == "read":
        if tunnel_id:
            tunnel, _, err = gre_api.get_gre_tunnel(tunnel_id)
            if err:
                raise Exception(f"Failed to retrieve GRE tunnel {tunnel_id}: {err}")
            return tunnel.as_dict()
        else:
            tunnels, _, err = gre_api.list_gre_tunnels()
            if err:
                raise Exception(f"Failed to list GRE tunnels: {err}")
            return [t.as_dict() for t in tunnels]

    elif action == "delete":
        if not tunnel_id or not static_ip_id:
            raise ValueError("Both tunnel_id and static_ip_id are required for delete")

        _, _, err = gre_api.delete_gre_tunnel(tunnel_id)
        if err:
            raise Exception(f"Failed to delete GRE tunnel {tunnel_id}: {err}")

        _, _, err = ip_api.delete_static_ip(static_ip_id)
        if err:
            raise Exception(f"Failed to delete static IP {static_ip_id}: {err}")

        return f"Deleted GRE tunnel {tunnel_id} and static IP {static_ip_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
