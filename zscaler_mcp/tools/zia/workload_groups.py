"""ZIA Workload Groups — read-only list/get tools.

Workload Groups are referenced by ID on the ``workload_groups`` operand
of these ZIA rule resources:

- Cloud Firewall Filtering rules
- URL Filtering rules
- SSL Inspection rules
- Web DLP rules

The ZIA SDK does support create/update/delete for Workload Groups, but
this MCP server intentionally exposes only the read-only operations —
Workload Group expressions are non-trivial JSON DSL payloads, and admins
are expected to author them in the ZIA UI. The list/get tools are wired
purely to support the operand-resolution workflow on rule resources.
"""

from typing import Annotated, Any, Dict, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath


def zia_list_workload_groups(
    page: Annotated[Optional[int], Field(description="Page offset for pagination.")] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Page size. Default 250; maximum 1000."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection. "
                "Useful when looking up a workload group by name — the ZIA "
                "list endpoint does not expose a server-side ``name`` filter, "
                "so projection like ``[?name=='WG-AWS-Prod'].id`` is the "
                "supported path."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """List ZIA workload groups, used as the ``workload_groups`` operand on rule resources.

    Workload groups are referenced by ID on Cloud Firewall, URL Filtering,
    SSL Inspection, and Web DLP rules. This tool is read-only — workload
    group authoring (with its expression DSL) is intentionally left to the
    ZIA UI.

    The ZIA list endpoint does not support a server-side name filter; pair
    this tool with a JMESPath ``query`` to find a group by name (e.g.
    ``query="[?name=='WG-AWS-Prod']"``).
    """
    query_params: Dict[str, Any] = {}
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size

    client = get_zscaler_client(service=service)
    wlg_api = client.zia.workload_groups

    result, _, err = wlg_api.list_groups(query_params=query_params or None)
    if err:
        raise Exception(f"Failed to list workload groups: {err}")
    results = [grp.as_dict() for grp in result or []]
    return apply_jmespath(results, query)


def zia_get_workload_group(
    group_id: Annotated[int, Field(description="Workload group ID.")],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Get a specific ZIA workload group by ID."""
    if not group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service=service)
    wlg_api = client.zia.workload_groups

    result, _, err = wlg_api.get_group(group_id)
    if err:
        raise Exception(f"Failed to get workload group {group_id}: {err}")
    return result.as_dict()
