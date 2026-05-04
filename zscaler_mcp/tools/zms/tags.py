"""
ZMS Tags Tools

Provides read-only tools for listing Zscaler Microsegmentation tag namespaces,
tag keys, and tag values.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zms import apply_jmespath_query


def _sort_direction(sort_order: Optional[str]):
    """Convert a string sort order to SortDirection enum."""
    if not sort_order:
        return None
    from zscaler.zms.models.enums import SortDirection

    return SortDirection(sort_order.upper())


def zms_list_tag_namespaces(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    name: Annotated[
        Optional[str],
        Field(description="Filter by namespace name (substring match)."),
    ] = None,
    origin: Annotated[
        Optional[str],
        Field(description="Filter by namespace origin: 'CUSTOM', 'EXTERNAL', 'ML', or 'UNKNOWN' (exact match)."),
    ] = None,
    sort_order: Annotated[
        Optional[str],
        Field(description="Sort order for namespace name: 'ASC' or 'DESC'."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?origin=='CUSTOM']\"."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    List Zscaler Microsegmentation (ZMS) tag namespaces with pagination and filtering.

    Tag namespaces organize tags into logical categories (e.g., AWS tags,
    custom tags, ML-discovered tags). Returns namespace name, description,
    and origin (CUSTOM, EXTERNAL, ML, UNKNOWN).
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View all tag namespace categories
    - Filter namespaces by name or origin (CUSTOM, EXTERNAL, ML, UNKNOWN)
    - Understand which tag sources are available (cloud provider, custom, ML)
    - Navigate the tag hierarchy (namespaces -> keys -> values)
    - Use JMESPath queries for advanced filtering (e.g., nodes[?origin=='CUSTOM'])
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": page_num,
        "page_size": page_size,
    }

    if name or origin:
        from zscaler.zms.models.inputs import NamespaceFilter, StringExpression

        kwargs["filter_by"] = NamespaceFilter(
            name=StringExpression(contains=name) if name else None,
            origin=StringExpression(equals=origin) if origin else None,
        )

    direction = _sort_direction(sort_order)
    if direction:
        from zscaler.zms.models.inputs import NamespaceQueryOrderBy

        kwargs["order_by"] = NamespaceQueryOrderBy(name=direction)

    result, response, err = client.zms.tags.list_tag_namespaces(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No tag namespaces found."}]
    return apply_jmespath_query(result, query)


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
    key_name: Annotated[
        Optional[str],
        Field(description="Filter by tag key name (substring match)."),
    ] = None,
    sort_order: Annotated[
        Optional[str],
        Field(description="Sort order for tag key name: 'ASC' or 'DESC'."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[*].key_name\"."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    List tag keys within a specific ZMS tag namespace with filtering.

    Returns tag key name and description for all keys in the specified namespace.
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View available tag keys within a namespace
    - Filter tag keys by name
    - Discover tag keys for building resource group rules
    - Navigate the tag hierarchy (namespaces -> keys -> values)
    - Use JMESPath queries for advanced filtering (e.g., nodes[*].key_name)
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "namespace_id": namespace_id,
        "page_num": page_num,
        "page_size": page_size,
    }

    if key_name:
        from zscaler.zms.models.inputs import StringExpression, TagKeyFilter

        kwargs["filter_by"] = TagKeyFilter(
            key_name=StringExpression(contains=key_name),
        )

    direction = _sort_direction(sort_order)
    if direction:
        from zscaler.zms.models.inputs import TagKeyQueryOrderBy

        kwargs["order_by"] = TagKeyQueryOrderBy(name=direction)

    result, response, err = client.zms.tags.list_tag_keys(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No tag keys found in this namespace."}]
    return apply_jmespath_query(result, query)


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
    name: Annotated[
        Optional[str],
        Field(description="Filter by tag value name (substring match)."),
    ] = None,
    sort_order: Annotated[
        Optional[str],
        Field(description="Sort order for tag value name: 'ASC' or 'DESC'."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[*].name\"."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    List tag values for a specific ZMS tag key with filtering.

    Returns the available values for the specified tag key and namespace origin.
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View all values for a specific tag key
    - Filter tag values by name
    - Discover possible tag values for filtering resources
    - Navigate the tag hierarchy (namespaces -> keys -> values)
    - Use JMESPath queries for advanced filtering (e.g., nodes[*].name)
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "tag_id": tag_id,
        "namespace_origin": namespace_origin,
        "page_num": page_num,
        "page_size": page_size,
    }

    if name:
        from zscaler.zms.models.inputs import StringExpression, TagValueFilter

        kwargs["filter_by"] = TagValueFilter(
            name=StringExpression(contains=name),
        )

    direction = _sort_direction(sort_order)
    if direction:
        from zscaler.zms.models.inputs import TagValueQueryOrderBy

        kwargs["order_by"] = TagValueQueryOrderBy(name=direction)

    result, response, err = client.zms.tags.list_tag_values(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No tag values found for this tag key."}]
    return apply_jmespath_query(result, query)
