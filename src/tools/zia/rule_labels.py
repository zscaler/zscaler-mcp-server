from src.sdk.zscaler_client import get_zscaler_client

def rule_label_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    username: str,
    password: str,
    api_key: str,
    label_id: int = None,
    name: str = None,
    description: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zia",
) -> dict | list[dict] | str:
    """
    Tool for managing ZIA Rule Labels via the Python SDK.

    Supported actions:
    - create: Requires name. Optionally accepts description.
    - read: List or get labels by ID.
    - update: Requires label_id and at least one field to update.
    - delete: Requires label_id.

    Args:
        action (str): One of 'create', 'read', 'update', 'delete'.
        label_id (int, optional): Required for read (by ID), update, and delete.
        name (str, optional): Label name.
        description (str, optional): Optional description.
        query_params (dict, optional): For filtering results in list.

    Returns:
        dict | list[dict] | str
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        username=username,
        password=password,
        api_key=api_key,
        use_legacy=use_legacy,
        service=service,
    )
    api = client.zia.rule_labels

    if action == "create":
        if not name:
            raise ValueError("Label name is required for creation.")
        payload = {"name": name}
        if description:
            payload["description"] = description

        created, _, err = api.add_label(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if label_id:
            result, _, err = api.get_label(label_id=label_id)
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            labels, _, err = api.list_labels(query_params=query_params or {})
            if err:
                raise Exception(f"List failed: {err}")
            return [label.as_dict() for label in labels]

    elif action == "update":
        if not label_id:
            raise ValueError("label_id is required for update.")
        update_fields = {}
        if name:
            update_fields["name"] = name
        if description:
            update_fields["description"] = description
        if not update_fields:
            raise ValueError("At least one field (name or description) must be provided for update.")

        updated, _, err = api.update_label(label_id=label_id, **update_fields)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not label_id:
            raise ValueError("label_id is required for deletion.")
        _, _, err = api.delete_label(label_id=label_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted rule label {label_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
