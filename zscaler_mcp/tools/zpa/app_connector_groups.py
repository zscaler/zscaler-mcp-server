from zscaler_mcp.client import get_zscaler_client
from typing import Union, List
from typing import Annotated
from pydantic import Field


def connector_group_manager(
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
    name: Annotated[str, Field(description="Name of the connector group.")] = None,
    description: Annotated[
        str, Field(description="Description of the connector group.")
    ] = None,
    enabled: Annotated[bool, Field(description="Whether the group is enabled.")] = True,
    latitude: Annotated[str, Field(description="Latitude coordinate.")] = None,
    longitude: Annotated[str, Field(description="Longitude coordinate.")] = None,
    location: Annotated[str, Field(description="Location name.")] = None,
    city_country: Annotated[
        str, Field(description="City and country information.")
    ] = None,
    country_code: Annotated[str, Field(description="Country code.")] = None,
    dns_query_type: Annotated[str, Field(description="DNS query type.")] = None,
    override_version_profile: Annotated[
        bool, Field(description="Whether to override version profile.")
    ] = None,
    server_group_ids: Annotated[
        List[str], Field(description="List of server group IDs.")
    ] = None,
    connector_ids: Annotated[
        List[str], Field(description="List of connector IDs.")
    ] = None,
    lss_app_connector_group: Annotated[
        bool, Field(description="Whether this is an LSS app connector group.")
    ] = None,
    upgrade_day: Annotated[str, Field(description="Upgrade day.")] = None,
    upgrade_time_in_secs: Annotated[
        str, Field(description="Upgrade time in seconds.")
    ] = None,
    version_profile: Annotated[str, Field(description="Version profile.")] = None,
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
    CRUD handler for ZPA App Connector Groups via the Python SDK.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

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
