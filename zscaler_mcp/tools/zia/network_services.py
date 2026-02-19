"""
ZIA Network Services MCP Tools.

This module provides MCP tools for managing ZIA Network Services, which define
custom network services based on TCP/UDP ports for use in Cloud Firewall policies.

Network Services allow you to:
- Define custom services with specific port ranges
- Group ports for source and destination traffic
- Support TCP and UDP protocols
- Use in firewall rules for traffic control

Dependencies:
    - Requires valid Zscaler credentials (ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, ZSCALER_VANITY_DOMAIN)
    - Uses the zscaler-sdk-python cloud_firewall module

Related Tools:
    - zia_list_network_svc_groups: Group multiple network services together
    - zia_list_firewall_rules: Use network services in firewall policies

Example Usage:
    # List all network services
    services = zia_list_network_services()

    # Get a specific service
    service = zia_get_network_service(service_id="12345")

    # Create a new LDAP service
    new_service = zia_create_network_service(
        name="Custom LDAP",
        description="LDAP/LDAPS ports",
        ports='[["dest", "tcp", "389"], ["dest", "tcp", "636"], ["dest", "udp", "389"]]'
    )

    # Update a service
    updated = zia_update_network_service(
        service_id="12345",
        name="Updated LDAP",
        ports='[["dest", "tcp", "389"], ["dest", "tcp", "636"]]'
    )

    # Delete a service
    result = zia_delete_network_service(service_id="12345")
"""

import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_network_services(
    search: Annotated[Optional[str], Field(description="Search string to filter by service name or description.")] = None,
    protocol: Annotated[
        Optional[str],
        Field(description="Filter by protocol. Supported values: 'ICMP', 'TCP', 'UDP', 'GRE', 'ESP', 'OTHER'.")
    ] = None,
    locale: Annotated[
        Optional[str],
        Field(description="Locale for localized descriptions. Supported: 'en-US', 'de-DE', 'es-ES', 'fr-FR', 'ja-JP', 'zh-CN'.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """
    List ZIA network services with optional filtering.

    Network services define custom services based on TCP/UDP port combinations
    that can be used in Cloud Firewall policies.

    Args:
        search: Filter results by name or description substring match.
        protocol: Filter by network protocol (ICMP, TCP, UDP, GRE, ESP, OTHER).
        locale: Get localized descriptions in the specified language.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of network service dictionaries containing:
        - id: Unique identifier for the service
        - name: Name of the network service
        - description: Description of the service
        - type: Service type (STANDARD, PREDEFINED, CUSTOM)
        - srcTcpPorts: List of source TCP port ranges
        - destTcpPorts: List of destination TCP port ranges
        - srcUdpPorts: List of source UDP port ranges
        - destUdpPorts: List of destination UDP port ranges
        - isNameL10nTag: Whether name is a localization tag

    Examples:
        >>> # List all network services
        >>> services = zia_list_network_services()

        >>> # Search for FTP-related services
        >>> ftp_services = zia_list_network_services(search="FTP")

        >>> # Filter by TCP protocol
        >>> tcp_services = zia_list_network_services(protocol="TCP")

        >>> # Get French descriptions
        >>> services_fr = zia_list_network_services(locale="fr-FR")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    query_params = {}
    if search:
        query_params["search"] = search
    if protocol:
        valid_protocols = {"ICMP", "TCP", "UDP", "GRE", "ESP", "OTHER"}
        if protocol.upper() not in valid_protocols:
            raise ValueError(f"Invalid protocol: {protocol}. Supported values: {', '.join(valid_protocols)}")
        query_params["protocol"] = protocol.upper()
    if locale:
        query_params["locale"] = locale

    services, _, err = zia.list_network_services(query_params=query_params if query_params else None)
    if err:
        raise Exception(f"Failed to list network services: {err}")
    return [s.as_dict() for s in services]


def zia_get_network_service(
    service_id: Annotated[Union[int, str], Field(description="The unique ID of the network service to retrieve.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Get a specific ZIA network service by ID.

    Retrieves detailed information about a single network service including
    all port configurations.

    Args:
        service_id: The unique identifier of the network service.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        Dictionary containing the network service details:
        - id: Unique identifier
        - name: Service name
        - description: Service description
        - type: Service type (STANDARD, PREDEFINED, CUSTOM)
        - srcTcpPorts: Source TCP ports [{start, end}]
        - destTcpPorts: Destination TCP ports [{start, end}]
        - srcUdpPorts: Source UDP ports [{start, end}]
        - destUdpPorts: Destination UDP ports [{start, end}]

    Examples:
        >>> service = zia_get_network_service(service_id="12345")
        >>> print(f"Service: {service['name']}")
    """
    if not service_id:
        raise ValueError("service_id is required")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    network_service, _, err = zia.get_network_service(service_id)
    if err:
        raise Exception(f"Failed to retrieve network service {service_id}: {err}")
    return network_service.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def _parse_ports(ports_input: Union[List, str, None]) -> Optional[List]:
    """
    Parse ports input which can be a list or JSON string.

    Ports should be in the format:
    [["src"|"dest", "tcp"|"udp", "start_port", "end_port(optional)"]]

    Examples:
        - ["dest", "tcp", "22"] - Single destination TCP port 22
        - ["dest", "tcp", "80", "443"] - Destination TCP ports 80-443
        - ["src", "udp", "1024", "65535"] - Source UDP ports 1024-65535

    Args:
        ports_input: List of port tuples or JSON string representation.

    Returns:
        Parsed list of port tuples or None if input is empty.

    Raises:
        ValueError: If JSON parsing fails or format is invalid.
    """
    if ports_input is None:
        return None

    if isinstance(ports_input, str):
        try:
            ports_input = json.loads(ports_input)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for ports: {e}")

    if not isinstance(ports_input, list):
        raise ValueError("ports must be a list of port tuples")

    # Convert inner lists to tuples for SDK compatibility
    return [tuple(p) if isinstance(p, list) else p for p in ports_input]


def zia_create_network_service(
    name: Annotated[str, Field(description="Name for the network service (required).")],
    ports: Annotated[
        Union[List, str],
        Field(
            description="""Port definitions as JSON array of arrays. Each inner array defines a port or port range:
            Format: [["src"|"dest", "tcp"|"udp", "start_port", "end_port(optional)"]]
            Examples:
            - Single port: [["dest", "tcp", "22"]]
            - Port range: [["dest", "tcp", "80", "443"]]
            - Multiple: [["dest", "tcp", "389"], ["dest", "udp", "389"], ["dest", "tcp", "636"]]"""
        )
    ],
    description: Annotated[Optional[str], Field(description="Description for the network service (optional).")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Create a new ZIA network service with custom port definitions.

    Network services define TCP/UDP port combinations that can be used in
    Cloud Firewall policies. Services can specify source and/or destination
    ports for both TCP and UDP protocols.

    Args:
        name: Name for the new network service (required).
        ports: Port definitions as JSON array or list. Each entry is a tuple of:
            - Direction: "src" (source) or "dest" (destination)
            - Protocol: "tcp" or "udp"
            - Start port: Starting port number
            - End port: (Optional) Ending port for ranges
        description: Optional description for the service.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        Dictionary containing the created network service with all fields.

    Raises:
        ValueError: If required parameters are missing or ports format is invalid.
        Exception: If the API call fails.

    Examples:
        >>> # Create a simple SSH service
        >>> ssh_svc = zia_create_network_service(
        ...     name="Custom SSH",
        ...     description="SSH access on port 22",
        ...     ports='[["dest", "tcp", "22"]]'
        ... )

        >>> # Create LDAP service with multiple ports
        >>> ldap_svc = zia_create_network_service(
        ...     name="Custom LDAP",
        ...     description="LDAP and LDAPS",
        ...     ports='[["dest", "tcp", "389"], ["dest", "udp", "389"], ["dest", "tcp", "636"]]'
        ... )

        >>> # Create service with port range
        >>> high_ports = zia_create_network_service(
        ...     name="High Ports",
        ...     description="Ephemeral ports",
        ...     ports='[["src", "tcp", "49152", "65535"]]'
        ... )

        >>> # Create service with both TCP and UDP
        >>> dns_svc = zia_create_network_service(
        ...     name="Custom DNS",
        ...     ports='[["dest", "tcp", "53"], ["dest", "udp", "53"]]'
        ... )
    """
    if not name:
        raise ValueError("name is required")
    if not ports:
        raise ValueError("ports is required - must specify at least one port definition")

    parsed_ports = _parse_ports(ports)
    if not parsed_ports:
        raise ValueError("ports must contain at least one port definition")

    # Validate port tuple format
    for port_tuple in parsed_ports:
        if len(port_tuple) < 3:
            raise ValueError(
                f"Invalid port tuple {port_tuple}. "
                "Format: ('src'|'dest', 'tcp'|'udp', 'start_port', 'end_port')"
            )
        direction, protocol = port_tuple[0], port_tuple[1]
        if direction not in ("src", "dest"):
            raise ValueError(f"Invalid direction '{direction}'. Must be 'src' or 'dest'.")
        if protocol.lower() not in ("tcp", "udp"):
            raise ValueError(f"Invalid protocol '{protocol}'. Must be 'tcp' or 'udp'.")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    kwargs = {"name": name}
    if description:
        kwargs["description"] = description

    network_service, _, err = zia.add_network_service(ports=parsed_ports, **kwargs)
    if err:
        raise Exception(f"Failed to create network service: {err}")
    return network_service.as_dict()


def zia_update_network_service(
    service_id: Annotated[Union[int, str], Field(description="The unique ID of the network service to update (required).")],
    name: Annotated[str, Field(description="Updated name for the network service (required for update).")],
    ports: Annotated[
        Optional[Union[List, str]],
        Field(
            description="""Port definitions as JSON array of arrays. If provided, REPLACES existing ports.
            Format: [["src"|"dest", "tcp"|"udp", "start_port", "end_port(optional)"]]
            If omitted, existing ports are preserved."""
        )
    ] = None,
    description: Annotated[Optional[str], Field(description="Updated description (optional).")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Update an existing ZIA network service.

    Updates the specified network service. If ports are provided, they will
    REPLACE the existing port configuration. If ports are not provided,
    the existing ports will be preserved.

    Note: Only custom network services can be updated. Predefined services
    cannot be modified.

    Args:
        service_id: The unique ID of the network service to update (required).
        name: Updated name for the service (required).
        ports: Optional new port definitions. If provided, replaces all existing ports.
        description: Optional updated description.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        Dictionary containing the updated network service.

    Raises:
        ValueError: If required parameters are missing or format is invalid.
        Exception: If the API call fails.

    Examples:
        >>> # Update service name and description (keep existing ports)
        >>> updated = zia_update_network_service(
        ...     service_id="12345",
        ...     name="Renamed Service",
        ...     description="Updated description"
        ... )

        >>> # Update ports (replaces existing)
        >>> updated = zia_update_network_service(
        ...     service_id="12345",
        ...     name="Updated Service",
        ...     ports='[["dest", "tcp", "8080"], ["dest", "tcp", "8443"]]'
        ... )
    """
    if not service_id:
        raise ValueError("service_id is required")
    if not name:
        raise ValueError("name is required for update")

    parsed_ports = _parse_ports(ports) if ports else None

    # Validate port tuples if provided
    if parsed_ports:
        for port_tuple in parsed_ports:
            if len(port_tuple) < 3:
                raise ValueError(
                    f"Invalid port tuple {port_tuple}. "
                    "Format: ('src'|'dest', 'tcp'|'udp', 'start_port', 'end_port')"
                )
            direction, protocol = port_tuple[0], port_tuple[1]
            if direction not in ("src", "dest"):
                raise ValueError(f"Invalid direction '{direction}'. Must be 'src' or 'dest'.")
            if protocol.lower() not in ("tcp", "udp"):
                raise ValueError(f"Invalid protocol '{protocol}'. Must be 'tcp' or 'udp'.")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    kwargs = {"name": name}
    if description is not None:
        kwargs["description"] = description

    network_service, _, err = zia.update_network_service(
        service_id=str(service_id),
        ports=parsed_ports,
        **kwargs
    )
    if err:
        raise Exception(f"Failed to update network service {service_id}: {err}")
    return network_service.as_dict()


def zia_delete_network_service(
    service_id: Annotated[Union[int, str], Field(description="The unique ID of the network service to delete (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Delete a ZIA network service.

    Permanently deletes the specified network service. This action cannot be
    undone. The service must not be in use by any firewall rules or service
    groups before deletion.

    Note: Only custom network services can be deleted. Predefined services
    cannot be removed.

    Args:
        service_id: The unique ID of the network service to delete (required).
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").
        kwargs: JSON string for internal confirmation handling.

    Returns:
        Success message confirming deletion.

    Raises:
        ValueError: If service_id is not provided.
        Exception: If the API call fails (e.g., service in use, not found).

    Examples:
        >>> # Delete a network service
        >>> result = zia_delete_network_service(service_id="12345")
        >>> print(result)  # "Network service 12345 deleted successfully"

    Warning:
        - Ensure the service is not referenced by any firewall rules
        - Ensure the service is not part of any network service groups
        - This operation cannot be undone
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation(
        "zia_delete_network_service",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check

    if not service_id:
        raise ValueError("service_id is required for delete")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    _, _, err = zia.delete_network_service(service_id)
    if err:
        raise Exception(f"Failed to delete network service {service_id}: {err}")
    return f"Network service {service_id} deleted successfully"
