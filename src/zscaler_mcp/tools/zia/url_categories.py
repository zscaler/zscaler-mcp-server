"""ZIA URL categories — list, lookup, get (+ predefined), create, update, delete.

Mirrors v1's ``client.zia.url_categories`` SDK calls. Two category kinds:

* **Custom** — fully CRUD-able (``zia_create/update/delete_url_category``).
* **Predefined** — Zscaler-curated; cannot be created/deleted. Read via
  ``zia_get_url_category_predefined``; full-replace via
  ``zia_update_url_category_predefined``; incremental URL/IP changes via
  ``zia_add_urls_to_category`` / ``zia_remove_urls_from_category``.

Listing uses ``/urlCategories`` with the two query parameters it actually
honours, ``custom_only`` and ``type``, plus the SDK-local ``search``. The
endpoint does not paginate and offers no way to omit a category's URL, keyword
and IP lists, so a listing carries whatever those categories hold — the response
that exhausted a customer's token budget, with no API switch for it. Narrowing
before the call and projecting with ``query`` after it are the only levers; one
category's full definition comes from ``zia_get_url_category``, and "which
category is this URL in?" is ``zia_url_lookup``.

``/urlCategories/lite`` is deliberately NOT used. It takes no parameters, so it
cannot filter, and it omits ``configuredName`` — which is the only handle a
custom category has, since its id is a generated string.

Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.common.zia_helpers import resolve_predefined_category
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    """Inputs for listing URL categories.

    ``custom_only`` and ``type`` are real query parameters on ``/urlCategories``
    and go upstream; ``search`` is applied by the SDK to the response.

    Nothing else is advertised, because nothing else works. ``page`` /
    ``page_size`` were dropped on the floor by the API while telling an agent it
    could page through a large result. ``include_only_url_keyword_counts`` was
    briefly exposed here on the assumption that it replaces the URL/keyword/IP
    lists with counts; a tenant response captured with it both on and off is
    byte-for-byte equivalent, ``dbCategorizedUrls`` and ``ipRanges`` populated in
    both, so it is not sent at all.

    ``custom_only`` matters more than it looks. "List the custom URL categories"
    is the most common way this tool is asked for, and without a typed parameter
    the agent has to write a JMESPath ``query`` and guess the field spelling.
    Observed in practice: it guessed ``customCategory`` (the API's spelling)
    where the record carries ``custom_category``, got an empty list back, and
    could not tell that apart from a tenant with no custom categories.
    """

    search: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Case-insensitive substring match on the category's configured name. "
                "Applied by the SDK to the response, not by the API — combine it with "
                "`custom_only` / `type` to also cut what is fetched. A category with "
                "no configured name never matches, so if a search comes back empty, "
                "retry without it and match on the id instead."
            ),
        ),
    ] = None
    custom_only: Annotated[
        Optional[bool],
        Field(
            default=None,
            description=(
                "True fetches ONLY custom (admin-created) categories. This is a real "
                "API filter. Use it for 'list the custom URL categories' rather than "
                "listing everything and filtering with a JMESPath `query` — it cannot "
                "be spelled wrong, and it does not transfer the predefined categories."
            ),
        ),
    ] = None
    type: Annotated[
        Optional[str],
        Field(
            default=None,
            description="API filter by category type: URL_CATEGORY, TLD_CATEGORY or ALL.",
        ),
    ] = None


class LookupInput(BaseModel):
    urls: Annotated[
        list[str],
        Field(
            description="URLs/domains to categorize (e.g. ['google.com', 'acme.com']). "
            "Accepts a list or JSON string. Processed in batches of 100."
        ),
    ]


class GetInput(BaseModel):
    category_id: Annotated[str, Field(description="Category ID.")]


class GetPredefinedInput(BaseModel):
    name: Annotated[
        str,
        Field(
            description="Predefined category ID (e.g. 'FINANCE') or display name "
            "(e.g. 'Finance'). Case-insensitive. Refuses custom categories."
        ),
    ]


class CreateInput(BaseModel):
    configured_name: Annotated[str, Field(description="Category name (required).")]
    super_category: Annotated[str, Field(description="Super category (required).")]
    urls: Annotated[Optional[list[str]], Field(default=None, description="List of URLs.")] = None
    description: Annotated[Optional[str], Field(default=None, description="Description.")] = None
    keywords: Annotated[
        Optional[list[str]], Field(default=None, description="Custom keywords.")
    ] = None
    ip_ranges: Annotated[Optional[list[str]], Field(default=None, description="IP ranges.")] = None
    advanced: Annotated[
        Optional[dict[str, Any]],
        Field(
            default=None,
            description="Less-common fields: db_categorized_urls, "
            "keywords_retaining_parent_category, ip_ranges_retaining_parent_category.",
        ),
    ] = None


class UpdateInput(BaseModel):
    category_id: Annotated[str, Field(description="Category ID (required).")]
    configured_name: Annotated[str, Field(description="Category name (required).")]
    urls: Annotated[
        Optional[list[str]], Field(default=None, description="URLs (full replace).")
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Description.")] = None
    keywords: Annotated[
        Optional[list[str]], Field(default=None, description="Custom keywords.")
    ] = None
    ip_ranges: Annotated[Optional[list[str]], Field(default=None, description="IP ranges.")] = None
    advanced: Annotated[
        Optional[dict[str, Any]],
        Field(default=None, description="Less-common fields (see create)."),
    ] = None


class UpdatePredefinedInput(BaseModel):
    name: Annotated[
        str,
        Field(description="Predefined category ID or display name (case-insensitive)."),
    ]
    configured_name: Annotated[
        Optional[str],
        Field(default=None, description="Display name; backfilled from existing if omitted."),
    ] = None
    urls: Annotated[
        Optional[list[str]],
        Field(default=None, description="URLs (full replace of curated list)."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Description.")] = None
    keywords: Annotated[
        Optional[list[str]], Field(default=None, description="Custom keywords.")
    ] = None
    ip_ranges: Annotated[Optional[list[str]], Field(default=None, description="IP ranges.")] = None
    advanced: Annotated[
        Optional[dict[str, Any]],
        Field(default=None, description="Less-common fields (see create)."),
    ] = None


class IncrementalUrlsInput(BaseModel):
    category_id: Annotated[str, Field(description="Category ID (required).")]
    configured_name: Annotated[str, Field(description="Category name (required).")]
    urls: Annotated[list[str], Field(description="URLs to add/remove (required).")]


class DeleteInput(BaseModel):
    category_id: Annotated[str, Field(description="Category ID (required).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _advanced_payload(advanced: Optional[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in (
        "db_categorized_urls",
        "keywords_retaining_parent_category",
        "ip_ranges_retaining_parent_category",
    ):
        if advanced and advanced.get(key) is not None:
            out[key] = parse_list(advanced[key])
    return out


# =============================================================================
# READ
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_url_categories",
    input_model=ListInput,
    is_list=True,
)
def zia_list_url_categories(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA URL categories. Narrow the request — this response can be large.

    ASK THE USER FOR SCOPE BEFORE CALLING THIS UNFILTERED. This endpoint does not
    paginate: everything matching the request comes back in a single response,
    and a large tenant holds thousands of categories. If the request was broad
    ("show me the URL categories"), ask which ones they mean — custom or
    predefined (`custom_only`), URL or TLD (`type`), or a name to match
    (`search`) — and call once with that answer. Do not call unfiltered first
    and narrow afterwards; the cost is already paid by then.

    Use this to see what categories exist, or to resolve a category id before
    calling another tool. For predefined categories the id IS the name
    (`OTHER_ADULT_MATERIAL`); custom categories carry a generated id and are
    identified by `configured_name`.

    For "list the custom URL categories", pass `custom_only=True` — that is a
    real API filter, so only those categories are fetched.

    Every category comes back with its URL, keyword and IP lists in full. The API
    has no parameter to return counts instead, so on a tenant whose categories
    hold large URL lists this response is big and nothing about the call itself
    makes it smaller. Two things do: filter before calling, and pass a `query`
    projection when the answer needs only part of each record — for example
    `[*].{id: id, name: configured_name, urls: custom_urls_count}` for an
    inventory rather than the URLs themselves. The projection is applied before
    the response is encoded, so it is a real saving, not cosmetic.

    Filtering narrows WHICH categories are returned; it cannot cap HOW MANY. A
    tenant with 5000 custom categories returns 5000 rows for `custom_only=True`.

    Use `zia_get_url_category` for one category's full definition once you know
    its id. To find which category a specific URL belongs to, use
    `zia_url_lookup` — a different question, and this tool does not answer it.
    """
    client = get_zscaler_client(service="zia")
    # `custom_only` and `type` are real query parameters on `/urlCategories`; the
    # SDK applies `search` locally against `configured_name`. Only send keys the
    # caller set, so the API's own defaults govern anything left unspecified.
    query_params: dict[str, Any] = {}
    if args.custom_only is not None:
        query_params["custom_only"] = args.custom_only
    if args.type:
        query_params["type"] = args.type
    if args.search:
        query_params["search"] = args.search
    results, _, err = client.zia.url_categories.list_categories(query_params=query_params)
    if err:
        raise RuntimeError(f"Failed to list URL categories: {err}")
    return shape_many([r.as_dict() for r in (results or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_url_categories",
    input_model=LookupInput,
    is_list=True,
)
def zia_url_lookup(args: LookupInput) -> list[dict[str, Any]]:
    """Which category does a URL belong to? Use THIS for that question.

    Answers "what category is twilio.com?" directly: pass the URLs and get back
    Zscaler's classification for each, e.g.
    `{"url": "notpurple.com", "urlClassifications": ["SPECIALIZED_SHOPPING"]}`.
    The response is small and scales with the number of URLs you ask about, not
    with the size of the tenant's category inventory.

    Do NOT try to answer it by listing categories. `zia_list_url_categories`
    returns the category inventory without any URLs in it, so it cannot tell you
    where a URL landed no matter how much of it you read.

    Two limits worth knowing. Only Zscaler's PREDEFINED classification is
    returned, so a URL matched by a custom category still reports its predefined
    category here. And up to 100 URLs may be looked up per request; a URL in no
    predefined category comes back as `MISCELLANEOUS_OR_UNKNOWN`.
    """
    urls = parse_list(args.urls)
    if not urls:
        raise ValueError("urls cannot be empty")
    client = get_zscaler_client(service="zia")
    results, err = client.zia.url_categories.lookup(urls=urls)
    if err:
        raise RuntimeError(f"URL lookup failed: {err}")
    out: list[dict[str, Any]] = []
    for r in results or []:
        out.append(r.as_dict() if hasattr(r, "as_dict") else dict(r))
    return shape_many(out)


@tool(
    action=READ,
    service="zia",
    toolset="zia_url_categories",
    input_model=GetInput,
    is_list=False,
)
def zia_get_url_category(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA URL category by ID (full detail)."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.url_categories.get_category(category_id=args.category_id)
    if err:
        raise RuntimeError(f"Failed to get URL category {args.category_id}: {err}")
    return shape_one(result.as_dict())


@tool(
    action=READ,
    service="zia",
    toolset="zia_url_categories",
    input_model=GetPredefinedInput,
    is_list=False,
)
def zia_get_url_category_predefined(args: GetPredefinedInput) -> dict[str, Any]:
    """Get a Zscaler-curated **predefined** URL category by ID or display name."""
    client = get_zscaler_client(service="zia")
    return shape_one(resolve_predefined_category(client, args.name))


# =============================================================================
# WRITE
# =============================================================================


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_url_categories",
    input_model=CreateInput,
    is_list=False,
)
def zia_create_url_category(args: CreateInput) -> dict[str, Any]:
    """Create a new **custom** ZIA URL category (write). Activate after."""
    payload: dict[str, Any] = {
        "configured_name": args.configured_name,
        "super_category": args.super_category,
        "custom_category": True,
    }
    if args.urls is not None:
        payload["urls"] = parse_list(args.urls)
    if args.description is not None:
        payload["description"] = args.description
    if args.keywords is not None:
        payload["keywords"] = parse_list(args.keywords)
    if args.ip_ranges is not None:
        payload["ip_ranges"] = parse_list(args.ip_ranges)
    payload.update(_advanced_payload(args.advanced))

    client = get_zscaler_client(service="zia")
    created, _, err = client.zia.url_categories.add_url_category(**payload)
    if err:
        raise RuntimeError(f"Failed to create URL category: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_url_categories",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_url_category(args: UpdateInput) -> dict[str, Any]:
    """Update a **custom** ZIA URL category (full PUT-replace). Activate after.

    Refuses predefined categories — use zia_update_url_category_predefined or the
    incremental add/remove tools instead.
    """
    client = get_zscaler_client(service="zia")
    api = client.zia.url_categories

    existing, _, err = api.get_category(category_id=args.category_id)
    if err:
        raise RuntimeError(f"Failed to read URL category {args.category_id}: {err}")
    existing_dict = existing.as_dict() if hasattr(existing, "as_dict") else dict(existing)
    if not existing_dict.get("custom_category"):
        raise ValueError(
            f"{args.category_id!r} is a predefined URL category. A full-replace "
            "PUT would obliterate Zscaler's curated list. Use "
            "zia_update_url_category_predefined, or zia_add_urls_to_category / "
            "zia_remove_urls_from_category for incremental changes."
        )

    payload: dict[str, Any] = {"configured_name": args.configured_name}
    if args.urls is not None:
        payload["urls"] = parse_list(args.urls)
    if args.description is not None:
        payload["description"] = args.description
    if args.keywords is not None:
        payload["keywords"] = parse_list(args.keywords)
    if args.ip_ranges is not None:
        payload["ip_ranges"] = parse_list(args.ip_ranges)
    payload.update(_advanced_payload(args.advanced))

    updated, _, err = api.update_url_category(category_id=args.category_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update URL category {args.category_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_url_categories",
    input_model=UpdatePredefinedInput,
    is_list=False,
)
def zia_update_url_category_predefined(args: UpdatePredefinedInput) -> dict[str, Any]:
    """Update a Zscaler-curated **predefined** URL category (full PUT). Activate after.

    For incremental "add a few URLs to FINANCE" workflows prefer
    zia_add_urls_to_category / zia_remove_urls_from_category instead.
    """
    client = get_zscaler_client(service="zia")
    api = client.zia.url_categories

    existing = resolve_predefined_category(client, args.name)
    category_id = existing["id"]

    payload: dict[str, Any] = {
        "configured_name": args.configured_name or existing.get("configured_name"),
    }
    if args.urls is not None:
        payload["urls"] = parse_list(args.urls)
    if args.description is not None:
        payload["description"] = args.description
    if args.keywords is not None:
        payload["keywords"] = parse_list(args.keywords)
    if args.ip_ranges is not None:
        payload["ip_ranges"] = parse_list(args.ip_ranges)
    payload.update(_advanced_payload(args.advanced))

    updated, _, err = api.update_url_category(category_id=category_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update predefined URL category {category_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_url_categories",
    input_model=IncrementalUrlsInput,
    is_list=False,
)
def zia_add_urls_to_category(args: IncrementalUrlsInput) -> dict[str, Any]:
    """Incrementally add URLs to an existing ZIA URL category. Activate after."""
    client = get_zscaler_client(service="zia")
    updated, _, err = client.zia.url_categories.add_urls_to_category(
        category_id=args.category_id,
        configured_name=args.configured_name,
        urls=parse_list(args.urls),
    )
    if err:
        raise RuntimeError(f"Failed to add URLs to category {args.category_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_url_categories",
    input_model=IncrementalUrlsInput,
    is_list=False,
)
def zia_remove_urls_from_category(args: IncrementalUrlsInput) -> dict[str, Any]:
    """Incrementally remove URLs from an existing ZIA URL category. Activate after."""
    client = get_zscaler_client(service="zia")
    updated, _, err = client.zia.url_categories.delete_urls_from_category(
        category_id=args.category_id,
        configured_name=args.configured_name,
        urls=parse_list(args.urls),
    )
    if err:
        raise RuntimeError(f"Failed to remove URLs from category {args.category_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_url_categories",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_url_category(args: DeleteInput) -> dict[str, Any]:
    """Delete a **custom** ZIA URL category (destructive). Activate after.

    Refuses predefined categories — those are Zscaler-curated and cannot be
    deleted via the API.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    api = client.zia.url_categories

    existing, _, err = api.get_category(category_id=args.category_id)
    if err:
        raise RuntimeError(f"Failed to read URL category {args.category_id}: {err}")
    existing_dict = existing.as_dict() if hasattr(existing, "as_dict") else dict(existing)
    if not existing_dict.get("custom_category"):
        raise ValueError(
            f"{args.category_id!r} is a predefined URL category. Predefined "
            "categories are Zscaler-curated and cannot be deleted via the API."
        )

    _, _, err = api.delete_category(category_id=args.category_id)
    if err:
        raise RuntimeError(f"Failed to delete URL category {args.category_id}: {err}")
    return OperationResult(
        success=True, message=f"URL category {args.category_id} deleted successfully."
    ).model_dump()
