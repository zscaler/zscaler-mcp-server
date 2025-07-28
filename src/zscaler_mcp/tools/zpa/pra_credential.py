from zscaler_mcp.sdk.zscaler_client import get_zscaler_client
from zscaler_mcp import app
from typing import Annotated, Union, List
from pydantic import Field


@app.tool(
    name="zpa_pra_credentials",
    description="Tool for managing ZPA Privileged Remote Access (PRA) Credentials.",
)
def pra_credential_manager(
    action: Annotated[
        str,
        Field(description="Action to perform: 'create', 'read', 'update', or 'delete'.")
    ],
    credential_id: Annotated[
        str,
        Field(description="Credential ID for read, update, or delete operations.")
    ] = None,
    name: Annotated[
        str,
        Field(description="Name of the PRA credential.")
    ] = None,
    description: Annotated[
        str,
        Field(description="Description of the PRA credential.")
    ] = None,
    credential_type: Annotated[
        str,
        Field(description="Type of credential: 'USERNAME_PASSWORD', 'PASSWORD', or 'SSH_KEY'.")
    ] = None,
    user_domain: Annotated[
        str,
        Field(description="User domain for the credential.")
    ] = None,
    username: Annotated[
        str,
        Field(description="Username for USERNAME_PASSWORD or SSH_KEY credentials.")
    ] = None,
    password: Annotated[
        str,
        Field(description="Password for USERNAME_PASSWORD or PASSWORD credentials.")
    ] = None,
    private_key: Annotated[
        str,
        Field(description="Private key for SSH_KEY credentials.")
    ] = None,
    microtenant_id: Annotated[
        str,
        Field(description="Microtenant ID for scoping operations.")
    ] = None,
    query_params: Annotated[
        dict,
        Field(description="Optional query parameters for filtering results.")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zpa",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing ZPA Privileged Remote Access (PRA) Credentials.

    Supported actions:
    - create: Requires name and credential_type, with additional fields depending on the type.
    - read: List or get credential(s).
    - update: Requires credential_id and valid fields. Credential type cannot be changed.
    - delete: Requires credential_id.

    Update behavior:
    - A pra credential type cannot be updated.
    - If credential type update is requested, we must delete and re-create the credential.
    """

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    api = client.zpa.pra_credential

    if action == "create":
        if not name or not credential_type:
            raise ValueError("Both 'name' and 'credential_type' are required for creation")

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
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if credential_id:
            result, _, err = api.get_credential(credential_id, query_params=query_params)
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            qp = query_params or {}
            if microtenant_id:
                qp["microtenant_id"] = microtenant_id
            results, _, err = api.list_credentials(query_params=qp)
            if err:
                raise Exception(f"List failed: {err}")
            return [r.as_dict() for r in results]

    elif action == "update":
        if not credential_id:
            raise ValueError("credential_id is required for update")

        existing, _, err = api.get_credential(credential_id, query_params=query_params)
        if err:
            raise Exception(f"Failed to fetch existing credential: {err}")
        if existing.credential_type != credential_type:
            raise ValueError("Cannot change credential_type. Delete and recreate the credential instead.")

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
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not credential_id:
            raise ValueError("credential_id is required for delete")
        _, _, err = api.delete_credential(credential_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted credential {credential_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
