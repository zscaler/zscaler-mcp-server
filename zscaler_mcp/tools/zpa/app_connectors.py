from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zpa_list_app_connectors(
    search: Annotated[
        Optional[str], Field(description="Search term for filtering results by connector name.")
    ] = None,
    page: Annotated[Optional[str], Field(description="Page number for pagination.")] = None,
    page_size: Annotated[
        Optional[str], Field(description="Number of items per page. Default 20, max 500.")
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA app connectors with optional filtering and pagination. Returns connector status, version, group membership, and health information."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connectors

    qp = {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    if search:
        qp["search"] = search
    if page:
        qp["page"] = page
    if page_size:
        qp["page_size"] = page_size

    connectors, _, err = api.list_connectors(query_params=qp)
    if err:
        raise Exception(f"Failed to list app connectors: {err}")
    return [c.as_dict() for c in (connectors or [])]


def zpa_get_app_connector(
    connector_id: Annotated[str, Field(description="The unique ID of the ZPA app connector.")],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA app connector by ID. Returns detailed connector information including runtime status, version, control connection state, and associated connector group."""
    if not connector_id:
        raise ValueError("connector_id is required")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connectors

    qp = {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id

    connector, _, err = api.get_connector(connector_id, query_params=qp)
    if err:
        raise Exception(f"Failed to get app connector {connector_id}: {err}")
    return connector.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zpa_update_app_connector(
    connector_id: Annotated[str, Field(description="The unique ID of the ZPA app connector.")],
    name: Annotated[Optional[str], Field(description="Name of the app connector.")] = None,
    description: Annotated[
        Optional[str], Field(description="Description of the app connector.")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="Whether the app connector is enabled.")
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA app connector. Can be used to enable/disable a connector or change its name/description."""
    if not connector_id:
        raise ValueError("connector_id is required for update")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connectors

    body = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if enabled is not None:
        body["enabled"] = enabled
    if microtenant_id:
        body["microtenant_id"] = microtenant_id

    updated, _, err = api.update_connector(connector_id, **body)
    if err:
        raise Exception(f"Failed to update app connector {connector_id}: {err}")
    return updated.as_dict()


def zpa_delete_app_connector(
    connector_id: Annotated[
        str, Field(description="The unique ID of the ZPA app connector to delete.")
    ],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}",
) -> str:
    """Delete a ZPA app connector. This removes the connector from the ZPA cloud. The connector must be re-provisioned to reconnect."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation("zpa_delete_app_connector", confirmed, {})
    if confirmation_check:
        return confirmation_check

    if not connector_id:
        raise ValueError("connector_id is required for delete")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connectors

    _, _, err = api.delete_connector(connector_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete app connector {connector_id}: {err}")
    return f"Successfully deleted app connector {connector_id}"


def zpa_bulk_delete_app_connectors(
    connector_ids: Annotated[List[str], Field(description="List of app connector IDs to delete.")],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}",
) -> str:
    """Bulk delete multiple ZPA app connectors. This removes all specified connectors from the ZPA cloud."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation("zpa_bulk_delete_app_connectors", confirmed, {})
    if confirmation_check:
        return confirmation_check

    if not connector_ids:
        raise ValueError("connector_ids is required and must not be empty")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.app_connectors

    _, _, err = api.bulk_delete_connectors(connector_ids, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to bulk delete app connectors: {err}")
    return f"Successfully deleted {len(connector_ids)} app connectors"
