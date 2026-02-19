"""
ZIA Network Applications MCP Tools.

This module provides MCP tools for managing ZIA Network Applications, which define
application-level protocols and services that can be used in Cloud Firewall policies.

Network Applications allow you to:
- Identify and control application-level traffic
- Use predefined applications or create custom applications
- Group applications for easier management
- Apply in firewall rules for granular traffic control

Dependencies:
    - Requires valid Zscaler credentials (ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, ZSCALER_VANITY_DOMAIN)
    - Uses the zscaler-sdk-python cloud_firewall module

Related Tools:
    - zia_list_network_app_groups: Group multiple network applications together
    - zia_list_firewall_rules: Use network applications in firewall policies

Example Usage:
    # List all network applications
    apps = zia_list_network_apps()

    # Search for specific applications
    icmp_apps = zia_list_network_apps(search="ICMP")

    # Get localized descriptions
    apps_fr = zia_list_network_apps(locale="fr-FR")

    # Get a specific application
    app = zia_get_network_app(app_id="ICMP_ANY")
"""

from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_network_apps(
    search: Annotated[
        Optional[str],
        Field(description="Search string to filter network applications by name or description."),
    ] = None,
    locale: Annotated[
        Optional[str],
        Field(
            description="Locale for localized descriptions. Supported values: 'en-US', 'de-DE', 'es-ES', 'fr-FR', 'ja-JP', 'zh-CN'."
        ),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """
    List ZIA network applications with optional filtering.

    Network applications define application-level protocols and services that can be
    used in Cloud Firewall policies. This includes predefined applications like ICMP,
    HTTP, HTTPS, and custom applications.

    Args:
        search: Filter results by name or description substring match.
            Examples: "ICMP", "HTTP", "FTP", "SSH"
        locale: Get localized descriptions in the specified language.
            Supported locales: 'en-US', 'de-DE', 'es-ES', 'fr-FR', 'ja-JP', 'zh-CN'
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of network application dictionaries containing:
        - id: Unique identifier for the application (e.g., "ICMP_ANY", "HTTP", "HTTPS")
        - name: Name of the network application
        - description: Description of the application
        - type: Application type (STANDARD, PREDEFINED, CUSTOM)
        - isNameL10nTag: Whether name is a localization tag
        - isDescriptionL10nTag: Whether description is a localization tag

    Examples:
        >>> # List all network applications
        >>> apps = zia_list_network_apps()
        >>> print(f"Total applications found: {len(apps)}")
        >>> for app in apps[:5]:
        ...     print(f"{app['id']}: {app['name']}")

        >>> # Search for ICMP-related applications
        >>> icmp_apps = zia_list_network_apps(search="ICMP")
        >>> print(f"Found {len(icmp_apps)} ICMP applications")
        >>> for app in icmp_apps:
        ...     print(f"  - {app['id']}: {app['name']}")

        >>> # Search for HTTP-related applications
        >>> http_apps = zia_list_network_apps(search="HTTP")
        >>> print(f"Found {len(http_apps)} HTTP applications")
        >>> for app in http_apps:
        ...     print(f"  - {app['id']}: {app['name']}")

        >>> # Get French localized descriptions
        >>> apps_fr = zia_list_network_apps(locale="fr-FR")
        >>> print(f"Applications with French descriptions: {len(apps_fr)}")
        >>> for app in apps_fr[:3]:
        ...     print(f"  - {app['name']}: {app.get('description', 'N/A')}")

        >>> # Combine search and locale
        >>> icmp_fr = zia_list_network_apps(search="ICMP", locale="fr-FR")
        >>> print(f"ICMP applications in French: {len(icmp_fr)}")
        >>> for app in icmp_fr:
        ...     print(f"  - {app['name']}: {app.get('description', 'N/A')}")

        >>> # Search for SSH applications
        >>> ssh_apps = zia_list_network_apps(search="SSH")
        >>> print(f"Found {len(ssh_apps)} SSH applications")
        >>> for app in ssh_apps:
        ...     print(f"  - {app['id']}: {app['name']}")

        >>> # List all predefined applications
        >>> all_apps = zia_list_network_apps()
        >>> predefined = [app for app in all_apps if app.get('type') == 'PREDEFINED']
        >>> print(f"Total predefined applications: {len(predefined)}")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    query_params = {}
    if search:
        query_params["search"] = search
    if locale:
        valid_locales = {"en-US", "de-DE", "es-ES", "fr-FR", "ja-JP", "zh-CN"}
        if locale not in valid_locales:
            raise ValueError(f"Invalid locale: {locale}. Supported values: {', '.join(sorted(valid_locales))}")
        query_params["locale"] = locale

    apps, _, err = zia.list_network_apps(query_params=query_params if query_params else None)
    if err:
        raise Exception(f"Failed to list network applications: {err}")
    return [app.as_dict() for app in apps]


def zia_get_network_app(
    app_id: Annotated[Union[int, str], Field(description="The unique ID of the network application to retrieve (e.g., 'ICMP_ANY', 'HTTP', 'HTTPS').")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Get a specific ZIA network application by ID.

    Retrieves detailed information about a single network application including
    its name, description, type, and localization tags.

    Args:
        app_id: The unique identifier of the network application.
            Can be a string ID (e.g., "ICMP_ANY", "HTTP", "HTTPS") or numeric ID.
            Common predefined application IDs include:
            - "ICMP_ANY": ICMP protocol
            - "HTTP": HTTP protocol
            - "HTTPS": HTTPS protocol
            - "FTP": FTP protocol
            - "SSH": SSH protocol
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        Dictionary containing the network application details:
        - id: Unique identifier (e.g., "ICMP_ANY", "HTTP")
        - name: Application name
        - description: Application description
        - type: Application type (STANDARD, PREDEFINED, CUSTOM)
        - isNameL10nTag: Whether name is a localization tag
        - isDescriptionL10nTag: Whether description is a localization tag

    Examples:
        >>> # Get ICMP application details
        >>> icmp = zia_get_network_app(app_id="ICMP_ANY")
        >>> print(f"Application: {icmp['name']}")
        >>> print(f"Description: {icmp.get('description', 'N/A')}")
        >>> print(f"Type: {icmp.get('type', 'N/A')}")

        >>> # Get HTTP application details
        >>> http = zia_get_network_app(app_id="HTTP")
        >>> print(f"Application: {http['name']}")
        >>> print(f"Description: {http.get('description', 'N/A')}")

        >>> # Get HTTPS application details
        >>> https = zia_get_network_app(app_id="HTTPS")
        >>> print(f"Application: {https['name']}")
        >>> print(f"Description: {https.get('description', 'N/A')}")

        >>> # Get SSH application details
        >>> ssh = zia_get_network_app(app_id="SSH")
        >>> print(f"Application: {ssh['name']}")
        >>> print(f"Description: {ssh.get('description', 'N/A')}")

        >>> # Get FTP application details
        >>> ftp = zia_get_network_app(app_id="FTP")
        >>> print(f"Application: {ftp['name']}")
        >>> print(f"Description: {ftp.get('description', 'N/A')}")

        >>> # Get application by numeric ID (if known)
        >>> app = zia_get_network_app(app_id=12345)
        >>> print(f"Application: {app['name']}")
    """
    if not app_id:
        raise ValueError("app_id is required")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    app, _, err = zia.get_network_app(app_id)
    if err:
        raise Exception(f"Failed to retrieve network application {app_id}: {err}")
    return app.as_dict()
