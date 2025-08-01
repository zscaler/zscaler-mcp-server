from zscaler_mcp.client import get_zscaler_client
from typing import Union, List
from typing import Annotated
from pydantic import Field


def service_edge_group_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', or 'delete'."
        ),
    ],
    group_id: Annotated[
        str, Field(description="Group ID for read, update, or delete operations.")
    ] = None,
    microtenant_id: Annotated[
        str, Field(description="Microtenant ID for scoping operations.")
    ] = None,
    query_params: Annotated[
        dict,
        Field(
            description="Optional query parameters for filtering, searching, pagination, or microtenant scoping."
        ),
    ] = None,
    name: Annotated[str, Field(description="Name of the service edge group.")] = None,
    description: Annotated[
        str, Field(description="Description of the service edge group.")
    ] = None,
    enabled: Annotated[bool, Field(description="Whether the group is enabled.")] = True,
    latitude: Annotated[str, Field(description="Latitude coordinate.")] = None,
    longitude: Annotated[str, Field(description="Longitude coordinate.")] = None,
    location: Annotated[str, Field(description="Location name.")] = None,
    city_country: Annotated[
        str, Field(description="City and country information.")
    ] = None,
    country_code: Annotated[str, Field(description="Country code.")] = None,
    is_public: Annotated[
        bool, Field(description="Whether the group is public.")
    ] = None,
    override_version_profile: Annotated[
        bool, Field(description="Whether to override version profile.")
    ] = None,
    version_profile_name: Annotated[
        str, Field(description="Version profile name.")
    ] = None,
    version_profile_id: Annotated[str, Field(description="Version profile ID.")] = None,
    service_edge_ids: Annotated[
        List[str], Field(description="List of service edge IDs.")
    ] = None,
    trusted_network_ids: Annotated[
        List[str], Field(description="List of trusted network IDs.")
    ] = None,
    grace_distance_enabled: Annotated[
        bool, Field(description="Whether grace distance is enabled.")
    ] = None,
    grace_distance_value: Annotated[
        int, Field(description="Grace distance value.")
    ] = None,
    grace_distance_value_unit: Annotated[
        str, Field(description="Grace distance value unit.")
    ] = None,
    upgrade_day: Annotated[str, Field(description="Upgrade day.")] = None,
    upgrade_time_in_secs: Annotated[
        str, Field(description="Upgrade time in seconds.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[dict, List[dict], str]:
    """
    CRUD handler for ZPA Service Edge Groups via the Python SDK.

    Required fields:
    - create: name, latitude, longitude, location
    - update: group_id
    - delete: group_id

    The query_params argument may be used for filtering, searching, pagination, or microtenant scoping.
    """

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    api = client.zpa.service_edge_group

    if action == "create":
        body = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "latitude": latitude,
            "longitude": longitude,
            "location": location,
            "city_country": city_country,
            "country_code": country_code,
            "is_public": is_public,
            "override_version_profile": override_version_profile,
            "version_profile_name": version_profile_name,
            "version_profile_id": version_profile_id,
            "grace_distance_enabled": grace_distance_enabled,
            "grace_distance_value": grace_distance_value,
            "grace_distance_value_unit": grace_distance_value_unit,
            "upgrade_day": upgrade_day,
            "upgrade_time_in_secs": upgrade_time_in_secs,
        }

        if microtenant_id:
            body["microtenant_id"] = microtenant_id
        if trusted_network_ids:
            body["trusted_network_ids"] = trusted_network_ids
        if service_edge_ids:
            body["service_edge_ids"] = service_edge_ids

        created, _, err = api.add_service_edge_group(**body)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if group_id:
            group, _, err = api.get_service_edge_group(
                group_id, query_params={"microtenant_id": microtenant_id}
            )
            if err:
                raise Exception(f"Read failed: {err}")
            return group.as_dict()
        else:
            query_params = query_params or {}
            if microtenant_id:
                query_params["microtenant_id"] = microtenant_id

            groups, _, err = api.list_service_edge_groups(query_params=query_params)
            if err:
                raise Exception(f"List failed: {err}")
            return [g.as_dict() for g in (groups or [])]

    elif action == "update":
        if not group_id:
            raise ValueError("group_id is required for update")

        body = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "latitude": latitude,
            "longitude": longitude,
            "location": location,
            "city_country": city_country,
            "country_code": country_code,
            "is_public": is_public,
            "override_version_profile": override_version_profile,
            "version_profile_name": version_profile_name,
            "version_profile_id": version_profile_id,
            "grace_distance_enabled": grace_distance_enabled,
            "grace_distance_value": grace_distance_value,
            "grace_distance_value_unit": grace_distance_value_unit,
            "upgrade_day": upgrade_day,
            "upgrade_time_in_secs": upgrade_time_in_secs,
        }

        if microtenant_id:
            body["microtenant_id"] = microtenant_id
        if trusted_network_ids:
            body["trusted_network_ids"] = trusted_network_ids
        if service_edge_ids:
            body["service_edge_ids"] = service_edge_ids

        updated, _, err = api.update_service_edge_group(group_id, **body)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete")
        _, _, err = api.delete_service_edge_group(
            group_id, microtenant_id=microtenant_id
        )
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted service edge group {group_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
