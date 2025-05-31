from zscaler_mcp.sdk.zscaler_client import get_zscaler_client

def connector_group_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    group_id: str = None,
    microtenant_id: str = None,
    name: str = None,
    description: str = None,
    enabled: bool = True,
    latitude: str = None,
    longitude: str = None,
    location: str = None,
    city_country: str = None,
    country_code: str = None,
    dns_query_type: str = None,
    override_version_profile: bool = None,
    server_group_ids: list[str] = None,
    connector_ids: list[str] = None,
    lss_app_connector_group: bool = None,
    upgrade_day: str = None,
    upgrade_time_in_secs: str = None,
    version_profile: str = None,
    search: str = None,
    page: str = None,
    page_size: str = None,
) -> dict | list[dict] | str:
    """
    CRUD handler for ZPA App Connector Groups via the Python SDK.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    api = client.zpa.app_connector_groups

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
            "dns_query_type": dns_query_type,
            "override_version_profile": override_version_profile,
            "server_group_ids": server_group_ids or [],
            "connector_ids": connector_ids or [],
            "lss_app_connector_group": lss_app_connector_group,
            "upgrade_day": upgrade_day,
            "upgrade_time_in_secs": upgrade_time_in_secs,
            "version_profile": version_profile,
        }
        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        created, _, err = api.add_connector_group(**body)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if group_id:
            group, _, err = api.get_connector_group(
                group_id, query_params={"microtenant_id": microtenant_id}
            )
            if err:
                raise Exception(f"Read failed: {err}")
            return group.as_dict()
        else:
            qp = {"microtenant_id": microtenant_id}
            if search:
                qp["search"] = search
            if page:
                qp["page"] = page
            if page_size:
                qp["page_size"] = page_size

            groups, _, err = api.list_connector_groups(query_params=qp)
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
            "dns_query_type": dns_query_type,
            "override_version_profile": override_version_profile,
            "server_group_ids": server_group_ids or [],
            "connector_ids": connector_ids or [],
            "lss_app_connector_group": lss_app_connector_group,
            "upgrade_day": upgrade_day,
            "upgrade_time_in_secs": upgrade_time_in_secs,
            "version_profile": version_profile,
        }

        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        updated, _, err = api.update_connector_group(group_id, **body)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete")
        _, _, err = api.delete_connector_group(group_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted app connector group {group_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
