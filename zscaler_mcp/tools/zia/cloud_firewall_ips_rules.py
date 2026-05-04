"""ZIA Cloud Firewall IPS Rules MCP Tools.

Cloud Firewall IPS rules govern Intrusion Prevention System actions on
network traffic flowing through the ZIA cloud firewall — allow, drop,
reset, or bypass IPS for matching traffic.

Each action is exposed as its own MCP tool: ``zia_list_*``, ``zia_get_*``,
``zia_create_*``, ``zia_update_*``, ``zia_delete_*``.

ZIA's IPS rule update endpoint is a PUT (full replacement). To keep partial
updates safe, ``zia_update_cloud_firewall_ips_rule`` silently backfills
``name`` and ``order`` from the existing rule when the caller does not
supply them.
"""

from typing import Annotated, Any, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.common.zia_helpers import (
    ORDER_FIELD_DESCRIPTION,
    RANK_FIELD_DESCRIPTION,
    apply_default_order,
    apply_default_rank,
    validate_order,
    validate_rank,
)
from zscaler_mcp.utils.utils import parse_list

# ============================================================================
# Helper Functions
# ============================================================================


def _build_ips_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    rule_action: Optional[str] = None,
    enable_full_logging: Optional[bool] = None,
    capture_pcap: Optional[bool] = None,
    predefined: Optional[bool] = None,
    default_rule: Optional[bool] = None,
    file_types: Optional[Union[List[str], str]] = None,
    protocols: Optional[Union[List[str], str]] = None,
    dest_addresses: Optional[Union[List[str], str]] = None,
    dest_countries: Optional[Union[List[str], str]] = None,
    dest_ip_categories: Optional[Union[List[str], str]] = None,
    dest_ip_groups: Optional[Union[List[int], str]] = None,
    dest_ipv6_groups: Optional[Union[List[int], str]] = None,
    src_ips: Optional[Union[List[str], str]] = None,
    source_countries: Optional[Union[List[str], str]] = None,
    src_ip_groups: Optional[Union[List[int], str]] = None,
    src_ipv6_groups: Optional[Union[List[int], str]] = None,
    res_categories: Optional[Union[List[str], str]] = None,
    threat_categories: Optional[Union[List[int], str]] = None,
    nw_services: Optional[Union[List[int], str]] = None,
    nw_service_groups: Optional[Union[List[int], str]] = None,
    devices: Optional[Union[List[int], str]] = None,
    device_groups: Optional[Union[List[int], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    zpa_app_segments: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for Cloud Firewall IPS rule operations."""
    payload: dict = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if enabled is not None:
        payload["enabled"] = enabled
    if rank is not None:
        payload["rank"] = rank
    if order is not None:
        payload["order"] = order
    if rule_action is not None:
        payload["action"] = rule_action
    if enable_full_logging is not None:
        payload["enable_full_logging"] = enable_full_logging
    if capture_pcap is not None:
        payload["capture_pcap"] = capture_pcap
    if predefined is not None:
        payload["predefined"] = predefined
    if default_rule is not None:
        payload["default_rule"] = default_rule

    for param_name, param_value in [
        ("file_types", file_types),
        ("protocols", protocols),
        ("dest_addresses", dest_addresses),
        ("dest_countries", dest_countries),
        ("dest_ip_categories", dest_ip_categories),
        ("dest_ip_groups", dest_ip_groups),
        ("dest_ipv6_groups", dest_ipv6_groups),
        ("src_ips", src_ips),
        ("source_countries", source_countries),
        ("src_ip_groups", src_ip_groups),
        ("src_ipv6_groups", src_ipv6_groups),
        ("res_categories", res_categories),
        ("threat_categories", threat_categories),
        ("nw_services", nw_services),
        ("nw_service_groups", nw_service_groups),
        ("devices", devices),
        ("device_groups", device_groups),
        ("locations", locations),
        ("location_groups", location_groups),
        ("groups", groups),
        ("users", users),
        ("time_windows", time_windows),
        ("labels", labels),
        ("zpa_app_segments", zpa_app_segments),
    ]:
        if param_value is not None:
            payload[param_name] = parse_list(param_value)

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zia_list_cloud_firewall_ips_rules(
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """
    Lists ZIA Cloud Firewall IPS Rules.

    IPS rules govern Intrusion Prevention System enforcement on traffic
    matched by the ZIA cloud firewall (allow, block-drop, block-reset, or
    bypass IPS scanning). This is a read-only operation. Supports JMESPath
    client-side filtering via the ``query`` parameter.

    Returns:
        list[dict]: Cloud Firewall IPS rule records.
    """
    client = get_zscaler_client(service=service)
    ips = client.zia.cloud_firewall_ips

    query_params = {"search": search} if search else {}
    rules, _, err = ips.list_rules(query_params=query_params)
    if err:
        raise Exception(f"Failed to list Cloud Firewall IPS rules: {err}")
    results = [r.as_dict() for r in (rules or [])]
    return apply_jmespath(results, query)


def zia_get_cloud_firewall_ips_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Cloud Firewall IPS rule to retrieve.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA Cloud Firewall IPS Rule by ID.

    Returns:
        dict: The Cloud Firewall IPS rule record.
    """
    client = get_zscaler_client(service=service)
    ips = client.zia.cloud_firewall_ips

    rule, _, err = ips.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve Cloud Firewall IPS rule {rule_id}: {err}")
    return rule.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================


def zia_create_cloud_firewall_ips_rule(
    name: Annotated[str, Field(description="Rule name (max 31 chars).")],
    rule_action: Annotated[
        str,
        Field(
            description=(
                "Action when traffic matches. Supported values: ALLOW, "
                "BLOCK_DROP, BLOCK_RESET, BYPASS_IPS."
            )
        ),
    ],
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = True,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description=ORDER_FIELD_DESCRIPTION)] = None,
    enable_full_logging: Annotated[
        Optional[bool], Field(description="If True, enables full logging.")
    ] = None,
    capture_pcap: Annotated[
        Optional[bool], Field(description="Enable packet capture (PCAP) for this rule.")
    ] = None,
    predefined: Annotated[Optional[bool], Field(description="Predefined rule flag.")] = None,
    default_rule: Annotated[
        Optional[bool], Field(description="Indicates the default Cloud IPS rule.")
    ] = None,
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="File types the rule applies to. Accepts JSON string or list."),
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocol criteria. Accepts JSON string or list."),
    ] = None,
    dest_addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination IPs/CIDRs. Accepts JSON string or list."),
    ] = None,
    dest_countries: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination countries. Accepts JSON string or list."),
    ] = None,
    dest_ip_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination IP address categories. Accepts JSON string or list."),
    ] = None,
    dest_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IP groups.")
    ] = None,
    dest_ipv6_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IPv6 groups.")
    ] = None,
    src_ips: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Source IPs/CIDRs. Accepts JSON string or list."),
    ] = None,
    source_countries: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Source countries. Accepts JSON string or list."),
    ] = None,
    src_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for source IP groups.")
    ] = None,
    src_ipv6_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for source IPv6 groups.")
    ] = None,
    res_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Resolved IP address categories. Accepts JSON string or list."),
    ] = None,
    threat_categories: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for threat categories.")
    ] = None,
    nw_services: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network services.")
    ] = None,
    nw_service_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network service groups.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for devices managed by Zscaler Client Connector."),
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for device groups.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for user groups.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels.")
    ] = None,
    zpa_app_segments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for ZPA app segments.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a ZIA Cloud Firewall IPS Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    Returns:
        dict: The created Cloud Firewall IPS rule.
    """
    rank = apply_default_rank(rank)
    order = apply_default_order(order)
    payload = _build_ips_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        rule_action=rule_action,
        enable_full_logging=enable_full_logging,
        capture_pcap=capture_pcap,
        predefined=predefined,
        default_rule=default_rule,
        file_types=file_types,
        protocols=protocols,
        dest_addresses=dest_addresses,
        dest_countries=dest_countries,
        dest_ip_categories=dest_ip_categories,
        dest_ip_groups=dest_ip_groups,
        dest_ipv6_groups=dest_ipv6_groups,
        src_ips=src_ips,
        source_countries=source_countries,
        src_ip_groups=src_ip_groups,
        src_ipv6_groups=src_ipv6_groups,
        res_categories=res_categories,
        threat_categories=threat_categories,
        nw_services=nw_services,
        nw_service_groups=nw_service_groups,
        devices=devices,
        device_groups=device_groups,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        users=users,
        time_windows=time_windows,
        labels=labels,
        zpa_app_segments=zpa_app_segments,
    )

    client = get_zscaler_client(service=service)
    ips = client.zia.cloud_firewall_ips

    rule, _, err = ips.add_rule(**payload)
    if err:
        raise Exception(f"Failed to create Cloud Firewall IPS rule: {err}")
    return rule.as_dict()


def zia_update_cloud_firewall_ips_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Cloud Firewall IPS rule to update.")
    ],
    name: Annotated[Optional[str], Field(description="Rule name (max 31 chars).")] = None,
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = None,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description=ORDER_FIELD_DESCRIPTION)] = None,
    rule_action: Annotated[
        Optional[str],
        Field(description="Action. Values: ALLOW, BLOCK_DROP, BLOCK_RESET, BYPASS_IPS."),
    ] = None,
    enable_full_logging: Annotated[Optional[bool], Field(description="Enable full logging.")] = None,
    capture_pcap: Annotated[Optional[bool], Field(description="Enable PCAP.")] = None,
    predefined: Annotated[Optional[bool], Field(description="Predefined rule flag.")] = None,
    default_rule: Annotated[Optional[bool], Field(description="Default IPS rule flag.")] = None,
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="File types. Accepts JSON string or list."),
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocols. Accepts JSON string or list."),
    ] = None,
    dest_addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination IPs/CIDRs."),
    ] = None,
    dest_countries: Annotated[
        Optional[Union[List[str], str]], Field(description="Destination countries.")
    ] = None,
    dest_ip_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination IP address categories."),
    ] = None,
    dest_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IP groups.")
    ] = None,
    dest_ipv6_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IPv6 groups.")
    ] = None,
    src_ips: Annotated[
        Optional[Union[List[str], str]], Field(description="Source IPs/CIDRs.")
    ] = None,
    source_countries: Annotated[
        Optional[Union[List[str], str]], Field(description="Source countries.")
    ] = None,
    src_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for source IP groups.")
    ] = None,
    src_ipv6_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for source IPv6 groups.")
    ] = None,
    res_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Resolved IP address categories."),
    ] = None,
    threat_categories: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for threat categories.")
    ] = None,
    nw_services: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network services.")
    ] = None,
    nw_service_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network service groups.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for devices managed by Zscaler Client Connector."),
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for device groups.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for user groups.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels.")
    ] = None,
    zpa_app_segments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for ZPA app segments.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates a ZIA Cloud Firewall IPS Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    The IPS rule update endpoint is a PUT (full replacement). This tool
    silently backfills ``name`` and ``order`` from the existing rule when
    the caller does not supply them, so partial updates "just work".

    Returns:
        dict: The updated Cloud Firewall IPS rule.
    """
    if rank is not None:
        rank = validate_rank(rank)
    if order is not None:
        order = validate_order(order)
    payload = _build_ips_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        rule_action=rule_action,
        enable_full_logging=enable_full_logging,
        capture_pcap=capture_pcap,
        predefined=predefined,
        default_rule=default_rule,
        file_types=file_types,
        protocols=protocols,
        dest_addresses=dest_addresses,
        dest_countries=dest_countries,
        dest_ip_categories=dest_ip_categories,
        dest_ip_groups=dest_ip_groups,
        dest_ipv6_groups=dest_ipv6_groups,
        src_ips=src_ips,
        source_countries=source_countries,
        src_ip_groups=src_ip_groups,
        src_ipv6_groups=src_ipv6_groups,
        res_categories=res_categories,
        threat_categories=threat_categories,
        nw_services=nw_services,
        nw_service_groups=nw_service_groups,
        devices=devices,
        device_groups=device_groups,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        users=users,
        time_windows=time_windows,
        labels=labels,
        zpa_app_segments=zpa_app_segments,
    )

    client = get_zscaler_client(service=service)
    ips = client.zia.cloud_firewall_ips

    if "name" not in payload or "order" not in payload:
        existing, _, fetch_err = ips.get_rule(rule_id)
        if fetch_err:
            raise Exception(
                f"Failed to fetch Cloud Firewall IPS rule {rule_id} for required-field backfill: {fetch_err}"
            )
        existing_dict = existing.as_dict()
        payload.setdefault("name", existing_dict.get("name"))
        payload.setdefault("order", existing_dict.get("order"))

    rule, _, err = ips.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update Cloud Firewall IPS rule {rule_id}: {err}")
    return rule.as_dict()


def zia_delete_cloud_firewall_ips_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Cloud Firewall IPS rule to delete.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """
    Deletes a ZIA Cloud Firewall IPS Rule by ID.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Returns:
        str: Success message confirming deletion.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zia_delete_cloud_firewall_ips_rule", confirmed, {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check

    client = get_zscaler_client(service=service)
    ips = client.zia.cloud_firewall_ips

    _, _, err = ips.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete Cloud Firewall IPS rule {rule_id}: {err}")
    return f"Cloud Firewall IPS rule {rule_id} deleted successfully."
