"""ZIA Cloud Firewall DNS Rules MCP Tools.

Cloud Firewall DNS rules govern how DNS traffic is allowed, blocked, or
redirected by the ZIA cloud firewall — they are evaluated alongside the
broader ZIA cloud-firewall and IPS rule sets but operate specifically on
DNS request/response semantics.

Each action is exposed as its own MCP tool: ``zia_list_*``, ``zia_get_*``,
``zia_create_*``, ``zia_update_*``, ``zia_delete_*``.

ZIA's DNS rule update endpoint is a PUT (full replacement). To keep partial
updates safe, ``zia_update_cloud_firewall_dns_rule`` silently backfills
``name`` and ``order`` from the existing rule when the caller does not
supply them — same pattern as ssl_inspection.

The ``applications`` attribute on DNS rules accepts the same canonical
ZIA cloud-application names used by SSL Inspection / Web DLP / File Type
Control / Cloud App Control — the field is just named ``applications``
on this rule type instead of ``cloud_applications``. The DNS-related
sub-categories (DNS tunnels, network apps, DNS-over-HTTPS providers)
live inside that same catalog. Friendly display names supplied by the
caller (e.g. "OneDrive", "Cloudflare DoH") are auto-resolved to canonical
names via :func:`zscaler_mcp.common.zia_helpers.resolve_cloud_applications`
before the API call.
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
    resolve_cloud_applications,
    validate_order,
    validate_rank,
)
from zscaler_mcp.utils.utils import parse_list

# ============================================================================
# Helper Functions
# ============================================================================


def _resolve_cloud_apps_in_place(
    applications: Optional[Union[List[str], str]],
    *,
    service: str,
) -> tuple[Optional[List[str]], Optional[dict]]:
    """Translate friendly cloud-app inputs to canonical names.

    Returns ``(resolved, audit)``. ``audit`` is ``None`` when the inputs
    were already canonical (no transformation happened) or when no inputs
    were provided. Mirrors the helper used by ssl_inspection.py and
    file_type_control_rules.py — kept as its own function (rather than
    imported from a sibling) to avoid cross-tool import churn.
    """
    if applications is None:
        return None, None

    parsed = parse_list(applications)
    if not parsed:
        return parsed, None

    resolved, audit = resolve_cloud_applications(
        parsed,
        scope="policy",
        service=service,
        strict=True,
    )

    transformed = False
    for original, info in audit["resolved"].items():
        enums = info["enums"]
        if info["match"] != "canonical" or [original] != enums:
            transformed = True
            break

    return resolved, (audit if transformed else None)


def _build_dns_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    rule_action: Optional[str] = None,
    redirect_ip: Optional[str] = None,
    enable_full_logging: Optional[bool] = None,
    capture_pcap: Optional[bool] = None,
    predefined: Optional[bool] = None,
    default_rule: Optional[bool] = None,
    block_response_code: Optional[str] = None,
    dns_gateway: Optional[Union[int, str]] = None,
    edns_ecs_object: Optional[Union[int, str]] = None,
    zpa_ip_group: Optional[Union[int, str]] = None,
    applications: Optional[Union[List[str], str]] = None,
    application_groups: Optional[Union[List[int], str]] = None,
    protocols: Optional[Union[List[str], str]] = None,
    dns_rule_request_types: Optional[Union[List[str], str]] = None,
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
    devices: Optional[Union[List[int], str]] = None,
    device_groups: Optional[Union[List[int], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    departments: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for Cloud Firewall DNS rule operations."""
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
    if redirect_ip is not None:
        payload["redirect_ip"] = redirect_ip
    if enable_full_logging is not None:
        payload["enable_full_logging"] = enable_full_logging
    if capture_pcap is not None:
        payload["capture_pcap"] = capture_pcap
    if predefined is not None:
        payload["predefined"] = predefined
    if default_rule is not None:
        payload["default_rule"] = default_rule
    if block_response_code is not None:
        payload["block_response_code"] = block_response_code
    if dns_gateway is not None:
        payload["dns_gateway"] = dns_gateway
    if edns_ecs_object is not None:
        payload["edns_ecs_object"] = edns_ecs_object
    if zpa_ip_group is not None:
        payload["zpa_ip_group"] = zpa_ip_group

    for param_name, param_value in [
        ("applications", applications),
        ("application_groups", application_groups),
        ("protocols", protocols),
        ("dns_rule_request_types", dns_rule_request_types),
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
        ("devices", devices),
        ("device_groups", device_groups),
        ("locations", locations),
        ("location_groups", location_groups),
        ("groups", groups),
        ("departments", departments),
        ("users", users),
        ("time_windows", time_windows),
        ("labels", labels),
    ]:
        if param_value is not None:
            payload[param_name] = parse_list(param_value)

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zia_list_cloud_firewall_dns_rules(
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
    Lists ZIA Cloud Firewall DNS Rules.

    DNS rules govern how the ZIA cloud firewall handles DNS requests
    (allow, block, redirect to a DoH/DNS gateway, redirect to a ZPA-aware
    resolver, etc.). This is a read-only operation and supports JMESPath
    client-side filtering via the ``query`` parameter.

    Returns:
        list[dict]: Cloud Firewall DNS rule records.

    Examples:
        >>> rules = zia_list_cloud_firewall_dns_rules()
        >>> rules = zia_list_cloud_firewall_dns_rules(search="block")
        >>> rules = zia_list_cloud_firewall_dns_rules(query="[].{id: id, name: name, action: action}")
    """
    client = get_zscaler_client(service=service)
    dns = client.zia.cloud_firewall_dns

    query_params = {"search": search} if search else {}
    rules, _, err = dns.list_rules(query_params=query_params)
    if err:
        raise Exception(f"Failed to list Cloud Firewall DNS rules: {err}")
    results = [r.as_dict() for r in (rules or [])]
    return apply_jmespath(results, query)


def zia_get_cloud_firewall_dns_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Cloud Firewall DNS rule to retrieve.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA Cloud Firewall DNS Rule by ID.

    Returns:
        dict: The Cloud Firewall DNS rule record.
    """
    client = get_zscaler_client(service=service)
    dns = client.zia.cloud_firewall_dns

    rule, _, err = dns.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve Cloud Firewall DNS rule {rule_id}: {err}")
    return rule.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================


def zia_create_cloud_firewall_dns_rule(
    name: Annotated[str, Field(description="Rule name (max 31 chars).")],
    rule_action: Annotated[
        str,
        Field(
            description=(
                "Action when traffic matches. Supported values: ALLOW, BLOCK, "
                "REDIR_REQ, REDIR_RES, REDIR_ZPA, REDIR_REQ_DOH, "
                "REDIR_REQ_KEEP_SENDER, REDIR_REQ_TCP, REDIR_REQ_UDP, "
                "BLOCK_WITH_RESPONSE."
            )
        ),
    ],
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = True,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description=ORDER_FIELD_DESCRIPTION)] = None,
    redirect_ip: Annotated[
        Optional[str],
        Field(description="Redirect target IP address when the action is REDIR_*."),
    ] = None,
    enable_full_logging: Annotated[
        Optional[bool], Field(description="If True, enables full logging.")
    ] = None,
    capture_pcap: Annotated[
        Optional[bool], Field(description="Enable packet capture (PCAP) for this rule.")
    ] = None,
    predefined: Annotated[
        Optional[bool], Field(description="Indicates whether the rule is predefined.")
    ] = None,
    default_rule: Annotated[
        Optional[bool], Field(description="Indicates whether the rule is the default DNS rule.")
    ] = None,
    block_response_code: Annotated[
        Optional[str],
        Field(description="DNS response code returned when action is BLOCK_WITH_RESPONSE."),
    ] = None,
    dns_gateway: Annotated[
        Optional[Union[int, str]],
        Field(description="DNS gateway ID for redirect-to-gateway actions."),
    ] = None,
    edns_ecs_object: Annotated[
        Optional[Union[int, str]],
        Field(description="EDNS ECS object ID used for resolution."),
    ] = None,
    zpa_ip_group: Annotated[
        Optional[Union[int, str]],
        Field(description="ZPA IP pool used when resolving ZPA application domains."),
    ] = None,
    applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications the DNS rule applies to. Accepts the same "
                "canonical ZIA app names used by SSL Inspection / Web DLP / "
                "File Type Control / Cloud App Control (e.g. ONEDRIVE, "
                "GOOGLE_DRIVE, CLOUDFLARE_DOH) — DNS just exposes the field as "
                "`applications` instead of `cloud_applications`. Friendly "
                "names (e.g. \"OneDrive\", \"Cloudflare DoH\") are auto-"
                "resolved to canonical names. Accepts JSON string or list."
            )
        ),
    ] = None,
    application_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for DNS application groups.")
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocols (e.g. TCP, UDP, DOHTTPS). Accepts JSON string or list."),
    ] = None,
    dns_rule_request_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="DNS request types covered by the rule. Accepts JSON string or list."),
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
        Field(description="Categories of IP addresses resolved by DNS. Accepts JSON string or list."),
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
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments.")
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
    resolve_cloud_apps: Annotated[
        bool,
        Field(
            description=(
                "When True (default), friendly cloud-application names "
                "supplied in `applications` are resolved to canonical ZIA app "
                "names via the policy-engine cloud-app catalog. Set False to "
                "pass values through unchanged (advanced)."
            )
        ),
    ] = True,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a ZIA Cloud Firewall DNS Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    Returns:
        dict: The created Cloud Firewall DNS rule. If friendly cloud-app
        names supplied in ``applications`` were resolved,
        ``_cloud_applications_resolution`` is included for audit.
    """
    cloud_apps_audit: Optional[dict] = None
    if resolve_cloud_apps and applications is not None:
        applications, cloud_apps_audit = _resolve_cloud_apps_in_place(
            applications, service=service
        )

    rank = apply_default_rank(rank)
    order = apply_default_order(order)
    payload = _build_dns_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        rule_action=rule_action,
        redirect_ip=redirect_ip,
        enable_full_logging=enable_full_logging,
        capture_pcap=capture_pcap,
        predefined=predefined,
        default_rule=default_rule,
        block_response_code=block_response_code,
        dns_gateway=dns_gateway,
        edns_ecs_object=edns_ecs_object,
        zpa_ip_group=zpa_ip_group,
        applications=applications,
        application_groups=application_groups,
        protocols=protocols,
        dns_rule_request_types=dns_rule_request_types,
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
        devices=devices,
        device_groups=device_groups,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        departments=departments,
        users=users,
        time_windows=time_windows,
        labels=labels,
    )

    client = get_zscaler_client(service=service)
    dns = client.zia.cloud_firewall_dns

    rule, _, err = dns.add_rule(**payload)
    if err:
        raise Exception(f"Failed to create Cloud Firewall DNS rule: {err}")
    result = rule.as_dict()
    if cloud_apps_audit:
        result["_cloud_applications_resolution"] = cloud_apps_audit
    return result


def zia_update_cloud_firewall_dns_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Cloud Firewall DNS rule to update.")
    ],
    name: Annotated[Optional[str], Field(description="Rule name (max 31 chars).")] = None,
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = None,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description=ORDER_FIELD_DESCRIPTION)] = None,
    rule_action: Annotated[
        Optional[str],
        Field(
            description=(
                "Action when traffic matches. Supported values: ALLOW, BLOCK, "
                "REDIR_REQ, REDIR_RES, REDIR_ZPA, REDIR_REQ_DOH, "
                "REDIR_REQ_KEEP_SENDER, REDIR_REQ_TCP, REDIR_REQ_UDP, "
                "BLOCK_WITH_RESPONSE."
            )
        ),
    ] = None,
    redirect_ip: Annotated[Optional[str], Field(description="Redirect target IP.")] = None,
    enable_full_logging: Annotated[Optional[bool], Field(description="Enable full logging.")] = None,
    capture_pcap: Annotated[Optional[bool], Field(description="Enable PCAP.")] = None,
    predefined: Annotated[Optional[bool], Field(description="Predefined rule flag.")] = None,
    default_rule: Annotated[Optional[bool], Field(description="Default DNS rule flag.")] = None,
    block_response_code: Annotated[
        Optional[str], Field(description="DNS response code for BLOCK_WITH_RESPONSE.")
    ] = None,
    dns_gateway: Annotated[Optional[Union[int, str]], Field(description="DNS gateway ID.")] = None,
    edns_ecs_object: Annotated[
        Optional[Union[int, str]], Field(description="EDNS ECS object ID.")
    ] = None,
    zpa_ip_group: Annotated[
        Optional[Union[int, str]], Field(description="ZPA IP pool ID.")
    ] = None,
    applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications the DNS rule applies to. Same canonical "
                "ZIA app names as SSL Inspection / Web DLP / FTC / CAC use in "
                "their `cloud_applications` field. Friendly names are auto-"
                "resolved. Accepts JSON string or list."
            )
        ),
    ] = None,
    application_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for DNS application groups.")
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocols. Accepts JSON string or list."),
    ] = None,
    dns_rule_request_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="DNS request types. Accepts JSON string or list."),
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
        Field(description="Categories of IP addresses resolved by DNS."),
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
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments.")
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
    resolve_cloud_apps: Annotated[
        bool,
        Field(
            description=(
                "When True (default), friendly cloud-application names "
                "supplied in `applications` are resolved to canonical ZIA app "
                "names via the policy-engine cloud-app catalog. Set False to "
                "pass values through unchanged (advanced)."
            )
        ),
    ] = True,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates a ZIA Cloud Firewall DNS Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    The DNS rule update endpoint is a PUT (full replacement). This tool
    silently backfills ``name`` and ``order`` from the existing rule when
    the caller does not supply them, so partial updates "just work".

    Returns:
        dict: The updated Cloud Firewall DNS rule. If friendly cloud-app
        names supplied in ``applications`` were resolved,
        ``_cloud_applications_resolution`` is included for audit.
    """
    cloud_apps_audit: Optional[dict] = None
    if resolve_cloud_apps and applications is not None:
        applications, cloud_apps_audit = _resolve_cloud_apps_in_place(
            applications, service=service
        )

    if rank is not None:
        rank = validate_rank(rank)
    if order is not None:
        order = validate_order(order)
    payload = _build_dns_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        rule_action=rule_action,
        redirect_ip=redirect_ip,
        enable_full_logging=enable_full_logging,
        capture_pcap=capture_pcap,
        predefined=predefined,
        default_rule=default_rule,
        block_response_code=block_response_code,
        dns_gateway=dns_gateway,
        edns_ecs_object=edns_ecs_object,
        zpa_ip_group=zpa_ip_group,
        applications=applications,
        application_groups=application_groups,
        protocols=protocols,
        dns_rule_request_types=dns_rule_request_types,
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
        devices=devices,
        device_groups=device_groups,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        departments=departments,
        users=users,
        time_windows=time_windows,
        labels=labels,
    )

    client = get_zscaler_client(service=service)
    dns = client.zia.cloud_firewall_dns

    if "name" not in payload or "order" not in payload:
        existing, _, fetch_err = dns.get_rule(rule_id)
        if fetch_err:
            raise Exception(
                f"Failed to fetch Cloud Firewall DNS rule {rule_id} for required-field backfill: {fetch_err}"
            )
        existing_dict = existing.as_dict()
        payload.setdefault("name", existing_dict.get("name"))
        payload.setdefault("order", existing_dict.get("order"))

    rule, _, err = dns.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update Cloud Firewall DNS rule {rule_id}: {err}")
    result = rule.as_dict()
    if cloud_apps_audit:
        result["_cloud_applications_resolution"] = cloud_apps_audit
    return result


def zia_delete_cloud_firewall_dns_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Cloud Firewall DNS rule to delete.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """
    Deletes a ZIA Cloud Firewall DNS Rule by ID.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Returns:
        str: Success message confirming deletion.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zia_delete_cloud_firewall_dns_rule", confirmed, {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check

    client = get_zscaler_client(service=service)
    dns = client.zia.cloud_firewall_dns

    _, _, err = dns.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete Cloud Firewall DNS rule {rule_id}: {err}")
    return f"Cloud Firewall DNS rule {rule_id} deleted successfully."
