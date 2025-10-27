from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.utils.utils import validate_and_convert_country_code_iso

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_service_edge_groups(
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering, searching, or pagination.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA service edge groups with optional filtering and pagination."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.service_edge_group
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    groups, _, err = api.list_service_edge_groups(query_params=qp)
    if err:
        raise Exception(f"Failed to list service edge groups: {err}")
    return [g.as_dict() for g in (groups or [])]


def zpa_get_service_edge_group(
    group_id: Annotated[str, Field(description="Group ID for the service edge group.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA service edge group by ID."""
    if not group_id:
        raise ValueError("group_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.service_edge_group
    
    group, _, err = api.get_service_edge_group(group_id, query_params={"microtenant_id": microtenant_id})
    if err:
        raise Exception(f"Failed to get service edge group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_service_edge_group(
    name: Annotated[str, Field(description="Name of the service edge group.")],
    latitude: Annotated[str, Field(description="Latitude coordinate.")],
    longitude: Annotated[str, Field(description="Longitude coordinate.")],
    location: Annotated[str, Field(description="Location name.")],
    description: Annotated[Optional[str], Field(description="Description of the service edge group.")] = None,
    enabled: Annotated[bool, Field(description="Whether the group is enabled.")] = True,
    city_country: Annotated[Optional[str], Field(description="City and country information.")] = None,
    country_code: Annotated[Optional[str], Field(description="Country code (e.g., 'Canada', 'US', 'CA', 'GB'). Will be converted to ISO alpha-2 format.")] = None,
    is_public: Annotated[Optional[bool], Field(description="Whether the group is public.")] = None,
    override_version_profile: Annotated[Optional[bool], Field(description="Whether to override version profile.")] = None,
    version_profile_name: Annotated[Optional[str], Field(description="Version profile name.")] = None,
    version_profile_id: Annotated[Optional[str], Field(description="Version profile ID.")] = None,
    service_edge_ids: Annotated[Optional[List[str]], Field(description="List of service edge IDs.")] = None,
    trusted_network_ids: Annotated[Optional[List[str]], Field(description="List of trusted network IDs.")] = None,
    grace_distance_enabled: Annotated[Optional[bool], Field(description="Whether grace distance is enabled.")] = None,
    grace_distance_value: Annotated[Optional[int], Field(description="Grace distance value.")] = None,
    grace_distance_value_unit: Annotated[Optional[str], Field(description="Grace distance value unit.")] = None,
    upgrade_day: Annotated[Optional[str], Field(description="Upgrade day.")] = None,
    upgrade_time_in_secs: Annotated[Optional[str], Field(description="Upgrade time in seconds.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA service edge group."""
    if not all([name, latitude, longitude, location]):
        raise ValueError("name, latitude, longitude, and location are required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    
    # Validate and convert country code if provided
    if country_code:
        try:
            country_code = validate_and_convert_country_code_iso(country_code)
        except ValueError as e:
            raise ValueError(f"Invalid country code: {e}")
    
    api = client.zpa.service_edge_group
    
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
        raise Exception(f"Failed to create service edge group: {err}")
    return created.as_dict()


def zpa_update_service_edge_group(
    group_id: Annotated[str, Field(description="Group ID for the service edge group.")],
    name: Annotated[Optional[str], Field(description="Name of the service edge group.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the service edge group.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the group is enabled.")] = None,
    latitude: Annotated[Optional[str], Field(description="Latitude coordinate.")] = None,
    longitude: Annotated[Optional[str], Field(description="Longitude coordinate.")] = None,
    location: Annotated[Optional[str], Field(description="Location name.")] = None,
    city_country: Annotated[Optional[str], Field(description="City and country information.")] = None,
    country_code: Annotated[Optional[str], Field(description="Country code (e.g., 'Canada', 'US', 'CA', 'GB'). Will be converted to ISO alpha-2 format.")] = None,
    is_public: Annotated[Optional[bool], Field(description="Whether the group is public.")] = None,
    override_version_profile: Annotated[Optional[bool], Field(description="Whether to override version profile.")] = None,
    version_profile_name: Annotated[Optional[str], Field(description="Version profile name.")] = None,
    version_profile_id: Annotated[Optional[str], Field(description="Version profile ID.")] = None,
    service_edge_ids: Annotated[Optional[List[str]], Field(description="List of service edge IDs.")] = None,
    trusted_network_ids: Annotated[Optional[List[str]], Field(description="List of trusted network IDs.")] = None,
    grace_distance_enabled: Annotated[Optional[bool], Field(description="Whether grace distance is enabled.")] = None,
    grace_distance_value: Annotated[Optional[int], Field(description="Grace distance value.")] = None,
    grace_distance_value_unit: Annotated[Optional[str], Field(description="Grace distance value unit.")] = None,
    upgrade_day: Annotated[Optional[str], Field(description="Upgrade day.")] = None,
    upgrade_time_in_secs: Annotated[Optional[str], Field(description="Upgrade time in seconds.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA service edge group."""
    if not group_id:
        raise ValueError("group_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    
    # Validate and convert country code if provided
    if country_code:
        try:
            country_code = validate_and_convert_country_code_iso(country_code)
        except ValueError as e:
            raise ValueError(f"Invalid country code: {e}")
    
    api = client.zpa.service_edge_group
    
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
        raise Exception(f"Failed to update service edge group {group_id}: {err}")
    return updated.as_dict()


def zpa_delete_service_edge_group(
    group_id: Annotated[str, Field(description="Group ID for the service edge group.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA service edge group."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_service_edge_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not group_id:
        raise ValueError("group_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.service_edge_group
    
    _, _, err = api.delete_service_edge_group(group_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete service edge group {group_id}: {err}")
    return f"Successfully deleted service edge group {group_id}"
