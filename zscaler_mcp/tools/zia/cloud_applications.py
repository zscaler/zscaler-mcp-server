from typing import Annotated, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_cloud_applications(
    page_number: Annotated[Optional[int], Field(description="Optional page number for pagination.")] = None,
    limit: Annotated[Optional[int], Field(description="Optional result limit. Use 1000 as the maximum limit for efficiency.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """List ZIA Shadow IT cloud applications with optional pagination."""
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
    return [app.as_dict() for app in apps]


def zia_list_cloud_application_custom_tags(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """List ZIA Shadow IT custom tags."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    shadow_it = client.zia.shadow_it_report
    
    tags, _, err = shadow_it.list_custom_tags()
    if err:
        raise Exception(f"Failed to list custom tags: {err}")
    return [tag.as_dict() for tag in tags]


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_bulk_update_cloud_applications(
    sanction_state: Annotated[str, Field(description="One of 'sanctioned', 'unsanctioned', or 'any' (required).")],
    application_ids: Annotated[Optional[List[str]], Field(description="List of application IDs to update.")] = None,
    custom_tag_ids: Annotated[Optional[List[str]], Field(description="List of custom tag IDs to apply.")] = None,
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
