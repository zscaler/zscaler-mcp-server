from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def cloud_applications_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'read' (list applications or custom tags), or 'bulk_update'."
        ),
    ] = "read",
    page_number: Annotated[
        int, Field(description="Optional page number for listing applications.")
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Optional result limit for listing applications. Use 1000 as the maximum limit for efficiency."
        ),
    ] = None,
    sanction_state: Annotated[
        str,
        Field(
            description="One of 'sanctioned', 'unsanctioned', or 'any' for bulk update."
        ),
    ] = None,
    application_ids: Annotated[
        List[str], Field(description="List of application IDs to update.")
    ] = None,
    custom_tag_ids: Annotated[
        List[str], Field(description="List of custom tag IDs to apply in bulk update.")
    ] = None,
    list_tags: Annotated[
        bool, Field(description="If True, lists custom tags instead of applications.")
    ] = False,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[List[dict], dict, str]:
    """
    Tool for managing ZIA Shadow IT Cloud Applications.

    Supported actions:
    - "read": Lists cloud applications with optional pagination, or custom tags if list_tags=True.
    - "bulk_update": Applies sanction state and/or custom tags to applications in bulk.

    Args:
        action (str): One of ["read", "bulk_update"]
        list_tags (bool): If True, lists custom tags instead of applications.
        use_legacy (bool): Whether to use the legacy client.
        service (str): The Zscaler service, e.g., "zia".
        page_number (int): Optional page number for listing applications (ignored when list_tags=True).
        limit (int): Optional result limit for listing applications (ignored when list_tags=True).
        sanction_state (str): One of ["sanctioned", "unsanctioned", "any"] for bulk update.
        application_ids (List[str]): List of application IDs to update.
        custom_tag_ids (List[str]): List of custom tag IDs to apply in bulk update.

    Returns:
        List of dicts or a dict depending on the action.

    Examples:
        cloud_applications_manager()  # Lists applications
        cloud_applications_manager(list_tags=True)  # Lists custom tags
        cloud_applications_manager(page_number=1, limit=1000)  # Lists applications with pagination
        cloud_applications_manager("bulk_update", sanction_state="sanctioned", application_ids=["123"], custom_tag_ids=["456"])
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    shadow_it = client.zia.shadow_it_report

    if action == "read":
        if list_tags:
            # List custom tags
            tags, _, err = shadow_it.list_custom_tags()
            if err:
                raise Exception(f"Failed to list custom tags: {err}")
            return [tag.as_dict() for tag in tags]
        else:
            # List applications with optional pagination
            query_params = {}
            if page_number is not None:
                query_params["page_number"] = page_number
            if limit is not None:
                query_params["limit"] = limit

            apps, _, err = shadow_it.list_apps(query_params=query_params or None)
            if err:
                raise Exception(f"Failed to list applications: {err}")
            return [app.as_dict() for app in apps]

    elif action == "bulk_update":
        if not sanction_state:
            raise ValueError("You must provide a sanction_state for bulk updates.")
        result, _, err = shadow_it.bulk_update(
            sanction_state,
            application_ids=application_ids,
            custom_tag_ids=custom_tag_ids,
        )
        if err:
            raise Exception(f"Bulk update failed: {err}")
        return result

    else:
        raise ValueError(f"Unsupported action: {action}")
