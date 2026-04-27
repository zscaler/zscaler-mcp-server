"""ZIA Cloud Applications (policy-engine catalog) tools.

These tools wrap the SDK's ``client.zia.cloud_applications`` resource, which
returns the **policy-engine cloud-application catalog** — the canonical enum
strings (e.g. ``ONEDRIVE``, ``ONEDRIVE_PERSONAL``, ``SHAREPOINT_ONLINE``,
``DROPBOX``) consumed by the ``cloud_applications`` field on:

- SSL Inspection rules
- Web DLP rules
- Cloud App Control rules
- File Type Control rules
- Bandwidth Classes
- Advanced Settings

Use these tools when you need to look up the exact enum token to pass into a
policy rule's ``cloud_applications`` field. For the broader Shadow IT
analytics catalog (numeric IDs, friendly display names, sanction state,
custom tags) see ``zscaler_mcp/tools/zia/shadow_it_report.py``.
"""

from typing import Annotated, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def _build_query_params(
    search: Optional[str],
    page: Optional[int],
    page_size: Optional[int],
    app_class: Optional[str],
    group_results: Optional[bool],
) -> Optional[dict]:
    params: dict = {}
    if search:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    if app_class:
        params["app_class"] = app_class
    if group_results is not None:
        params["group_results"] = group_results
    return params or None


def zia_list_cloud_app_policy(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring filter on application name "
                "(e.g. 'sharepoint', 'onedrive'). Use this first to narrow "
                "results before applying a JMESPath query."
            )
        ),
    ] = None,
    app_class: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter by application category (e.g. 'WEB_MAIL', "
                "'ENTERPRISE_COLLABORATION', 'FILE_SHARE')."
            )
        ),
    ] = None,
    page: Annotated[
        Optional[int], Field(description="Page offset for pagination.")
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Page size (default 200, maximum 1000)."),
    ] = None,
    group_results: Annotated[
        Optional[bool],
        Field(description="If true, return application counts grouped by category."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection. "
                "Examples: '[?contains(name, `Share`)].{id: id, name: name}', "
                "'[?app_class==`ENTERPRISE_COLLABORATION`].name'."
            )
        ),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """List the ZIA policy-engine cloud-application catalog.

    Returns the predefined and user-defined cloud applications referenced by
    DLP rules, Cloud App Control rules, File Type Control rules, Bandwidth
    Classes, and Advanced Settings. Each entry includes the canonical enum
    string used as the ``cloud_applications`` value on policy rules.

    Supports both server-side filtering (``search``, ``app_class``,
    ``group_results``) and client-side JMESPath projection (``query``).

    Tip: when looking up the right enum to feed into an SSL inspection or
    DLP rule, prefer ``zia_list_cloud_app_ssl_policy`` if the target rule is
    SSL-inspection-scoped — its catalog can differ slightly from the generic
    policy catalog returned here.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    cloud_apps = client.zia.cloud_applications

    query_params = _build_query_params(search, page, page_size, app_class, group_results)

    apps, _, err = cloud_apps.list_cloud_app_policy(query_params=query_params)
    if err:
        raise Exception(f"Failed to list cloud application policies: {err}")
    results = [app.as_dict() for app in apps]
    return apply_jmespath(results, query)


def zia_list_cloud_app_ssl_policy(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring filter on application name "
                "(e.g. 'sharepoint', 'onedrive'). Use this first to narrow "
                "results before applying a JMESPath query."
            )
        ),
    ] = None,
    app_class: Annotated[
        Optional[str],
        Field(description="Filter by application category."),
    ] = None,
    page: Annotated[
        Optional[int], Field(description="Page offset for pagination.")
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Page size (default 200, maximum 1000)."),
    ] = None,
    group_results: Annotated[
        Optional[bool],
        Field(description="If true, return application counts grouped by category."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection. "
                "Example: '[?contains(name, `Share`)].{id: id, name: name}'."
            )
        ),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """List the ZIA cloud-application catalog scoped to SSL Inspection rules.

    Returns the predefined and user-defined cloud applications that are
    addressable by the ``cloud_applications`` field on SSL Inspection rules.
    Each entry includes the canonical enum string ZIA expects when creating
    or updating an SSL Inspection rule.

    This is the right tool to call when answering "what enum should I pass
    into ``cloud_applications`` for SharePoint Online / OneDrive / Box / …?"
    because it returns the exact strings the SSL Inspection API will accept.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    cloud_apps = client.zia.cloud_applications

    query_params = _build_query_params(search, page, page_size, app_class, group_results)

    apps, _, err = cloud_apps.list_cloud_app_ssl_policy(query_params=query_params)
    if err:
        raise Exception(f"Failed to list cloud application SSL policies: {err}")
    results = [app.as_dict() for app in apps]
    return apply_jmespath(results, query)
