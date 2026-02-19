from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_url_categories(
    query_params: Annotated[Optional[Dict], Field(description="Optional filters for pagination and filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List all ZIA URL categories with optional filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories
    
    results, _, err = api.list_categories(query_params=query_params or {})
    if err:
        raise Exception(f"List failed: {err}")
    return [r.as_dict() for r in results]


def zia_url_lookup(
    urls: Annotated[
        Union[List[str], str],
        Field(
            description="List of URLs to perform a category lookup on. "
            "Examples: ['google.com', 'acme.com'], ['example.com', 'github.com']. Accepts JSON string or list. "
            "URLs are processed in batches of 100; large lists may take longer due to API rate limiting."
        ),
    ],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """
    Look up the URL category for the provided URLs.

    Performs a bulk category lookup against the Zscaler URL categorization database.
    Each URL is matched to a category (e.g., SEARCH_ENGINES, BUSINESS_AND_ECONOMY,
    COMPUTER_AND_INTERNET_SECURITY). URLs are processed in batches of 100 with
    a short delay between batches to respect API limits.

    Args:
        urls: List of URLs or domains to look up (e.g., "google.com", "acme.com").
            Accepts a list or JSON string. Maximum 100 URLs per batch; larger
            lists are processed in multiple batches automatically.
        use_legacy: Whether to use the legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of URL category report entries. Each entry typically includes:
        - url: The URL or domain that was looked up
        - urlCategories: List of category IDs/names the URL belongs to
        - Other categorization metadata from the ZIA URL Lookup API

    Examples:
        >>> # Look up category for a single URL
        >>> results = zia_url_lookup(urls=["google.com"])
        >>> for entry in results:
        ...     print(f"URL: {entry.get('url')}, Categories: {entry.get('urlCategories', [])}")

        >>> # Look up categories for multiple URLs
        >>> results = zia_url_lookup(urls=["google.com", "acme.com", "github.com"])
        >>> print(f"Looked up {len(results)} URLs")
        >>> for entry in results:
        ...     print(f"  {entry.get('url')}: {entry.get('urlCategories', [])}")

        >>> # Look up category for a domain
        >>> results = zia_url_lookup(urls=["finance.yahoo.com"])
        >>> if results:
        ...     print(f"Yahoo Finance category: {results[0]}")

        >>> # Pass URLs as JSON string
        >>> results = zia_url_lookup(urls='["example.com", "microsoft.com"]')
        >>> for entry in results:
        ...     print(entry)
    """
    # Normalize urls: accept list or JSON string
    if isinstance(urls, str):
        import json

        try:
            urls = json.loads(urls)
        except json.JSONDecodeError:
            urls = [u.strip() for u in urls.split(",") if u.strip()]
    if not isinstance(urls, list):
        raise ValueError("urls must be a list of URL strings or a JSON string")
    if not urls:
        raise ValueError("urls cannot be empty")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories

    results, err = api.lookup(urls=urls)
    if err:
        raise Exception(f"URL lookup failed: {err}")

    # Results may be dicts or objects with as_dict(); normalize to dicts
    out = []
    for r in results:
        if hasattr(r, "as_dict"):
            out.append(r.as_dict())
        elif isinstance(r, dict):
            out.append(r)
        else:
            out.append(dict(r) if hasattr(r, "__iter__") and not isinstance(r, str) else {"url": str(r), "raw": r})
    return out or []


def zia_get_url_category(
    category_id: Annotated[str, Field(description="Category ID.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA URL category by ID."""
    if not category_id:
        raise ValueError("category_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories
    
    result, _, err = api.get_category(category_id=category_id)
    if err:
        raise Exception(f"Read failed: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_url_category(
    configured_name: Annotated[str, Field(description="Name of the category (required).")],
    super_category: Annotated[str, Field(description="Super category (required for custom categories).")],
    urls: Annotated[Optional[List[str]], Field(description="List of URLs.")] = None,
    description: Annotated[Optional[str], Field(description="Optional description for the category.")] = None,
    custom_category: Annotated[bool, Field(description="Must be True for custom categories.")] = True,
    keywords: Annotated[Optional[List[str]], Field(description="Custom keywords.")] = None,
    ip_ranges: Annotated[Optional[List[str]], Field(description="Optional list of IP ranges.")] = None,
    db_categorized_urls: Annotated[Optional[List[str]], Field(description="DB-categorized URLs.")] = None,
    keywords_retaining_parent_category: Annotated[Optional[List[str]], Field(description="Retained keywords from parent.")] = None,
    ip_ranges_retaining_parent_category: Annotated[Optional[List[str]], Field(description="Retained IP ranges from parent.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Create a new custom ZIA URL category."""
    if not configured_name or not super_category:
        raise ValueError("configured_name and super_category are required for creation")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories
    
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
        payload["keywords_retaining_parent_category"] = keywords_retaining_parent_category
    if ip_ranges_retaining_parent_category:
        payload["ip_ranges_retaining_parent_category"] = ip_ranges_retaining_parent_category
    
    created, _, err = api.add_url_category(**payload)
    if err:
        raise Exception(f"Create failed: {err}")
    return created.as_dict()


def zia_update_url_category(
    category_id: Annotated[str, Field(description="Category ID (required).")],
    configured_name: Annotated[str, Field(description="Name of the category (required).")],
    urls: Annotated[Optional[List[str]], Field(description="List of URLs (full replacement).")] = None,
    description: Annotated[Optional[str], Field(description="Optional description for the category.")] = None,
    keywords: Annotated[Optional[List[str]], Field(description="Custom keywords.")] = None,
    ip_ranges: Annotated[Optional[List[str]], Field(description="Optional list of IP ranges.")] = None,
    db_categorized_urls: Annotated[Optional[List[str]], Field(description="DB-categorized URLs.")] = None,
    keywords_retaining_parent_category: Annotated[Optional[List[str]], Field(description="Retained keywords from parent.")] = None,
    ip_ranges_retaining_parent_category: Annotated[Optional[List[str]], Field(description="Retained IP ranges from parent.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Update an existing ZIA URL category (full replacement of all fields)."""
    if not category_id or not configured_name:
        raise ValueError("category_id and configured_name are required for full update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories
    
    payload = {"configured_name": configured_name}
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
        payload["keywords_retaining_parent_category"] = keywords_retaining_parent_category
    if ip_ranges_retaining_parent_category:
        payload["ip_ranges_retaining_parent_category"] = ip_ranges_retaining_parent_category
    
    updated, _, err = api.update_url_category(category_id=category_id, **payload)
    if err:
        raise Exception(f"Update failed: {err}")
    return updated.as_dict()


def zia_add_urls_to_category(
    category_id: Annotated[str, Field(description="Category ID (required).")],
    configured_name: Annotated[str, Field(description="Name of the category (required).")],
    urls: Annotated[List[str], Field(description="List of URLs to add (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Incrementally add URLs to an existing ZIA URL category."""
    if not category_id or not configured_name or not urls:
        raise ValueError("category_id, configured_name, and urls are required for adding URLs")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories
    
    payload = {"configured_name": configured_name, "urls": urls}
    updated, _, err = api.add_urls_to_category(category_id=category_id, **payload)
    if err:
        raise Exception(f"Add URLs failed: {err}")
    return updated.as_dict()


def zia_remove_urls_from_category(
    category_id: Annotated[str, Field(description="Category ID (required).")],
    configured_name: Annotated[str, Field(description="Name of the category (required).")],
    urls: Annotated[List[str], Field(description="List of URLs to remove (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> Union[str, Dict]:
    """Incrementally remove URLs from an existing ZIA URL category.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_remove_urls_from_category",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not category_id or not configured_name or not urls:
        raise ValueError("category_id, configured_name, and urls are required for removing URLs")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories
    
    payload = {"configured_name": configured_name, "urls": urls}
    updated, _, err = api.delete_urls_from_category(category_id=category_id, **payload)
    if err:
        raise Exception(f"Remove URLs failed: {err}")
    return updated.as_dict()


def zia_delete_url_category(
    category_id: Annotated[str, Field(description="Category ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """Delete a custom ZIA URL category."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_url_category",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not category_id:
        raise ValueError("category_id is required for deletion")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.url_categories
    
    _, _, err = api.delete_category(category_id=category_id)
    if err:
        raise Exception(f"Delete failed: {err}")
    return f"Deleted URL category {category_id}"
