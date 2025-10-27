"""
ZPA Application Segments Tools

This module provides verb-based tools for managing ZPA application segments.
All related operations are grouped in this single file for maintainability.
"""

from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_application_segments(
    search: Annotated[Optional[str], Field(description="Search term for filtering segments.")] = None,
    page: Annotated[Optional[str], Field(description="Page number for pagination.")] = None,
    page_size: Annotated[Optional[str], Field(description="Number of items per page.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """
    List ZPA application segments with optional filtering and pagination.
    
    🔒 READ-ONLY OPERATION - Safe for autonomous agents.
    
    Args:
        search: Optional search term to filter segments by name
        page: Page number for pagination
        page_size: Number of items per page
        microtenant_id: Optional microtenant ID for scoping
        use_legacy: Whether to use legacy API (default: False)
        service: Service to use (default: "zpa")
        
    Returns:
        List of application segment dictionaries
        
    Examples:
        >>> segments = zpa_list_application_segments()
        >>> segments = zpa_list_application_segments(search="production")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.application_segment
    
    query_params = {"microtenant_id": microtenant_id}
    if search:
        query_params["search"] = search
    if page:
        query_params["page"] = page
    if page_size:
        query_params["page_size"] = page_size
    
    segments, _, err = api.list_segments(query_params=query_params)
    if err:
        raise Exception(f"Failed to list application segments: {err}")
    
    return [s.as_dict() for s in (segments or [])]


def zpa_get_application_segment(
    segment_id: Annotated[str, Field(description="ID of the segment to retrieve.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """
    Get a specific ZPA application segment by ID.
    
    🔒 READ-ONLY OPERATION - Safe for autonomous agents.
    
    Args:
        segment_id: ID of the segment to retrieve (required)
        microtenant_id: Optional microtenant ID for scoping
        use_legacy: Whether to use legacy API (default: False)
        service: Service to use (default: "zpa")
        
    Returns:
        Application segment dictionary
        
    Examples:
        >>> segment = zpa_get_application_segment(segment_id="123456")
    """
    if not segment_id:
        raise ValueError("segment_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.application_segment
    
    segment, _, err = api.get_segment(
        segment_id,
        query_params={"microtenant_id": microtenant_id}
    )
    if err:
        raise Exception(f"Failed to get application segment {segment_id}: {err}")
    
    return segment.as_dict()


# =============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# =============================================================================

def zpa_create_application_segment(
    name: Annotated[str, Field(description="Name of the application segment.")],
    segment_group_id: Annotated[str, Field(description="ID of the segment group.")],
    domain_names: Annotated[Optional[List[str]], Field(description="List of domain names.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the segment.")] = None,
    enabled: Annotated[bool, Field(description="Whether the segment is enabled.")] = True,
    server_group_ids: Annotated[Optional[List[str]], Field(description="List of server group IDs.")] = None,
    tcp_port_range: Annotated[Optional[List[dict]], Field(description="TCP port ranges.")] = None,
    udp_port_range: Annotated[Optional[List[dict]], Field(description="UDP port ranges.")] = None,
    tcp_port_ranges: Annotated[Optional[List[str]], Field(description="TCP port ranges (legacy format).")] = None,
    udp_port_ranges: Annotated[Optional[List[str]], Field(description="UDP port ranges (legacy format).")] = None,
    bypass_type: Annotated[Optional[str], Field(description="Bypass type for the segment.")] = None,
    health_check_type: Annotated[Optional[str], Field(description="Health check type.")] = None,
    health_reporting: Annotated[Optional[str], Field(description="Health reporting configuration.")] = None,
    is_cname_enabled: Annotated[Optional[bool], Field(description="Whether CNAME is enabled.")] = None,
    passive_health_enabled: Annotated[Optional[bool], Field(description="Whether passive health checking is enabled.")] = None,
    clientless_app_ids: Annotated[Optional[List[dict]], Field(description="List of clientless app IDs.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """
    Create a new ZPA application segment.
    
    ⚠️  WRITE OPERATION - Requires --enable-write-tools flag.
    
    Args:
        name: Name of the application segment (required)
        segment_group_id: ID of the segment group (required)
        domain_names: List of domain names for the segment
        description: Optional description
        enabled: Whether the segment is enabled (default: True)
        server_group_ids: List of server group IDs
        tcp_port_range: TCP port ranges [{"from": "80", "to": "80"}]
        udp_port_range: UDP port ranges
        tcp_port_ranges: TCP port ranges in legacy format ["80", "443"]
        udp_port_ranges: UDP port ranges in legacy format
        bypass_type: Bypass type for the segment
        health_check_type: Health check type
        health_reporting: Health reporting configuration
        is_cname_enabled: Whether CNAME is enabled
        passive_health_enabled: Whether passive health checking is enabled
        clientless_app_ids: List of clientless app IDs
        microtenant_id: Optional microtenant ID for scoping
        use_legacy: Whether to use legacy API (default: False)
        service: Service to use (default: "zpa")
        
    Returns:
        Created application segment dictionary
        
    Examples:
        >>> segment = zpa_create_application_segment(
        ...     name="Production App",
        ...     segment_group_id="123456",
        ...     domain_names=["app.example.com"],
        ...     tcp_port_range=[{"from": "443", "to": "443"}]
        ... )
    """
    # Validate required fields
    if not name:
        raise ValueError("name is required")
    if not segment_group_id:
        raise ValueError("segment_group_id is required")
    
    # Validate port configurations
    if (tcp_port_range and tcp_port_ranges) or (udp_port_range and udp_port_ranges):
        raise ValueError(
            "Use either structured port ranges (tcp_port_range/udp_port_range) "
            "or legacy string ranges (tcp_port_ranges/udp_port_ranges), not both."
        )
    if not any([tcp_port_range, udp_port_range, tcp_port_ranges, udp_port_ranges]):
        raise ValueError("At least one port configuration must be provided (TCP or UDP).")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.application_segment
    
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
    
    created, _, err = api.add_segment(**body)
    if err:
        raise Exception(f"Failed to create application segment: {err}")
    
    return created.as_dict()


def zpa_update_application_segment(
    segment_id: Annotated[str, Field(description="ID of the segment to update.")],
    name: Annotated[Optional[str], Field(description="Name of the application segment.")] = None,
    segment_group_id: Annotated[Optional[str], Field(description="ID of the segment group.")] = None,
    domain_names: Annotated[Optional[List[str]], Field(description="List of domain names.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the segment.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the segment is enabled.")] = None,
    server_group_ids: Annotated[Optional[List[str]], Field(description="List of server group IDs.")] = None,
    tcp_port_range: Annotated[Optional[List[dict]], Field(description="TCP port ranges.")] = None,
    udp_port_range: Annotated[Optional[List[dict]], Field(description="UDP port ranges.")] = None,
    tcp_port_ranges: Annotated[Optional[List[str]], Field(description="TCP port ranges (legacy format).")] = None,
    udp_port_ranges: Annotated[Optional[List[str]], Field(description="UDP port ranges (legacy format).")] = None,
    bypass_type: Annotated[Optional[str], Field(description="Bypass type for the segment.")] = None,
    health_check_type: Annotated[Optional[str], Field(description="Health check type.")] = None,
    health_reporting: Annotated[Optional[str], Field(description="Health reporting configuration.")] = None,
    is_cname_enabled: Annotated[Optional[bool], Field(description="Whether CNAME is enabled.")] = None,
    passive_health_enabled: Annotated[Optional[bool], Field(description="Whether passive health checking is enabled.")] = None,
    clientless_app_ids: Annotated[Optional[List[dict]], Field(description="List of clientless app IDs.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """
    Update an existing ZPA application segment.
    
    ⚠️  WRITE OPERATION - Requires --enable-write-tools flag.
    
    Args:
        segment_id: ID of the segment to update (required)
        name: New name for the segment
        segment_group_id: New segment group ID
        domain_names: New list of domain names
        description: New description
        enabled: Whether the segment should be enabled
        server_group_ids: New list of server group IDs
        tcp_port_range: TCP port ranges
        udp_port_range: UDP port ranges
        tcp_port_ranges: TCP port ranges in legacy format
        udp_port_ranges: UDP port ranges in legacy format
        bypass_type: Bypass type for the segment
        health_check_type: Health check type
        health_reporting: Health reporting configuration
        is_cname_enabled: Whether CNAME is enabled
        passive_health_enabled: Whether passive health checking is enabled
        clientless_app_ids: List of clientless app IDs
        microtenant_id: Optional microtenant ID for scoping
        use_legacy: Whether to use legacy API (default: False)
        service: Service to use (default: "zpa")
        
    Returns:
        Updated application segment dictionary
        
    Examples:
        >>> segment = zpa_update_application_segment(
        ...     segment_id="123456",
        ...     name="Updated Production App"
        ... )
    """
    if not segment_id:
        raise ValueError("segment_id is required for update")
    
    if (tcp_port_range and tcp_port_ranges) or (udp_port_range and udp_port_ranges):
        raise ValueError(
            "Use either structured port ranges (tcp_port_range/udp_port_range) "
            "or legacy string ranges (tcp_port_ranges/udp_port_ranges), not both."
        )
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.application_segment
    
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
        raise Exception(f"Failed to update application segment {segment_id}: {err}")
    
    return updated.as_dict()


def zpa_delete_application_segment(
    segment_id: Annotated[str, Field(description="ID of the segment to delete.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """
    Delete a ZPA application segment.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.
    
    Args:
        segment_id: ID of the segment to delete (required)
        microtenant_id: Optional microtenant ID for scoping
        use_legacy: Whether to use legacy API (default: False)
        service: Service to use (default: "zpa")
        
    Returns:
        Success message string or confirmation message
        
    Examples:
        >>> result = zpa_delete_application_segment(segment_id="123456")
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_application_segment",
        confirmed,
        {"segment_id": segment_id}
    )
    if confirmation_check:
        return confirmation_check
    
    if not segment_id:
        raise ValueError("segment_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.application_segment
    
    _, _, err = api.delete_segment(segment_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete application segment {segment_id}: {err}")
    
    return f"Successfully deleted application segment {segment_id}"
