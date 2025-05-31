from zscaler_mcp.sdk.zscaler_client import get_zscaler_client

def service_edge_group_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    group_id: str = None,
    microtenant_id: str = None,
    query_params: dict = None,
    name: str = None,
    description: str = None,
    enabled: bool = True,
    latitude: str = None,
    longitude: str = None,
    location: str = None,
    city_country: str = None,
    country_code: str = None,
    is_public: bool = None,
    override_version_profile: bool = None,
    version_profile_name: str = None,
    version_profile_id: str = None,
    service_edge_ids: list[str] = None,
    trusted_network_ids: list[str] = None,
    grace_distance_enabled: bool = None,
    grace_distance_value: int = None,
    grace_distance_value_unit: str = None,
    upgrade_day: str = None,
    upgrade_time_in_secs: str = None,
) -> dict | list[dict] | str:
    """
    CRUD handler for ZPA Service Edge Groups via the Python SDK.

    Required fields:
    - create: name, latitude, longitude, location
    - update: group_id
    - delete: group_id

    The query_params argument may be used for filtering, searching, pagination, or microtenant scoping.
    """

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

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
        _, _, err = api.delete_service_edge_group(group_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted service edge group {group_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
