from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_rule_labels(
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List ZIA rule labels."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.rule_labels
    
    labels, _, err = api.list_labels(query_params=query_params or {})
    if err:
        raise Exception(f"List failed: {err}")
    return [label.as_dict() for label in labels]


def zia_get_rule_label(
    label_id: Annotated[int, Field(description="Label ID.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA rule label by ID."""
    if not label_id:
        raise ValueError("label_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.rule_labels
    
    result, _, err = api.get_label(label_id=label_id)
    if err:
        raise Exception(f"Read failed: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_rule_label(
    name: Annotated[str, Field(description="Label name (required).")],
    description: Annotated[Optional[str], Field(description="Optional description.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Create a new ZIA rule label."""
    if not name:
        raise ValueError("Label name is required for creation")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.rule_labels
    
    payload = {"name": name}
    if description:
        payload["description"] = description
    
    created, _, err = api.add_label(**payload)
    if err:
        raise Exception(f"Create failed: {err}")
    return created.as_dict()


def zia_update_rule_label(
    label_id: Annotated[int, Field(description="Label ID (required).")],
    name: Annotated[Optional[str], Field(description="Label name.")] = None,
    description: Annotated[Optional[str], Field(description="Optional description.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Update an existing ZIA rule label."""
    if not label_id:
        raise ValueError("label_id is required for update")
    
    update_fields = {}
    if name:
        update_fields["name"] = name
    if description:
        update_fields["description"] = description
    if not update_fields:
        raise ValueError("At least one field (name or description) must be provided for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.rule_labels
    
    updated, _, err = api.update_label(label_id=label_id, **update_fields)
    if err:
        raise Exception(f"Update failed: {err}")
    return updated.as_dict()


def zia_delete_rule_label(
    label_id: Annotated[int, Field(description="Label ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """Delete a ZIA rule label.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_rule_label",
        confirmed,
        {"label_id": label_id}
    )
    if confirmation_check:
        return confirmation_check
    
    if not label_id:
        raise ValueError("label_id is required for deletion")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.rule_labels
    
    _, _, err = api.delete_label(label_id=label_id)
    if err:
        raise Exception(f"Delete failed: {err}")
    return f"Deleted rule label {label_id}"
