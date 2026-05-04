"""
ZPA Application Segments Tools

This module provides verb-based tools for managing ZPA application segments.
All related operations are grouped in this single file for maintainability.
"""

from typing import Annotated, Dict, List, Literal, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zpa_list_application_segments(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring match on the application segment's `name` field. "
                "Returns the full set of matches in this tenant — no fuzzy matching, no "
                "synonym expansion. An empty list means no segment name contains this "
                "string; do not retry with split keywords or no filter."
            )
        ),
    ] = None,
    page: Annotated[Optional[str], Field(description="Page number for pagination.")] = None,
    page_size: Annotated[Optional[str], Field(description="Number of items per page.")] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """
    List ZPA application segments with optional filtering and pagination.

    Supports JMESPath client-side filtering via the query parameter.

    🔒 READ-ONLY OPERATION - Safe for autonomous agents.

    Args:
        search: Optional search term to filter segments by name
        page: Page number for pagination
        page_size: Number of items per page
        microtenant_id: Optional microtenant ID for scoping
        query: JMESPath expression for client-side filtering/projection
        service: Service to use (default: "zpa")

    Returns:
        List of application segment dictionaries

    Examples:
        >>> segments = zpa_list_application_segments()
        >>> segments = zpa_list_application_segments(search="production")
    """
    client = get_zscaler_client(service=service)
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

    results = [s.as_dict() for s in (segments or [])]
    return apply_jmespath(results, query)


def zpa_get_application_segment(
    segment_id: Annotated[str, Field(description="ID of the segment to retrieve.")],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """
    Get a specific ZPA application segment by ID.

    🔒 READ-ONLY OPERATION - Safe for autonomous agents.

    Args:
        segment_id: ID of the segment to retrieve (required)
        microtenant_id: Optional microtenant ID for scoping
        service: Service to use (default: "zpa")

    Returns:
        Application segment dictionary

    Examples:
        >>> segment = zpa_get_application_segment(segment_id="123456")
    """
    if not segment_id:
        raise ValueError("segment_id is required")

    client = get_zscaler_client(service=service)
    api = client.zpa.application_segment

    segment, _, err = api.get_segment(segment_id, query_params={"microtenant_id": microtenant_id})
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
    server_group_ids: Annotated[
        Optional[List[str]], Field(description="List of server group IDs.")
    ] = None,
    tcp_port_range: Annotated[Optional[List[dict]], Field(description="TCP port ranges.")] = None,
    udp_port_range: Annotated[Optional[List[dict]], Field(description="UDP port ranges.")] = None,
    tcp_port_ranges: Annotated[
        Optional[List[str]], Field(description="TCP port ranges as a flat string list.")
    ] = None,
    udp_port_ranges: Annotated[
        Optional[List[str]], Field(description="UDP port ranges as a flat string list.")
    ] = None,
    bypass_type: Annotated[Optional[str], Field(description="Bypass type for the segment.")] = None,
    health_check_type: Annotated[Optional[str], Field(description="Health check type.")] = None,
    health_reporting: Annotated[
        Optional[str], Field(description="Health reporting configuration.")
    ] = None,
    is_cname_enabled: Annotated[
        Optional[bool], Field(description="Whether CNAME is enabled.")
    ] = None,
    passive_health_enabled: Annotated[
        Optional[bool], Field(description="Whether passive health checking is enabled.")
    ] = None,
    clientless_app_ids: Annotated[
        Optional[List[dict]], Field(description="List of clientless app IDs.")
    ] = None,
    icmp_access_type: Annotated[
        Optional[Literal["NONE", "PING", "PING_TRACEROUTING"]],
        Field(
            description=(
                "Controls whether the application segment responds to ICMP. "
                "`NONE` disables ICMP, `PING` allows ping, `PING_TRACEROUTING` allows "
                "ping plus traceroute. Defaults to `NONE` server-side when omitted."
            )
        ),
    ] = None,
    double_encrypt: Annotated[
        Optional[bool],
        Field(description="Enable double encryption for the segment."),
    ] = None,
    config_space: Annotated[
        Optional[Literal["DEFAULT", "SIEM"]],
        Field(
            description="Configuration space for the segment. `DEFAULT` for normal app segments."
        ),
    ] = None,
    ip_anchored: Annotated[
        Optional[bool],
        Field(description="Whether the application segment is IP-anchored."),
    ] = None,
    bypass_on_reauth: Annotated[
        Optional[bool],
        Field(description="Bypass the application segment when the user re-authenticates."),
    ] = None,
    inspect_traffic_with_zia: Annotated[
        Optional[bool],
        Field(
            description=(
                "Enable Source IP Anchoring — forwards traffic from this segment through "
                "ZIA for inspection. Requires a corresponding ZIA configuration."
            )
        ),
    ] = None,
    use_in_dr_mode: Annotated[
        Optional[bool],
        Field(description="Enable this segment in Disaster Recovery (DR) mode."),
    ] = None,
    tcp_keep_alive: Annotated[
        Optional[str],
        Field(
            description=(
                "Enable TCP keep-alive for the segment. API expects a string flag "
                "(`'1'` to enable, `'0'` to disable)."
            )
        ),
    ] = None,
    select_connector_close_to_app: Annotated[
        Optional[bool],
        Field(
            description=(
                "Prefer App Connectors that are network-close to the application "
                "(rather than network-close to the user)."
            )
        ),
    ] = None,
    match_style: Annotated[
        Optional[Literal["INCLUSIVE", "EXCLUSIVE"]],
        Field(
            description=(
                "Domain-name matching style. `INCLUSIVE` (default) matches any listed "
                "domain; `EXCLUSIVE` requires an exact match for the FQDN."
            )
        ),
    ] = None,
    adp_enabled: Annotated[
        Optional[bool],
        Field(description="Enable AppProtection Discovery (ADP) on this segment."),
    ] = None,
    auto_app_protect_enabled: Annotated[
        Optional[bool],
        Field(description="Enable auto-AppProtection (recommended profiles auto-applied)."),
    ] = None,
    api_protection_enabled: Annotated[
        Optional[bool],
        Field(description="Enable API protection on this segment."),
    ] = None,
    fqdn_dns_check: Annotated[
        Optional[bool],
        Field(
            description=(
                "Validate that the segment's domain names resolve via DNS before "
                "the API accepts the configuration."
            )
        ),
    ] = None,
    weighted_load_balancing: Annotated[
        Optional[bool],
        Field(description="Enable weighted load balancing across server groups."),
    ] = None,
    extranet_enabled: Annotated[
        Optional[bool],
        Field(description="Enable Extranet (`zpnErId`) consumption for this segment."),
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
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
        tcp_port_ranges: TCP port ranges as a flat string list ["80", "443"]
        udp_port_ranges: UDP port ranges as a flat string list
        bypass_type: Bypass type for the segment
        health_check_type: Health check type
        health_reporting: Health reporting configuration
        is_cname_enabled: Whether CNAME is enabled
        passive_health_enabled: Whether passive health checking is enabled
        clientless_app_ids: List of clientless app IDs
        icmp_access_type: ICMP behaviour: "NONE", "PING", or "PING_TRACEROUTING"
        double_encrypt: Enable double encryption for the segment
        config_space: Configuration space ("DEFAULT" or "SIEM")
        ip_anchored: Whether the segment is IP-anchored
        bypass_on_reauth: Bypass on user re-authentication
        inspect_traffic_with_zia: Forward segment traffic through ZIA (Source IP Anchoring)
        use_in_dr_mode: Enable in Disaster Recovery mode
        tcp_keep_alive: TCP keep-alive flag ("1" enable / "0" disable)
        select_connector_close_to_app: Prefer App Connectors close to the app vs. user
        match_style: Domain matching style ("INCLUSIVE" or "EXCLUSIVE")
        adp_enabled: Enable AppProtection Discovery
        auto_app_protect_enabled: Enable auto-AppProtection
        api_protection_enabled: Enable API protection
        fqdn_dns_check: Validate domain names resolve via DNS
        weighted_load_balancing: Enable weighted load balancing
        extranet_enabled: Enable Extranet for this segment
        microtenant_id: Optional microtenant ID for scoping
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
        >>> segment = zpa_create_application_segment(
        ...     name="Internal API",
        ...     segment_group_id="123456",
        ...     domain_names=["api.internal"],
        ...     tcp_port_ranges=["443", "443"],
        ...     icmp_access_type="PING",
        ...     inspect_traffic_with_zia=True,
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
            "or flat string ranges (tcp_port_ranges/udp_port_ranges), not both."
        )
    if not any([tcp_port_range, udp_port_range, tcp_port_ranges, udp_port_ranges]):
        raise ValueError("At least one port configuration must be provided (TCP or UDP).")

    client = get_zscaler_client(service=service)
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
        "icmp_access_type": icmp_access_type,
        "double_encrypt": double_encrypt,
        "config_space": config_space,
        "ip_anchored": ip_anchored,
        "bypass_on_reauth": bypass_on_reauth,
        "inspect_traffic_with_zia": inspect_traffic_with_zia,
        "use_in_dr_mode": use_in_dr_mode,
        "tcp_keep_alive": tcp_keep_alive,
        "select_connector_close_to_app": select_connector_close_to_app,
        "match_style": match_style,
        "adp_enabled": adp_enabled,
        "auto_app_protect_enabled": auto_app_protect_enabled,
        "api_protection_enabled": api_protection_enabled,
        "fqdn_dns_check": fqdn_dns_check,
        "weighted_load_balancing": weighted_load_balancing,
        "extranet_enabled": extranet_enabled,
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
    segment_group_id: Annotated[
        Optional[str], Field(description="ID of the segment group.")
    ] = None,
    domain_names: Annotated[Optional[List[str]], Field(description="List of domain names.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the segment.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the segment is enabled.")] = None,
    server_group_ids: Annotated[
        Optional[List[str]], Field(description="List of server group IDs.")
    ] = None,
    tcp_port_range: Annotated[Optional[List[dict]], Field(description="TCP port ranges.")] = None,
    udp_port_range: Annotated[Optional[List[dict]], Field(description="UDP port ranges.")] = None,
    tcp_port_ranges: Annotated[
        Optional[List[str]], Field(description="TCP port ranges as a flat string list.")
    ] = None,
    udp_port_ranges: Annotated[
        Optional[List[str]], Field(description="UDP port ranges as a flat string list.")
    ] = None,
    bypass_type: Annotated[Optional[str], Field(description="Bypass type for the segment.")] = None,
    health_check_type: Annotated[Optional[str], Field(description="Health check type.")] = None,
    health_reporting: Annotated[
        Optional[str], Field(description="Health reporting configuration.")
    ] = None,
    is_cname_enabled: Annotated[
        Optional[bool], Field(description="Whether CNAME is enabled.")
    ] = None,
    passive_health_enabled: Annotated[
        Optional[bool], Field(description="Whether passive health checking is enabled.")
    ] = None,
    clientless_app_ids: Annotated[
        Optional[List[dict]], Field(description="List of clientless app IDs.")
    ] = None,
    icmp_access_type: Annotated[
        Optional[Literal["NONE", "PING", "PING_TRACEROUTING"]],
        Field(
            description=(
                "Controls whether the application segment responds to ICMP. "
                "`NONE` disables ICMP, `PING` allows ping, `PING_TRACEROUTING` allows "
                "ping plus traceroute."
            )
        ),
    ] = None,
    double_encrypt: Annotated[
        Optional[bool],
        Field(description="Enable double encryption for the segment."),
    ] = None,
    config_space: Annotated[
        Optional[Literal["DEFAULT", "SIEM"]],
        Field(description="Configuration space for the segment."),
    ] = None,
    ip_anchored: Annotated[
        Optional[bool],
        Field(description="Whether the application segment is IP-anchored."),
    ] = None,
    bypass_on_reauth: Annotated[
        Optional[bool],
        Field(description="Bypass the application segment when the user re-authenticates."),
    ] = None,
    inspect_traffic_with_zia: Annotated[
        Optional[bool],
        Field(
            description=(
                "Forward segment traffic through ZIA for inspection (Source IP Anchoring)."
            )
        ),
    ] = None,
    use_in_dr_mode: Annotated[
        Optional[bool],
        Field(description="Enable this segment in Disaster Recovery (DR) mode."),
    ] = None,
    tcp_keep_alive: Annotated[
        Optional[str],
        Field(
            description=(
                "Enable TCP keep-alive for the segment. API expects a string flag "
                "(`'1'` to enable, `'0'` to disable)."
            )
        ),
    ] = None,
    select_connector_close_to_app: Annotated[
        Optional[bool],
        Field(
            description=(
                "Prefer App Connectors that are network-close to the application "
                "(rather than network-close to the user)."
            )
        ),
    ] = None,
    match_style: Annotated[
        Optional[Literal["INCLUSIVE", "EXCLUSIVE"]],
        Field(description="Domain-name matching style (`INCLUSIVE` or `EXCLUSIVE`)."),
    ] = None,
    adp_enabled: Annotated[
        Optional[bool],
        Field(description="Enable AppProtection Discovery (ADP) on this segment."),
    ] = None,
    auto_app_protect_enabled: Annotated[
        Optional[bool],
        Field(description="Enable auto-AppProtection."),
    ] = None,
    api_protection_enabled: Annotated[
        Optional[bool],
        Field(description="Enable API protection on this segment."),
    ] = None,
    fqdn_dns_check: Annotated[
        Optional[bool],
        Field(description="Validate that the segment's domain names resolve via DNS."),
    ] = None,
    weighted_load_balancing: Annotated[
        Optional[bool],
        Field(description="Enable weighted load balancing across server groups."),
    ] = None,
    extranet_enabled: Annotated[
        Optional[bool],
        Field(description="Enable Extranet (`zpnErId`) consumption for this segment."),
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
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
        tcp_port_ranges: TCP port ranges as a flat string list
        udp_port_ranges: UDP port ranges as a flat string list
        bypass_type: Bypass type for the segment
        health_check_type: Health check type
        health_reporting: Health reporting configuration
        is_cname_enabled: Whether CNAME is enabled
        passive_health_enabled: Whether passive health checking is enabled
        clientless_app_ids: List of clientless app IDs
        icmp_access_type: ICMP behaviour: "NONE", "PING", or "PING_TRACEROUTING"
        double_encrypt: Enable double encryption for the segment
        config_space: Configuration space ("DEFAULT" or "SIEM")
        ip_anchored: Whether the segment is IP-anchored
        bypass_on_reauth: Bypass on user re-authentication
        inspect_traffic_with_zia: Forward segment traffic through ZIA (Source IP Anchoring)
        use_in_dr_mode: Enable in Disaster Recovery mode
        tcp_keep_alive: TCP keep-alive flag ("1" enable / "0" disable)
        select_connector_close_to_app: Prefer App Connectors close to the app vs. user
        match_style: Domain matching style ("INCLUSIVE" or "EXCLUSIVE")
        adp_enabled: Enable AppProtection Discovery
        auto_app_protect_enabled: Enable auto-AppProtection
        api_protection_enabled: Enable API protection
        fqdn_dns_check: Validate domain names resolve via DNS
        weighted_load_balancing: Enable weighted load balancing
        extranet_enabled: Enable Extranet for this segment
        microtenant_id: Optional microtenant ID for scoping
        service: Service to use (default: "zpa")

    Returns:
        Updated application segment dictionary

    Examples:
        >>> segment = zpa_update_application_segment(
        ...     segment_id="123456",
        ...     name="Updated Production App"
        ... )
        >>> segment = zpa_update_application_segment(
        ...     segment_id="123456",
        ...     icmp_access_type="PING",
        ...     inspect_traffic_with_zia=True,
        ... )
    """
    if not segment_id:
        raise ValueError("segment_id is required for update")

    if (tcp_port_range and tcp_port_ranges) or (udp_port_range and udp_port_ranges):
        raise ValueError(
            "Use either structured port ranges (tcp_port_range/udp_port_range) "
            "or flat string ranges (tcp_port_ranges/udp_port_ranges), not both."
        )

    client = get_zscaler_client(service=service)
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
        "icmp_access_type": icmp_access_type,
        "double_encrypt": double_encrypt,
        "config_space": config_space,
        "ip_anchored": ip_anchored,
        "bypass_on_reauth": bypass_on_reauth,
        "inspect_traffic_with_zia": inspect_traffic_with_zia,
        "use_in_dr_mode": use_in_dr_mode,
        "tcp_keep_alive": tcp_keep_alive,
        "select_connector_close_to_app": select_connector_close_to_app,
        "match_style": match_style,
        "adp_enabled": adp_enabled,
        "auto_app_protect_enabled": auto_app_protect_enabled,
        "api_protection_enabled": api_protection_enabled,
        "fqdn_dns_check": fqdn_dns_check,
        "weighted_load_balancing": weighted_load_balancing,
        "extranet_enabled": extranet_enabled,
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
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}",
) -> str:
    """
    Delete a ZPA application segment.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Args:
        segment_id: ID of the segment to delete (required)
        microtenant_id: Optional microtenant ID for scoping
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
        "zpa_delete_application_segment", confirmed, {"segment_id": segment_id}
    )
    if confirmation_check:
        return confirmation_check

    if not segment_id:
        raise ValueError("segment_id is required for delete")

    client = get_zscaler_client(service=service)
    api = client.zpa.application_segment

    _, _, err = api.delete_segment(segment_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete application segment {segment_id}: {err}")

    return f"Successfully deleted application segment {segment_id}"
