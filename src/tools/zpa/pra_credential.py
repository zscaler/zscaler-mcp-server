from src.sdk.zscaler_client import get_zscaler_client
from typing import Union


def pra_credential_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    credential_id: str = None,
    name: str = None,
    description: str = None,
    credential_type: str = None,
    user_domain: str = None,
    username: str = None,
    password: str = None,
    private_key: str = None,
    microtenant_id: str = None,
    query_params: dict = None,
) -> Union[dict, list[dict], str]:
    """
    Tool for managing ZPA PRA Credentials.

    Supported actions:
    - create: Requires name and credential_type, with additional fields depending on the type.
    - read: List or get credential(s).
    - update: Requires credential_id and valid fields. Credential type cannot be changed.
    - delete: Requires credential_id.

    Update behavior:
    - A pra credential type cannot be updated.
    - If credential type update is requested, we must delete and re-create the credential.
    """

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

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
