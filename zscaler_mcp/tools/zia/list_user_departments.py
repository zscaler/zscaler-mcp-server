from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_user_department_manager(
    action: Annotated[
        Literal["read", "read_lite"],
        Field(
            description=(
                "Operation to perform. Use 'read' to paginate/filter departments, "
                "'read' to fetch a department by ID, or 'read_lite' for the lite version."
            )
        ),
    ] = "read",
    department_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Department ID. Required for 'read' and 'read_lite' actions."),
    ] = None,
    limit_search: Annotated[
        Optional[bool],
        Field(description="If true, limits the search to match against the department name only."),
    ] = None,
    search: Annotated[
        Optional[str],
        Field(description="Search string to match against department name or user attributes."),
    ] = None,
    page: Annotated[
        Optional[int],
        Field(description="Page offset for pagination when listing departments."),
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Page size for listing departments. Default is 100; maximum is 1000."),
    ] = None,
    sort_by: Annotated[
        Optional[Literal["id", "name", "expiry", "status", "external_id", "rank"]],
        Field(description="Sort field for listing departments."),
    ] = None,
    sort_order: Annotated[
        Optional[Literal["asc", "desc", "rule_execution"]],
        Field(description="Sort order for listing departments."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="Zscaler service name. Always 'zia' for this tool.")] = "zia",
) -> Union[dict, List[dict]]:
    """
    ZIA User Departments manager using the Python SDK.

    This tool uses the SDK methods `list_departments(query_params)`,
    `get_department(department_id)`, and `get_department_lite(department_id)`.

    Supported actions:
    - "read": Retrieves a paginated list of departments with optional filters and sorting.
    - "read": Retrieves a single department by its unique identifier.
    - "get_lite": Retrieves a single department by ID using the lite endpoint.

    Parameters
    - action: One of ["list", "get", "get_lite"]. Defaults to "list".
    - department_id: Required when action is "get" or "get_lite". The unique department ID (int or str).
    - limit_search: Optional bool. If true, limits search to department name only.
    - search: Optional search string to match against department name or applicable attributes.
    - page: Optional page offset for pagination.
    - page_size: Optional page size for pagination. The SDK's default is 100; maximum is 1000.
    - sort_by: Optional sort field. Supported values: "id", "name", "expiry", "status", "external_id", "rank".
    - sort_order: Optional sort order. Supported values: "asc", "desc", "rule_execution".
    - use_legacy: Whether to use the legacy client implementation.
    - service: Zscaler service. Use "zia".

    Returns:
    - For action "read": List[dict] — each element represents a department as a dictionary.
    - For action "get" and "get_lite": dict — the department represented as a dictionary.

    Examples:
    
    - List departments with search and sorting
      >>> zia_user_department_manager(
      ...     action="read",
      ...     search="Finance",
      ...     limit_search=True,
      ...     page=1,
      ...     page_size=500,
      ...     sort_by="name",
      ...     sort_order="asc",
      ... )

    - Get a department by ID
      >>> zia_user_department_manager(action="read", department_id="99999")

    - Get a department by ID using the lite endpoint
      >>> zia_user_department_manager(action="get_lite", department_id="99999")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.user_management

    if action == "read":
        # If department_id is provided, get a single department
        if department_id is not None:
            department, _, err = zia.get_department(department_id)
            if err:
                raise Exception(f"Error retrieving department {department_id}: {err}")
            return department.as_dict()
        
        # Otherwise, list departments with optional filters
        query_params = {}
        if limit_search is not None:
            query_params["limit_search"] = limit_search
        if search is not None:
            query_params["search"] = search
        if page is not None:
            query_params["page"] = page
        if page_size is not None:
            if page_size <= 0:
                raise ValueError("page_size must be a positive integer")
            if page_size > 1000:
                raise ValueError("page_size cannot exceed 1000")
            query_params["page_size"] = page_size
        if sort_by is not None:
            query_params["sort_by"] = sort_by
        if sort_order is not None:
            query_params["sort_order"] = sort_order

        departments, _, err = zia.list_departments(query_params=query_params or None)
        if err:
            raise Exception(f"Error listing departments: {err}")
        return [d.as_dict() for d in departments]

    if action == "read_lite":
        if not department_id:
            raise ValueError("department_id is required for action 'read_lite'")
        department, _, err = zia.get_department_lite(department_id)
        if err:
            raise Exception(f"Error retrieving department (lite) {department_id}: {err}")
        return department.as_dict()

    raise ValueError(f"Unsupported action: {action}")
