from src.sdk.zscaler_client import get_zscaler_client
from src.utils.utils import convert_v2_to_sdk_format, convert_v1_to_v2_response

def forwarding_policy_manager(
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
    conditions: list = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> dict | list[dict] | str:
    """
    CRUD handler for ZPA Client Forwarding Policy Rules via the Python SDK.

    Required fields:
    - create: name, action_type
    - update: rule_id, at least one mutable field
    - delete: rule_id
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        use_legacy=use_legacy,
        service=service,
    )

    # Convert input conditions to SDK format
    try:
        processed_conditions = convert_v2_to_sdk_format(conditions)
    except Exception as e:
        raise ValueError(f"Invalid conditions format: {str(e)}")

    policy_type = "client_forwarding"
    api = client.zpa.policies

    if action == "create":
        if not all([name, action_type]):
            raise ValueError("'name' and 'action_type' are required for creating a client forwarding rule")

        payload = {
            "name": name,
            "description": description,
            "action": action_type,
            "conditions": processed_conditions,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        created, _, err = api.add_client_forwarding_rule_v2(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if rule_id:
            result, _, err = api.get_rule(policy_type, rule_id, query_params={"microtenantId": microtenant_id})
            if err:
                raise Exception(f"Read failed: {err}")
            rule_data = result.as_dict()
            # Convert response to standardized v2 format
            if "conditions" in rule_data:
                rule_data["conditions"] = convert_v1_to_v2_response(rule_data["conditions"])
            return rule_data
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
            raise ValueError("'rule_id' is required for updating a client forwarding rule")

        payload = {
            "name": name,
            "description": description,
            "action": action_type,
            "conditions": processed_conditions,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        updated, _, err = api.update_client_forwarding_rule_v2(rule_id, **payload)
        if err:
            raise Exception(f"Update failed: {err}")
        rule_data = updated.as_dict()
        if "conditions" in rule_data:
            rule_data["conditions"] = convert_v1_to_v2_response(rule_data["conditions"])
        return rule_data

    elif action == "delete":
        if not rule_id:
            raise ValueError("'rule_id' is required")

        _, _, err = api.delete_rule(policy_type, rule_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted access rule {rule_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
