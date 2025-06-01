from src.sdk.zscaler_client import get_zscaler_client

def isolation_policy_manager(
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
    action_type: str = None,
    zpn_isolation_profile_id: str = None,
    conditions: list = None,
    rule_order: str = None,
    query_params: dict = None,
) -> dict | list[dict] | str:
    """
    CRUD handler for ZPA Isolation Policy Rules via the Python SDK.

    Required fields:
    - create: name, action_type, zpn_isolation_profile_id (if action_type == 'isolate')
    - update: rule_id, at least one mutable field
    - delete: rule_id
    - list/get: policy_type is inferred as 'isolation'
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    policy_type = "isolation"
    api = client.zpa.policies

    if action == "create":
        if not name or not action_type:
            raise ValueError("'name' and 'action_type' are required for creating an isolation rule")
        if action_type.lower() == "isolate" and not zpn_isolation_profile_id:
            raise ValueError("'zpn_isolation_profile_id' is required when action_type is 'isolate'")

        payload = {
            "name": name,
            "action": action_type,
            "zpn_isolation_profile_id": zpn_isolation_profile_id,
            "description": description,
            "rule_order": rule_order,
            "conditions": conditions,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        created, _, err = api.add_isolation_rule_v2(**payload)
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
            raise ValueError("'rule_id' is required for updating an isolation rule")

        payload = {
            "name": name,
            "action": action_type,
            "zpn_isolation_profile_id": zpn_isolation_profile_id,
            "description": description,
            "rule_order": rule_order,
            "conditions": conditions,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        updated, _, err = api.update_isolation_rule_v2(rule_id, **payload)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not rule_id:
            raise ValueError("'rule_id' is required for deleting an isolation rule")

        _, _, err = api.delete_rule(policy_type, rule_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted isolation rule {rule_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
