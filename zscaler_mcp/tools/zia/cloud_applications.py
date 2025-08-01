from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List
from pydantic import Field


def cloud_applications_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'list_apps', 'list_custom_tags', or 'bulk_update'."
        ),
    ],
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
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[List[dict], dict, str]:
    """
    Tool for managing ZIA Shadow IT Cloud Applications.

    Supported actions:
    - "list_apps": Lists cloud applications with optional pagination.
    - "list_custom_tags": Lists custom tags available for cloud applications.
    - "bulk_update": Applies sanction state and/or custom tags to applications in bulk.

    Args:
        action (str): One of ["list_apps", "list_custom_tags", "bulk_update"]
        use_legacy (bool): Whether to use the legacy client.
        service (str): The Zscaler service, e.g., "zia".
        page_number (int): Optional page number for listing applications.
        limit (int): Optional result limit for listing applications. Use 1000 as the maximum limit for efficiency.
        sanction_state (str): One of ["sanctioned", "unsanctioned", "any"] for bulk update.
        application_ids (List[str]): List of application IDs to update.
        custom_tag_ids (List[str]): List of custom tag IDs to apply in bulk update.

    Returns:
        List of dicts or a dict depending on the action.

    Examples:
        cloud_applications_manager("list_apps", page_number=1, limit=1000)
        cloud_applications_manager("list_custom_tags")
        cloud_applications_manager("bulk_update", sanction_state="sanctioned", application_ids=["123"], custom_tag_ids=["456"])
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    shadow_it = client.zia.shadow_it_report

    if action == "list_apps":
        query_params = {}
        if page_number is not None:
            query_params["page_number"] = page_number
        if limit is not None:
            query_params["limit"] = limit

        apps, _, err = shadow_it.list_apps(query_params=query_params or None)
        if err:
            raise Exception(f"Failed to list applications: {err}")
        return [app.as_dict() for app in apps]

    elif action == "list_custom_tags":
        tags, _, err = shadow_it.list_custom_tags()
        if err:
            raise Exception(f"Failed to list custom tags: {err}")
        return [tag.as_dict() for tag in tags]

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
