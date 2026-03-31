"""
ZMS Tags Tools

Provides read-only tools for listing Zscaler Microsegmentation tag namespaces,
tag keys, and tag values.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zms_list_tag_namespaces(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
    use_legacy: Annotated[
        Optional[bool],
        Field(description="Whether to use the legacy API."),
    ] = False,
) -> List[Dict[str, Any]]:
    """
    List Zscaler Microsegmentation (ZMS) tag namespaces with pagination.

    Tag namespaces organize tags into logical categories (e.g., AWS tags,
    custom tags, ML-discovered tags). Returns namespace name, description,
    and origin (CUSTOM, EXTERNAL, ML, UNKNOWN).

    Use this tool to:
    - View all tag namespace categories
    - Understand which tag sources are available (cloud provider, custom, ML)
    - Navigate the tag hierarchy (namespaces -> keys -> values)
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.tags.list_tag_namespaces(
        customer_id=customer_id,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No tag namespaces found."}]
    return [result]


def zms_list_tag_keys(
    namespace_id: Annotated[
        str,
        Field(description="The namespace ID. Use zms_list_tag_namespaces to find namespace IDs."),
    ],
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
    use_legacy: Annotated[
        Optional[bool],
        Field(description="Whether to use the legacy API."),
    ] = False,
) -> List[Dict[str, Any]]:
    """
    List tag keys within a specific ZMS tag namespace.

    Returns tag key name and description for all keys in the specified namespace.

    Use this tool to:
    - View available tag keys within a namespace
    - Discover tag keys for building resource group rules
    - Navigate the tag hierarchy (namespaces -> keys -> values)
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.tags.list_tag_keys(
        customer_id=customer_id,
        namespace_id=namespace_id,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No tag keys found in this namespace."}]
    return [result]


def zms_list_tag_values(
    tag_id: Annotated[
        str,
        Field(description="The tag key ID. Use zms_list_tag_keys to find tag key IDs."),
    ],
    namespace_origin: Annotated[
        str,
        Field(description="The namespace origin: CUSTOM, EXTERNAL, ML, or UNKNOWN."),
    ],
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
    use_legacy: Annotated[
        Optional[bool],
        Field(description="Whether to use the legacy API."),
    ] = False,
) -> List[Dict[str, Any]]:
    """
    List tag values for a specific ZMS tag key.

    Returns the available values for the specified tag key and namespace origin.

    Use this tool to:
    - View all values for a specific tag key
    - Discover possible tag values for filtering resources
    - Navigate the tag hierarchy (namespaces -> keys -> values)
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.tags.list_tag_values(
        customer_id=customer_id,
        tag_id=tag_id,
        namespace_origin=namespace_origin,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No tag values found for this tag key."}]
    return [result]
