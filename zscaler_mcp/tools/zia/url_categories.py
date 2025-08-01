from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List
from pydantic import Field


def url_category_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', 'add', 'remove', or 'delete'."
        ),
    ],
    category_id: Annotated[
        str,
        Field(
            description="Category ID for read (single), update, add, remove, and delete operations."
        ),
    ] = None,
    configured_name: Annotated[
        str,
        Field(
            description="Name of the category (required for create, update, add, remove)."
        ),
    ] = None,
    super_category: Annotated[
        str,
        Field(description="Super category (required for creating custom categories)."),
    ] = None,
    urls: Annotated[
        List, Field(description="List of URLs to create/update/add/remove.")
    ] = None,
    description: Annotated[
        str, Field(description="Optional description for the category.")
    ] = None,
    custom_category: Annotated[
        bool,
        Field(description="Must be True for custom categories. Required for create."),
    ] = None,
    keywords: Annotated[List, Field(description="Custom keywords.")] = None,
    ip_ranges: Annotated[List, Field(description="Optional list of IP ranges.")] = None,
    db_categorized_urls: Annotated[
        List, Field(description="DB-categorized URLs.")
    ] = None,
    keywords_retaining_parent_category: Annotated[
        List, Field(description="Retained keywords from parent.")
    ] = None,
    ip_ranges_retaining_parent_category: Annotated[
        List, Field(description="Retained IP ranges from parent.")
    ] = None,
    query_params: Annotated[
        dict, Field(description="Optional filters for listing categories.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing ZIA URL Categories via the Python SDK.

    This tool provides comprehensive URL category management capabilities including:
    - Listing all URL categories with optional filtering
    - Retrieving specific categories by ID
    - Creating new custom URL categories
    - Performing full or incremental updates to existing categories
    - Deleting custom URL categories

    **AI Agent Requirements:**
    - For CREATE: Always verify that `configured_name` and `super_category` are provided
    - For CREATE: Ensure `custom_category=True` is set when creating custom categories
    - For FULL UPDATE: Use `action="update"` and supply the full replacement payload (e.g., `urls`, `description`, etc.)
    - For INCREMENTAL UPDATES:
        - Use `action="add"` to append URLs to the existing list
        - Use `action="remove"` to delete specific URLs from the list
        - Only `category_id`, `configured_name`, and `urls` are required for these operations
    - For DELETE: Only custom categories can be deleted
    - For READ: Use `category_id` for specific category lookup, omit for listing all categories

    Supported actions:
    - create: Creates a new custom URL category.
    - read: Lists all categories or retrieves a specific category by `category_id`.
    - update: Performs a full update that replaces all fields (e.g., URLs, description, etc.).
    - add: Incrementally adds URLs to the category using `add_urls_to_category()`.
    - remove: Incrementally removes URLs from the category using `delete_urls_from_category()`.
    - delete: Deletes a custom URL category.

    Args:
        action (str): One of 'create', 'read', 'update', 'add', 'remove', 'delete'.
        category_id (str, optional): Required for read (single), update, add, remove, and delete.
        configured_name (str, required for create, update, add, remove): Name of the category.
        super_category (str, optional): Required for creating custom categories.
        urls (list, optional): List of URLs to create/update/add/remove.
        description (str, optional): Optional description for the category.
        custom_category (bool, optional): Must be True for custom categories. Required for create.
        keywords (list, optional): Custom keywords.
        ip_ranges (list, optional): Optional list of IP ranges.
        db_categorized_urls (list, optional): DB-categorized URLs.
        keywords_retaining_parent_category (list, optional): Retained keywords from parent.
        ip_ranges_retaining_parent_category (list, optional): Retained IP ranges from parent.
        query_params (dict, optional): Filters for listing categories.
        use_legacy (bool, optional): Whether to use the legacy ZIA API client.
        service (str, optional): Defaults to 'zia'.

    Returns:
        dict | list[dict] | str:
            - For create/update/add/remove: A single category dict
            - For read: A list of categories or a single category dict
            - For delete: A success message

    Examples:
        Create a custom URL category:
        >>> result = url_category_manager(
        ...     action="create",
        ...     configured_name="Custom Social Media",
        ...     super_category="SOCIAL_NETWORKING",
        ...     description="Custom social media sites",
        ...     urls=["example-social.com", "custom-social.net"],
        ...     keywords=["social", "networking"],
        ...     custom_category=True
        ... )

        List all categories:
        >>> categories = url_category_manager(action="read")

        Get a specific category:
        >>> category = url_category_manager(action="read", category_id="CUSTOM_01")

        Full update (replaces all URLs and metadata):
        >>> result = url_category_manager(
        ...     action="update",
        ...     category_id="CUSTOM_01",
        ...     configured_name="Custom Social Media",
        ...     urls=["updated-site.com", "another-updated-site.com"],
        ...     description="Updated description"
        ... )

        Incremental update (add URLs to existing list):
        >>> result = url_category_manager(
        ...     action="add",
        ...     category_id="CUSTOM_01",
        ...     configured_name="Custom Social Media",
        ...     urls=["new-addition1.com", "new-addition2.com"]
        ... )

        Incremental update (remove URLs from existing list):
        >>> result = url_category_manager(
        ...     action="remove",
        ...     category_id="CUSTOM_01",
        ...     configured_name="Custom Social Media",
        ...     urls=["old-site.com", "legacy-entry.com"]
        ... )

        Delete a custom URL category:
        >>> result = url_category_manager(action="delete", category_id="CUSTOM_01")
    """
    if action not in ["create", "read", "update", "add", "remove", "delete"]:
        raise ValueError(
            f"Unsupported action: {action}. Must be one of 'create', 'read', 'update', 'add', 'remove', 'delete'."
        )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories

    if action == "create":
        if not configured_name or not super_category:
            raise ValueError(
                "configured_name and super_category are required for creation."
            )
        if custom_category is None:
            custom_category = True

        payload = {
            "configured_name": configured_name,
            "super_category": super_category,
            "custom_category": custom_category,
        }
        if urls:
            payload["urls"] = urls
        if description:
            payload["description"] = description
        if keywords:
            payload["keywords"] = keywords
        if ip_ranges:
            payload["ip_ranges"] = ip_ranges
        if db_categorized_urls:
            payload["db_categorized_urls"] = db_categorized_urls
        if keywords_retaining_parent_category:
            payload["keywords_retaining_parent_category"] = (
                keywords_retaining_parent_category
            )
        if ip_ranges_retaining_parent_category:
            payload["ip_ranges_retaining_parent_category"] = (
                ip_ranges_retaining_parent_category
            )

        created, _, err = api.add_url_category(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if category_id:
            result, _, err = api.get_category(category_id=category_id)
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            results, _, err = api.list_categories(query_params=query_params or {})
            if err:
                raise Exception(f"List failed: {err}")
            return [r.as_dict() for r in results]

    elif action == "add":
        if not category_id or not configured_name or not urls:
            raise ValueError(
                "category_id, configured_name, and urls are required for adding URLs."
            )
        payload = {
            "configured_name": configured_name,
            "urls": urls,
        }
        updated, _, err = api.add_urls_to_category(category_id=category_id, **payload)
        if err:
            raise Exception(f"Add failed: {err}")
        return updated.as_dict()

    elif action == "remove":
        if not category_id or not configured_name or not urls:
            raise ValueError(
                "category_id, configured_name, and urls are required for removing URLs."
            )
        payload = {
            "configured_name": configured_name,
            "urls": urls,
        }
        updated, _, err = api.delete_urls_from_category(
            category_id=category_id, **payload
        )
        if err:
            raise Exception(f"Remove failed: {err}")
        return updated.as_dict()

    elif action == "update":
        if not category_id or not configured_name:
            raise ValueError(
                "category_id and configured_name are required for full update."
            )
        payload = {
            "configured_name": configured_name,
        }
        if urls:
            payload["urls"] = urls
        if description:
            payload["description"] = description
        if keywords:
            payload["keywords"] = keywords
        if ip_ranges:
            payload["ip_ranges"] = ip_ranges
        if db_categorized_urls:
            payload["db_categorized_urls"] = db_categorized_urls
        if keywords_retaining_parent_category:
            payload["keywords_retaining_parent_category"] = (
                keywords_retaining_parent_category
            )
        if ip_ranges_retaining_parent_category:
            payload["ip_ranges_retaining_parent_category"] = (
                ip_ranges_retaining_parent_category
            )

        updated, _, err = api.update_url_category(category_id=category_id, **payload)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not category_id:
            raise ValueError("category_id is required for deletion.")
        _, _, err = api.delete_category(category_id=category_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted URL category {category_id}"
