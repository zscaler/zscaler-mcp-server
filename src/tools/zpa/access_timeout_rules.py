from src.sdk.zscaler_client import get_zscaler_client

def timeout_policy_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    rule_id: str = None,
    microtenant_id: str = None,
    name: str = None,
    description: str = None,
    custom_msg: str = None,
    reauth_timeout: str = "172800",
    reauth_idle_timeout: str = "600",
    conditions: list = None,
    query_params: dict = None,
) -> dict | list[dict] | str:
    """
    CRUD handler for ZPA Timeout Policy Rules via the Python SDK.

    Required fields:
    - create: name
    - update: rule_id, at least one mutable field
    - delete: rule_id
    - list/get: policy_type is inferred as 'timeout'
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    policy_type = "timeout"
    api = client.zpa.policies

    if action == "create":
        if not name:
            raise ValueError("'name' is required for creating a timeout rule")

        payload = {
            "name": name,
            "description": description,
            "custom_msg": custom_msg,
            "reauth_timeout": reauth_timeout,
            "reauth_idle_timeout": reauth_idle_timeout,
            "conditions": conditions or [],
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        created, _, err = api.add_timeout_rule_v2(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if rule_id:
            result, _, err = api.get_rule(policy_type, rule_id, query_params={"microtenantId": microtenant_id})
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            query_params = query_params or {}
            if microtenant_id:
                query_params["microtenant_id"] = microtenant_id

            rules, _, err = api.list_rules(policy_type, query_params=query_params)
            if err:
                raise Exception(f"List failed: {err}")
            return [r.as_dict() for r in (rules or [])]

    elif action == "update":
        if not rule_id:
            raise ValueError("'rule_id' is required for updating a timeout rule")

        payload = {
            "name": name,
            "description": description,
            "custom_msg": custom_msg,
            "reauth_timeout": reauth_timeout,
            "reauth_idle_timeout": reauth_idle_timeout,
            "conditions": conditions or [],
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        updated, _, err = api.update_timeout_rule_v2(rule_id, **payload)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not rule_id:
            raise ValueError("'rule_id' is required for deleting a timeout rule")

        _, _, err = api.delete_rule(policy_type, rule_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted timeout rule {rule_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
