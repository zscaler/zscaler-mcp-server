from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_pra_credentials(
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA PRA (Privileged Remote Access) credentials."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_credential
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    results, _, err = api.list_credentials(query_params=qp)
    if err:
        raise Exception(f"Failed to list PRA credentials: {err}")
    return [r.as_dict() for r in results]


def zpa_get_pra_credential(
    credential_id: Annotated[str, Field(description="Credential ID for the PRA credential.")],
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA PRA credential by ID."""
    if not credential_id:
        raise ValueError("credential_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_credential
    
    result, _, err = api.get_credential(credential_id, query_params=query_params)
    if err:
        raise Exception(f"Failed to get PRA credential {credential_id}: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_pra_credential(
    name: Annotated[str, Field(description="Name of the PRA credential.")],
    credential_type: Annotated[str, Field(description="Type of credential: 'USERNAME_PASSWORD', 'PASSWORD', or 'SSH_KEY'.")],
    username: Annotated[Optional[str], Field(description="Username for USERNAME_PASSWORD or SSH_KEY credentials.")] = None,
    password: Annotated[Optional[str], Field(description="Password for USERNAME_PASSWORD or PASSWORD credentials.")] = None,
    private_key: Annotated[Optional[str], Field(description="Private key for SSH_KEY credentials.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the PRA credential.")] = None,
    user_domain: Annotated[Optional[str], Field(description="User domain for the credential.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA PRA credential."""
    if not name or not credential_type:
        raise ValueError("Both 'name' and 'credential_type' are required for creation")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_credential
    
    body = {
        "name": name,
        "description": description,
        "credential_type": credential_type,
        "user_domain": user_domain,
        "microtenant_id": microtenant_id,
    }
    
    if credential_type == "USERNAME_PASSWORD":
        if not username or not password:
            raise ValueError("USERNAME_PASSWORD requires 'username' and 'password'")
        body.update({"user_name": username, "password": password})
    elif credential_type == "PASSWORD":
        if not password:
            raise ValueError("PASSWORD type requires 'password'")
        body.update({"password": password})
    elif credential_type == "SSH_KEY":
        if not username or not private_key:
            raise ValueError("SSH_KEY requires 'username' and 'private_key'")
        body.update({"user_name": username, "private_key": private_key})
    else:
        raise ValueError(f"Invalid credential_type: {credential_type}")
    
    created, _, err = api.add_credential(**body)
    if err:
        raise Exception(f"Failed to create PRA credential: {err}")
    return created.as_dict()


def zpa_update_pra_credential(
    credential_id: Annotated[str, Field(description="Credential ID for the PRA credential.")],
    credential_type: Annotated[str, Field(description="Type of credential: 'USERNAME_PASSWORD', 'PASSWORD', or 'SSH_KEY'.")],
    name: Annotated[Optional[str], Field(description="Name of the PRA credential.")] = None,
    username: Annotated[Optional[str], Field(description="Username for USERNAME_PASSWORD or SSH_KEY credentials.")] = None,
    password: Annotated[Optional[str], Field(description="Password for USERNAME_PASSWORD or PASSWORD credentials.")] = None,
    private_key: Annotated[Optional[str], Field(description="Private key for SSH_KEY credentials.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the PRA credential.")] = None,
    user_domain: Annotated[Optional[str], Field(description="User domain for the credential.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA PRA credential. Note: credential type cannot be changed."""
    if not credential_id:
        raise ValueError("credential_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_credential
    
    # Verify the credential type matches
    existing, _, err = api.get_credential(credential_id, query_params=query_params)
    if err:
        raise Exception(f"Failed to fetch existing credential: {err}")
    if existing.credential_type != credential_type:
        raise ValueError(
            "Cannot change credential_type. Delete and recreate the credential instead."
        )
    
    body = {
        "name": name,
        "description": description,
        "credential_type": credential_type,
        "user_domain": user_domain,
        "microtenant_id": microtenant_id,
    }
    
    if credential_type == "USERNAME_PASSWORD":
        if not username or not password:
            raise ValueError("USERNAME_PASSWORD requires 'username' and 'password'")
        body.update({"user_name": username, "password": password})
    elif credential_type == "PASSWORD":
        if not password:
            raise ValueError("PASSWORD type requires 'password'")
        body.update({"password": password})
    elif credential_type == "SSH_KEY":
        if not username or not private_key:
            raise ValueError("SSH_KEY requires 'username' and 'private_key'")
        body.update({"user_name": username, "private_key": private_key})
    else:
        raise ValueError(f"Invalid credential_type: {credential_type}")
    
    updated, _, err = api.update_credential(credential_id, **body)
    if err:
        raise Exception(f"Failed to update PRA credential {credential_id}: {err}")
    return updated.as_dict()


def zpa_delete_pra_credential(
    credential_id: Annotated[str, Field(description="Credential ID for the PRA credential.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA PRA credential."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_pra_credential",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not credential_id:
        raise ValueError("credential_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_credential
    
    _, _, err = api.delete_credential(credential_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete PRA credential {credential_id}: {err}")
    return f"Successfully deleted PRA credential {credential_id}"
