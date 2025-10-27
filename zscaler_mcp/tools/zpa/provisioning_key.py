from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_provisioning_keys(
    key_type: Annotated[str, Field(description="Type of key: 'connector' or 'service_edge'.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA provisioning keys by type."""
    VALID_TYPES = {"connector", "service_edge"}
    if key_type not in VALID_TYPES:
        raise ValueError(f"Invalid key_type '{key_type}'. Must be 'connector' or 'service_edge'.")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.provisioning
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    results, _, err = api.list_provisioning_keys(key_type=key_type, query_params=qp)
    if err:
        raise Exception(f"Failed to list provisioning keys: {err}")
    return [r.as_dict() for r in results]


def zpa_get_provisioning_key(
    key_id: Annotated[str, Field(description="Provisioning key ID.")],
    key_type: Annotated[str, Field(description="Type of key: 'connector' or 'service_edge'.")],
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA provisioning key by ID and type."""
    VALID_TYPES = {"connector", "service_edge"}
    if key_type not in VALID_TYPES:
        raise ValueError(f"Invalid key_type '{key_type}'. Must be 'connector' or 'service_edge'.")
    if not key_id:
        raise ValueError("key_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.provisioning
    
    result, _, err = api.get_provisioning_key(key_id=key_id, key_type=key_type, query_params=query_params)
    if err:
        raise Exception(f"Failed to get provisioning key {key_id}: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_provisioning_key(
    name: Annotated[str, Field(description="Name of the provisioning key.")],
    key_type: Annotated[str, Field(description="Type of key: 'connector' or 'service_edge'.")],
    max_usage: Annotated[int, Field(description="Maximum usage count for the provisioning key.")],
    component_id: Annotated[str, Field(description="Component ID (App Connector Group or Service Edge Group).")],
    enrollment_cert_id: Annotated[Optional[str], Field(description="Enrollment certificate ID (required for 'connector' key_type).")] = None,
    description: Annotated[Optional[str], Field(description="Description of the provisioning key.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA provisioning key."""
    VALID_TYPES = {"connector", "service_edge"}
    if key_type not in VALID_TYPES:
        raise ValueError(f"Invalid key_type '{key_type}'. Must be 'connector' or 'service_edge'.")
    if not all([name, key_type, max_usage, component_id]):
        raise ValueError("name, key_type, max_usage, and component_id are required")
    if key_type == "connector" and not enrollment_cert_id:
        raise ValueError("enrollment_cert_id is required for 'connector' key_type")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.provisioning
    
    payload = {
        "name": name,
        "description": description,
        "max_usage": max_usage,
        "component_id": component_id,
        "enrollment_cert_id": enrollment_cert_id,
    }
    if microtenant_id:
        payload["microtenant_id"] = microtenant_id
    
    created, _, err = api.add_provisioning_key(key_type=key_type, **payload)
    if err:
        raise Exception(f"Failed to create provisioning key: {err}")
    return created.as_dict()


def zpa_update_provisioning_key(
    key_id: Annotated[str, Field(description="Provisioning key ID.")],
    key_type: Annotated[str, Field(description="Type of key: 'connector' or 'service_edge'.")],
    name: Annotated[Optional[str], Field(description="Name of the provisioning key.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the provisioning key.")] = None,
    max_usage: Annotated[Optional[int], Field(description="Maximum usage count for the provisioning key.")] = None,
    component_id: Annotated[Optional[str], Field(description="Component ID (App Connector Group or Service Edge Group).")] = None,
    enrollment_cert_id: Annotated[Optional[str], Field(description="Enrollment certificate ID.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA provisioning key."""
    VALID_TYPES = {"connector", "service_edge"}
    if key_type not in VALID_TYPES:
        raise ValueError(f"Invalid key_type '{key_type}'. Must be 'connector' or 'service_edge'.")
    if not key_id:
        raise ValueError("key_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.provisioning
    
    update_data = {
        "name": name,
        "description": description,
        "max_usage": max_usage,
        "component_id": component_id,
        "enrollment_cert_id": enrollment_cert_id,
    }
    if microtenant_id:
        update_data["microtenant_id"] = microtenant_id
    
    updated, _, err = api.update_provisioning_key(key_id=key_id, key_type=key_type, **update_data)
    if err:
        raise Exception(f"Failed to update provisioning key {key_id}: {err}")
    return updated.as_dict()


def zpa_delete_provisioning_key(
    key_id: Annotated[str, Field(description="Provisioning key ID.")],
    key_type: Annotated[str, Field(description="Type of key: 'connector' or 'service_edge'.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA provisioning key. If the associated component was already deleted, this will return a safe message."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_provisioning_key",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    VALID_TYPES = {"connector", "service_edge"}
    if key_type not in VALID_TYPES:
        raise ValueError(f"Invalid key_type '{key_type}'. Must be 'connector' or 'service_edge'.")
    if not key_id:
        raise ValueError("key_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.provisioning
    
    # Check if the key exists before attempting deletion
    result, _, err = api.get_provisioning_key(key_id=key_id, key_type=key_type, query_params=query_params)
    if err or not result:
        return (
            f"Provisioning key {key_id} does not exist or was already deleted "
            f"(possibly due to associated component deletion)."
        )
    
    _, _, err = api.delete_provisioning_key(key_id=key_id, key_type=key_type, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete provisioning key {key_id}: {err}")
    return f"Successfully deleted provisioning key {key_id}"
