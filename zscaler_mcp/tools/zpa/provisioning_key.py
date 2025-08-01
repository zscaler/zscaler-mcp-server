from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List
from pydantic import Field


def provisioning_key_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', or 'delete'."
        ),
    ],
    key_id: Annotated[
        str,
        Field(
            description="Provisioning key ID for read, update, or delete operations."
        ),
    ] = None,
    name: Annotated[str, Field(description="Name of the provisioning key.")] = None,
    key_type: Annotated[
        str, Field(description="Type of key: 'connector' or 'service_edge'.")
    ] = None,
    description: Annotated[
        str, Field(description="Description of the provisioning key.")
    ] = None,
    max_usage: Annotated[
        int, Field(description="Maximum usage count for the provisioning key.")
    ] = None,
    enrollment_cert_id: Annotated[
        str,
        Field(
            description="Enrollment certificate ID (required for 'connector' key_type)."
        ),
    ] = None,
    component_id: Annotated[
        str,
        Field(description="Component ID (App Connector Group or Service Edge Group)."),
    ] = None,
    microtenant_id: Annotated[
        str, Field(description="Microtenant ID for scoping operations.")
    ] = None,
    query_params: Annotated[
        dict, Field(description="Optional query parameters for filtering results.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing ZPA Provisioning Keys.

    Supported actions:
    - create: Requires name, key_type, max_usage, component_id, and enrollment_cert_id (for connectors).
    - read: List or get provisioning key(s); requires key_type for listing.
    - update: Requires key_id and key_type plus at least one mutable field.
    - delete: Requires key_id and key_type.

    Notes:
    - Valid key_type values: "connector" or "service_edge"
    - For 'connector', you must associate an enrollment certificate.
    - App Connector Groups and Service Edge Groups are required components.

    Deletion behavior:
    - If the associated App Connector Group or Service Edge Group is deleted first,
      the provisioning key will be automatically removed by ZPA backend.
    - In such cases, delete will fail with a "not found" error, which is safe to ignore.
    """
    VALID_TYPES = {"connector", "service_edge"}

    if action not in {"create", "read", "update", "delete"}:
        raise ValueError(f"Unsupported action: {action}")

    if action in {"read", "update", "delete"} and not key_type:
        raise ValueError(f"'key_type' is required for {action} operations")

    if key_type and key_type not in VALID_TYPES:
        raise ValueError(
            f"Invalid key_type '{key_type}'. Must be 'connector' or 'service_edge'."
        )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.provisioning

    if action == "create":
        if not all([name, key_type, max_usage, component_id]):
            raise ValueError("Missing required fields for provisioning key creation")

        if key_type == "connector" and not enrollment_cert_id:
            raise ValueError("enrollment_cert_id is required for 'connector' key_type")

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
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if key_id:
            result, _, err = api.get_provisioning_key(
                key_id=key_id, key_type=key_type, query_params=query_params
            )
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            query_params = query_params or {}
            if microtenant_id:
                query_params["microtenant_id"] = microtenant_id
            results, _, err = api.list_provisioning_keys(
                key_type=key_type, query_params=query_params
            )
            if err:
                raise Exception(f"List failed: {err}")
            return [r.as_dict() for r in results]

    elif action == "update":
        if not key_id:
            raise ValueError("key_id is required for update")

        update_data = {
            "name": name,
            "description": description,
            "max_usage": max_usage,
            "component_id": component_id,
            "enrollment_cert_id": enrollment_cert_id,
        }
        if microtenant_id:
            update_data["microtenant_id"] = microtenant_id

        updated, _, err = api.update_provisioning_key(
            key_id=key_id, key_type=key_type, **update_data
        )
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not key_id:
            raise ValueError("key_id is required for delete")

        result, _, err = api.get_provisioning_key(
            key_id=key_id, key_type=key_type, query_params=query_params
        )
        if err or not result:
            return (
                f"Provisioning key {key_id} does not exist or was already deleted "
                f"(possibly due to associated component deletion)."
            )

        _, _, err = api.delete_provisioning_key(
            key_id=key_id, key_type=key_type, microtenant_id=microtenant_id
        )
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted provisioning key {key_id}"
