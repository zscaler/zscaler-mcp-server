"""
ZMS Nonces (Provisioning Keys) Tools

Provides read-only tools for listing and retrieving Zscaler Microsegmentation
provisioning keys (nonces).
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zms import apply_jmespath_query


def zms_list_nonces(
    page: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    search: Annotated[
        Optional[str],
        Field(description="Search filter string to narrow nonces."),
    ] = None,
    sort: Annotated[
        Optional[str],
        Field(description="Sort field (e.g., 'name')."),
    ] = None,
    sort_dir: Annotated[
        Optional[str],
        Field(description="Sort direction: ASC or DESC."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?product_type=='ZMS']\"."),
    ] = None,
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
    List Zscaler Microsegmentation (ZMS) nonces (provisioning keys) with pagination.

    Nonces are one-time provisioning keys used to register new agents.
    Returns key name, value, max usage, current usage count, associated
    agent group, product type, and timestamps.
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View available provisioning keys for agent enrollment
    - Check usage counts vs max usage limits
    - See which agent groups keys are associated with
    - Monitor key creation and modification dates
    - Use JMESPath queries for advanced filtering (e.g., nodes[?product_type=='ZMS'])
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "page": page,
        "page_size": page_size,
    }
    if search is not None:
        kwargs["search"] = search
    if sort is not None:
        kwargs["sort"] = sort
    if sort_dir is not None:
        kwargs["sort_dir"] = sort_dir

    result, response, err = client.zms.nonces.list_nonces(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No nonces (provisioning keys) found."}]
    return apply_jmespath_query(result, query)


def zms_get_nonce(
    eyez_id: Annotated[
        str,
        Field(description="The nonce eyez ID. Use zms_list_nonces to find eyez IDs."),
    ],
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
    Get a specific ZMS nonce (provisioning key) by its eyez ID.

    Returns detailed information about the provisioning key including
    the key value, usage counts, and associated agent group.

    Use this tool to:
    - Retrieve a specific provisioning key's details
    - Check remaining usage for a provisioning key
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.nonces.get_nonce(
        customer_id=customer_id,
        eyez_id=eyez_id,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No nonce found with this eyez ID."}]
    return [result]
