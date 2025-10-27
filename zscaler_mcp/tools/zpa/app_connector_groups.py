from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.utils.utils import validate_and_convert_country_code_iso

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_app_connector_groups(
    search: Annotated[Optional[str], Field(description="Search term for filtering results.")] = None,
    page: Annotated[Optional[str], Field(description="Page number for pagination.")] = None,
    page_size: Annotated[Optional[str], Field(description="Number of items per page.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA app connector groups with optional filtering and pagination."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connector_groups
    
    qp = {"microtenant_id": microtenant_id}
    if search:
        qp["search"] = search
    if page:
        qp["page"] = page
    if page_size:
        qp["page_size"] = page_size
    
    groups, _, err = api.list_connector_groups(query_params=qp)
    if err:
        raise Exception(f"Failed to list app connector groups: {err}")
    return [g.as_dict() for g in (groups or [])]


def zpa_get_app_connector_group(
    group_id: Annotated[str, Field(description="Group ID for the app connector group.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA app connector group by ID."""
    if not group_id:
        raise ValueError("group_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connector_groups
    
    group, _, err = api.get_connector_group(group_id, query_params={"microtenant_id": microtenant_id})
    if err:
        raise Exception(f"Failed to get app connector group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_app_connector_group(
    name: Annotated[str, Field(description="Name of the connector group.")],
    description: Annotated[Optional[str], Field(description="Description of the connector group.")] = None,
    enabled: Annotated[bool, Field(description="Whether the group is enabled.")] = True,
    latitude: Annotated[Optional[str], Field(description="Latitude coordinate.")] = None,
    longitude: Annotated[Optional[str], Field(description="Longitude coordinate.")] = None,
    location: Annotated[Optional[str], Field(description="Location name.")] = None,
    city_country: Annotated[Optional[str], Field(description="City and country information.")] = None,
    country_code: Annotated[Optional[str], Field(description="Country code (e.g., 'Canada', 'US', 'CA', 'GB'). Will be converted to ISO alpha-2 format.")] = None,
    dns_query_type: Annotated[Optional[str], Field(description="DNS query type.")] = None,
    override_version_profile: Annotated[Optional[bool], Field(description="Whether to override version profile.")] = None,
    server_group_ids: Annotated[Optional[List[str]], Field(description="List of server group IDs.")] = None,
    connector_ids: Annotated[Optional[List[str]], Field(description="List of connector IDs.")] = None,
    lss_app_connector_group: Annotated[Optional[bool], Field(description="Whether this is an LSS app connector group.")] = None,
    upgrade_day: Annotated[Optional[str], Field(description="Upgrade day.")] = None,
    upgrade_time_in_secs: Annotated[Optional[str], Field(description="Upgrade time in seconds.")] = None,
    version_profile: Annotated[Optional[str], Field(description="Version profile.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA app connector group."""
    if not name:
        raise ValueError("name is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    
    # Validate and convert country code if provided
    if country_code:
        try:
            country_code = validate_and_convert_country_code_iso(country_code)
        except ValueError as e:
            raise ValueError(f"Invalid country code: {e}")
    
    api = client.zpa.app_connector_groups
    
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
        raise Exception(f"Failed to create app connector group: {err}")
    return created.as_dict()


def zpa_update_app_connector_group(
    group_id: Annotated[str, Field(description="Group ID for the app connector group.")],
    name: Annotated[Optional[str], Field(description="Name of the connector group.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the connector group.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the group is enabled.")] = None,
    latitude: Annotated[Optional[str], Field(description="Latitude coordinate.")] = None,
    longitude: Annotated[Optional[str], Field(description="Longitude coordinate.")] = None,
    location: Annotated[Optional[str], Field(description="Location name.")] = None,
    city_country: Annotated[Optional[str], Field(description="City and country information.")] = None,
    country_code: Annotated[Optional[str], Field(description="Country code (e.g., 'Canada', 'US', 'CA', 'GB'). Will be converted to ISO alpha-2 format.")] = None,
    dns_query_type: Annotated[Optional[str], Field(description="DNS query type.")] = None,
    override_version_profile: Annotated[Optional[bool], Field(description="Whether to override version profile.")] = None,
    server_group_ids: Annotated[Optional[List[str]], Field(description="List of server group IDs.")] = None,
    connector_ids: Annotated[Optional[List[str]], Field(description="List of connector IDs.")] = None,
    lss_app_connector_group: Annotated[Optional[bool], Field(description="Whether this is an LSS app connector group.")] = None,
    upgrade_day: Annotated[Optional[str], Field(description="Upgrade day.")] = None,
    upgrade_time_in_secs: Annotated[Optional[str], Field(description="Upgrade time in seconds.")] = None,
    version_profile: Annotated[Optional[str], Field(description="Version profile.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA app connector group."""
    if not group_id:
        raise ValueError("group_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    
    # Validate and convert country code if provided
    if country_code:
        try:
            country_code = validate_and_convert_country_code_iso(country_code)
        except ValueError as e:
            raise ValueError(f"Invalid country code: {e}")
    
    api = client.zpa.app_connector_groups
    
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
        raise Exception(f"Failed to update app connector group {group_id}: {err}")
    return updated.as_dict()


def zpa_delete_app_connector_group(
    group_id: Annotated[str, Field(description="Group ID for the app connector group.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA app connector group."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_app_connector_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not group_id:
        raise ValueError("group_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connector_groups
    
    _, _, err = api.delete_connector_group(group_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete app connector group {group_id}: {err}")
    return f"Successfully deleted app connector group {group_id}"
