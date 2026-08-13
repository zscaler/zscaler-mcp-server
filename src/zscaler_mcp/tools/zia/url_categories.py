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
    contains_url: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Return ONLY the categories whose configured URL entries match this "
                "URL or domain — the direct answer to 'which custom category contains "
                "app.box.com?'. Combine with custom_only=True for exactly that "
                "question. Matching is applied by the server, is domain-aware "
                "(an entry `.box.com` matches `app.box.com`; schemes, paths and case "
                "are ignored), and covers the `urls` and `db_categorized_urls` "
                "entries an admin configured. It does NOT consult Zscaler's own "
                "curated classification — that question is `zia_url_lookup`. Each "
                "returned category carries a `_url_match` field naming the entries "
                "that matched."
            ),
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


def _url_host(value: str) -> str:
    """Reduce a URL or domain to its bare host for matching.

    Accepts whatever an admin is likely to paste — `app.box.com`,
    `https://app.box.com/folder/x?y=1`, `APP.BOX.COM:443` — and returns
    `app.box.com`. Matching is by domain; schemes, paths, query strings, ports
    and case carry no meaning in a category's URL entries.
    """
    host = value.strip().lower()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0].split("?", 1)[0].split(":", 1)[0]
    return host.strip(".")


def _entry_matches_host(entry: str, host: str) -> bool:
    """True when a category URL entry covers ``host``, per ZIA semantics.

    A leading dot on an entry (`.box.com`) explicitly includes subdomains, and a
    bare entry (`box.com`) covers the domain itself and its subdomains too — so
    both reduce to the same rule: exact match, or ``host`` ends with
    ``"." + entry``. The suffix check is anchored at a label boundary, so
    `box.com` never matches `notbox.com`.
    """
    entry_host = _url_host(entry)
    if not entry_host:
        return False
    return host == entry_host or host.endswith("." + entry_host)


def _match_categories_containing(rows: list[dict[str, Any]], url: str) -> list[dict[str, Any]]:
    """Keep only the categories whose configured entries cover ``url``.

    Searches the admin-configured entry lists (`urls`, `db_categorized_urls`) —
    the fields the customer's own screenshots showed the answer living in
    (`.app.box.com` inside CUSTOM_44). Zscaler's curated classification is NOT
    consulted here; that is `zia_url_lookup`'s job.

    Matching categories are returned as the verbatim record plus one additive
    `_url_match` field naming the entries that matched — same audit-trail
    pattern as `_cloud_applications_resolution`, so the agent can explain WHY a
    category matched instead of guessing.
    """
    host = _url_host(url)
    matched_rows: list[dict[str, Any]] = []
    for row in rows:
        matches: list[dict[str, Any]] = []
        for field in ("urls", "db_categorized_urls", "dbCategorizedUrls"):
            for entry in row.get(field) or []:
                if isinstance(entry, str) and _entry_matches_host(entry, host):
                    matches.append({"field": field, "entry": entry})
        if matches:
            matched_rows.append({**row, "_url_match": {"url": url, "matched": matches}})
    return matched_rows


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

    For "WHICH custom category contains app.box.com?", pass
    `custom_only=True, contains_url="app.box.com"` — ONE call, and only the
    matching categories come back, each annotated with `_url_match` naming the
    entries that matched. Do NOT list all custom categories and scan their URL
    lists yourself: the server's matching understands ZIA's domain semantics
    (`.app.box.com` covers `app.box.com`), and a manual scan of full records is
    exactly the response that exhausts token budgets on large tenants.

    Every category comes back with its URL, keyword and IP lists in full. The API
    has no parameter to return counts instead, so on a tenant whose categories
    hold large URL lists this response is big and nothing about the call itself
    makes it smaller. Three things do: `contains_url` when the question is about
    one URL, filtering before calling, and a `query` projection when the answer
    needs only part of each record — for example
    `[*].{id: id, name: configured_name, urls: custom_urls_count}` for an
    inventory rather than the URLs themselves. The projection is applied before
    the response is encoded, so it is a real saving, not cosmetic.

    Filtering narrows WHICH categories are returned; it cannot cap HOW MANY. A
    tenant with 5000 custom categories returns 5000 rows for `custom_only=True`.

    Use `zia_get_url_category` for one category's full definition once you know
    its id. For Zscaler's own (predefined) classification of a URL, use
    `zia_url_lookup` — that is a different question, and this tool's
    `contains_url` only searches admin-configured entries, never Zscaler's
    curated database.
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
    rows = [r.as_dict() for r in (results or [])]
    if args.contains_url:
        # Server-side, because the API has no such filter and the alternative is
        # shipping every full record for the agent to scan — the 100k-token
        # response this parameter exists to prevent.
        rows = _match_categories_containing(rows, args.contains_url)
    return shape_many(rows)


@tool(
    action=READ,
    service="zia",
    toolset="zia_url_categories",
    input_model=LookupInput,
    is_list=True,
)
def zia_url_lookup(args: LookupInput) -> list[dict[str, Any]]:
    """Which category does a URL belong to? Use THIS for that question — default.

    Answers "what category is twilio.com?" directly: pass the URLs and get back
    Zscaler's classification for each, e.g.
    `{"url": "notpurple.com", "urlClassifications": ["SPECIALIZED_SHOPPING"]}`.
    The response is small and scales with the number of URLs you ask about, not
    with the size of the tenant's category inventory.

    This returns Zscaler's PREDEFINED classification ONLY. It does not report
    the tenant's custom categories: a URL an admin placed in a custom category
    still shows its predefined category here. When the user explicitly asks
    about CUSTOM categories ("which custom category contains app.box.com?"),
    make ONE call to
    `zia_list_url_categories(custom_only=True, contains_url="app.box.com")` —
    the server does the matching and returns only the categories that contain
    the URL. Do not answer the custom question from this tool's output, and do
    not list all categories and scan them yourself.

    Unless the user says "custom", this tool alone answers the question — stop
    after it. Up to 100 URLs per request; a URL in no predefined category comes
    back as `MISCELLANEOUS_OR_UNKNOWN`.
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
