"""ZIA Shadow IT Report tools.

These tools wrap the SDK's ``client.zia.shadow_it_report`` resource, which
exposes the **Shadow IT analytics catalog** (numeric application IDs, friendly
display names like "Sharepoint Online", custom tag management, and bulk
sanction-state updates).

This catalog is *separate* from the policy-engine cloud-application catalog
used by SSL Inspection / DLP / Cloud App Control rules. For the policy-engine
catalog (canonical enum strings such as ``ONEDRIVE`` / ``SHAREPOINT_ONLINE``),
see ``zscaler_mcp/tools/zia/cloud_applications.py``.
"""

from typing import Annotated, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_shadow_it_apps(
    page_number: Annotated[
        Optional[int], Field(description="Optional page number for pagination.")
    ] = None,
    limit: Annotated[
        Optional[int],
        Field(description="Optional result limit. Use 1000 as the maximum limit for efficiency."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """List ZIA Shadow IT cloud applications with optional pagination.

    Returns the Shadow IT analytics catalog (numeric IDs + friendly names),
    not the policy-engine enum catalog. Supports JMESPath client-side
    filtering via the ``query`` parameter.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    shadow_it = client.zia.shadow_it_report

    query_params = {}
    if page_number is not None:
        query_params["page_number"] = page_number
    if limit is not None:
        query_params["limit"] = limit

    apps, _, err = shadow_it.list_apps(query_params=query_params or None)
    if err:
        raise Exception(f"Failed to list applications: {err}")
    results = [app.as_dict() for app in apps]
    return apply_jmespath(results, query)


def zia_list_shadow_it_custom_tags(
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """List ZIA Shadow IT custom tags.

    Supports JMESPath client-side filtering via the ``query`` parameter.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    shadow_it = client.zia.shadow_it_report

    tags, _, err = shadow_it.list_custom_tags()
    if err:
        raise Exception(f"Failed to list custom tags: {err}")
    results = [tag.as_dict() for tag in tags]
    return apply_jmespath(results, query)


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zia_bulk_update_shadow_it_apps(
    sanction_state: Annotated[
        str, Field(description="One of 'sanctioned', 'unsanctioned', or 'any' (required).")
    ],
    application_ids: Annotated[
        Optional[List[str]], Field(description="List of application IDs to update.")
    ] = None,
    custom_tag_ids: Annotated[
        Optional[List[str]], Field(description="List of custom tag IDs to apply.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Apply sanction state and/or custom tags to ZIA Shadow IT applications in bulk."""
    if not sanction_state:
        raise ValueError("You must provide a sanction_state for bulk updates")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    shadow_it = client.zia.shadow_it_report

    result, _, err = shadow_it.bulk_update(
        sanction_state,
        application_ids=application_ids,
        custom_tag_ids=custom_tag_ids,
    )
    if err:
        raise Exception(f"Bulk update failed: {err}")

    return result.as_dict() if hasattr(result, "as_dict") else result
