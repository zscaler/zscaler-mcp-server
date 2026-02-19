"""
ZIA Cloud App Control MCP Tools.

This module provides MCP tools for ZIA Cloud App Control, which manages granular
controls over cloud application usage (e.g., streaming media, webmail, file sharing).

Cloud App Control allows you to:
- Define rules that allow, block, caution, or isolate specific actions within cloud apps
- Apply rules by rule type (STREAMING_MEDIA, WEBMAIL, FILE_SHARE, etc.)
- Query available granular actions for each rule type and cloud app combination

Dependencies:
    - Requires valid Zscaler credentials (ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, ZSCALER_VANITY_DOMAIN)
    - Uses the zscaler-sdk-python cloudappcontrol module

Related Tools:
    - zia_list_cloud_applications: List cloud applications (Shadow IT)
    - zia_list_cloud_firewall_rules: Cloud firewall rules

Example Usage:
    # List available actions for STREAMING_MEDIA rule type and DROPBOX app
    actions = zia_list_cloud_app_control_actions(
        rule_type="STREAMING_MEDIA",
        cloud_apps=["DROPBOX"],
    )
"""

from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_cloud_app_control_actions(
    rule_type: Annotated[
        str,
        Field(
            description="The type of rule for which actions should be retrieved. "
            "Examples: STREAMING_MEDIA, WEBMAIL, FILE_SHARE, AI_ML, BUSINESS_PRODUCTIVITY, "
            "CONSUMER, DNS_OVER_HTTPS, ENTERPRISE_COLLABORATION, FINANCE, HEALTH_CARE, "
            "HOSTING_PROVIDER, HUMAN_RESOURCES, INSTANT_MESSAGING, IT_SERVICES, LEGAL, "
            "SALES_AND_MARKETING, SOCIAL_NETWORKING, SYSTEM_AND_DEVELOPMENT."
        ),
    ],
    cloud_apps: Annotated[
        Union[List[str], str],
        Field(
            description="List of cloud application names for filtering. "
            "Examples: ['DROPBOX'], ['GOOGLE_WEBMAIL', 'YAHOO_WEBMAIL']. Accepts JSON string or list."
        ),
    ],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[str]:
    """
    List granular actions supported for a specific Cloud App Control rule type.

    Retrieves the list of actions (e.g., ALLOW_STREAMING_VIEW_LISTEN, BLOCK_WEBMAIL_SEND)
    that can be used when creating or updating Cloud App Control rules for the given
    rule type and cloud application combination.

    Args:
        rule_type: The type of rule for which actions should be retrieved.
            Common values: STREAMING_MEDIA, WEBMAIL, FILE_SHARE, AI_ML, BUSINESS_PRODUCTIVITY,
            CONSUMER, DNS_OVER_HTTPS, ENTERPRISE_COLLABORATION, FINANCE, HEALTH_CARE,
            HOSTING_PROVIDER, HUMAN_RESOURCES, INSTANT_MESSAGING, IT_SERVICES, LEGAL,
            SALES_AND_MARKETING, SOCIAL_NETWORKING, SYSTEM_AND_DEVELOPMENT.
        cloud_apps: List of cloud application names for filtering (e.g., DROPBOX, GOOGLE_WEBMAIL).
            Accepts a list or JSON string.
        use_legacy: Whether to use the legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of action strings supported for the given rule type and cloud apps.
        Example: ['ALLOW_STREAMING_VIEW_LISTEN', 'ALLOW_STREAMING_UPLOAD', 'BLOCK_STREAMING_UPLOAD', ...]

    Examples:
        >>> # Retrieve available actions for STREAMING_MEDIA rule type with DROPBOX
        >>> actions = zia_list_cloud_app_control_actions(
        ...     rule_type="STREAMING_MEDIA",
        ...     cloud_apps=["DROPBOX"],
        ... )
        >>> if actions:
        ...     for action in actions:
        ...         print(action)
        >>> # Output may include: ALLOW_STREAMING_VIEW_LISTEN, ALLOW_STREAMING_UPLOAD, etc.

        >>> # Retrieve available actions for WEBMAIL rule type with multiple apps
        >>> actions = zia_list_cloud_app_control_actions(
        ...     rule_type="WEBMAIL",
        ...     cloud_apps=["GOOGLE_WEBMAIL", "YAHOO_WEBMAIL"],
        ... )
        >>> print(f"Found {len(actions)} actions for WEBMAIL")
        >>> for action in actions:
        ...     print(f"  - {action}")
        >>> # Output may include: ALLOW_WEBMAIL_VIEW, ALLOW_WEBMAIL_ATTACHMENT_SEND, BLOCK_WEBMAIL_SEND, etc.

        >>> # Retrieve available actions for FILE_SHARE rule type
        >>> actions = zia_list_cloud_app_control_actions(
        ...     rule_type="FILE_SHARE",
        ...     cloud_apps=["DROPBOX", "GOOGLE_DRIVE"],
        ... )
        >>> print(f"FILE_SHARE actions: {', '.join(actions)}")
        >>> # Output may include: ALLOW_FILE_SHARE_VIEW, ALLOW_FILE_SHARE_UPLOAD, DENY_FILE_SHARE_VIEW, etc.

        >>> # Retrieve available actions for AI_ML rule type
        >>> actions = zia_list_cloud_app_control_actions(
        ...     rule_type="AI_ML",
        ...     cloud_apps=["CHATGPT"],
        ... )
        >>> if "ALLOW_AI_ML_WEB_USE" in actions:
        ...     print("ALLOW_AI_ML_WEB_USE is available")

    Rule Types and Example Actions (reference):
        - STREAMING_MEDIA: ALLOW_STREAMING_VIEW_LISTEN, ALLOW_STREAMING_UPLOAD, BLOCK_STREAMING_UPLOAD
        - WEBMAIL: ALLOW_WEBMAIL_VIEW, ALLOW_WEBMAIL_ATTACHMENT_SEND, ALLOW_WEBMAIL_SEND, BLOCK_WEBMAIL_SEND
        - FILE_SHARE: ALLOW_FILE_SHARE_VIEW, ALLOW_FILE_SHARE_UPLOAD, DENY_FILE_SHARE_VIEW
        - AI_ML: ALLOW_AI_ML_WEB_USE, CAUTION_AI_ML_WEB_USE, DENY_AI_ML_WEB_USE, ISOLATE_AI_ML_WEB_USE
        - BUSINESS_PRODUCTIVITY: ALLOW_BUSINESS_PRODUCTIVITY_APPS, BLOCK_BUSINESS_PRODUCTIVITY_APPS
        - SOCIAL_NETWORKING: ALLOW_SOCIAL_NETWORKING_VIEW, ALLOW_SOCIAL_NETWORKING_POST, BLOCK_SOCIAL_NETWORKING_POST
    """
    # Normalize cloud_apps: accept list or JSON string
    if isinstance(cloud_apps, str):
        import json

        try:
            cloud_apps = json.loads(cloud_apps)
        except json.JSONDecodeError:
            cloud_apps = [a.strip() for a in cloud_apps.split(",") if a.strip()]
    if not isinstance(cloud_apps, list):
        raise ValueError("cloud_apps must be a list of cloud application names or a JSON string")
    if not cloud_apps:
        raise ValueError("cloud_apps cannot be empty")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    cloudappcontrol = client.zia.cloudappcontrol

    actions, _, err = cloudappcontrol.list_available_actions(rule_type=rule_type, cloud_apps=cloud_apps)
    if err:
        raise Exception(f"Failed to list available Cloud App Control actions: {err}")

    return actions or []
