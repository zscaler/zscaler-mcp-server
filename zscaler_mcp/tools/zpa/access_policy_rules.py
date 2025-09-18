from typing import Annotated, Any, Dict, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.utils.utils import convert_v1_to_v2_response, convert_v2_to_sdk_format


def access_policy_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', or 'delete'."
        ),
    ],
    rule_id: Annotated[
        str, Field(description="Rule ID for read, update, or delete operations.")
    ] = None,
    microtenant_id: Annotated[
        str, Field(description="Microtenant ID for scoping operations.")
    ] = None,
    name: Annotated[str, Field(description="Name of the access policy rule.")] = None,
    description: Annotated[
        str, Field(description="Description of the access policy rule.")
    ] = None,
    action_type: Annotated[
        str, Field(description="Action type for the policy rule.")
    ] = None,
    app_connector_group_ids: Annotated[
        List[str], Field(description="List of app connector group IDs.")
    ] = None,
    app_server_group_ids: Annotated[
        List[str], Field(description="List of app server group IDs.")
    ] = None,
    conditions: Annotated[
        Any, Field(description="Conditions for the policy rule in v2 format.")
    ] = None,
    query_params: Annotated[
        Dict[str, Any],
        Field(description="Optional query parameters for filtering results."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[Dict[str, Any], List[Dict[str, Any]], str]:
    """
    CRUD handler for ZPA Access Policy Rules via the Python SDK.

    IMPORTANT: The 'conditions' parameter must be in the exact v2 format expected by the SDK:
    - Use lists/tuples, NOT dictionaries
    - Follow the precise structure shown in examples below

    Conditions Format Rules:

    1. Basic conditions:
       ("object_type", ["value1", "value2"])

    2. Conditions with operators:
       ("AND"/"OR", ("object_type", [("lhs", "rhs")]))

    3. Special cases:
       - Chrome: ("chrome_enterprise", "attribute", value)
       - Multi-value: (("platform", [("windows", "true"), ("mac", "true")]))

    Note: When sending via JSON, use lists [] instead of tuples ().

    Responses will always be returned in a standardized v2 format that maintains
    the original operator grouping from the API.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    # Convert input conditions to SDK format
    try:
        processed_conditions = convert_v2_to_sdk_format(conditions)
    except Exception as e:
        raise ValueError(f"Invalid conditions format: {str(e)}")

    policy_type = "access"
    api = client.zpa.policies

    if action == "create":
        if not all([name, action]):
            raise ValueError("'name' and 'action_type' are required")

        payload = {
            "name": name,
            "description": description,
            "action": action_type,
            "conditions": processed_conditions,
            "app_connector_group_ids": app_connector_group_ids or [],
            "app_server_group_ids": app_server_group_ids or [],
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        created, _, err = api.add_access_rule_v2(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if rule_id:
            result, _, err = api.get_rule(
                policy_type, rule_id, query_params={"microtenantId": microtenant_id}
            )
            if err:
                raise Exception(f"Read failed: {err}")
            rule_data = result.as_dict()
            # Convert response to standardized v2 format
            if "conditions" in rule_data:
                rule_data["conditions"] = convert_v1_to_v2_response(
                    rule_data["conditions"]
                )
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
            raise ValueError("'rule_id' is required")

        payload = {
            "name": name,
            "description": description,
            "action": action_type,
            "conditions": processed_conditions,
            "app_connector_group_ids": app_connector_group_ids or [],
            "app_server_group_ids": app_server_group_ids or [],
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        updated, _, err = api.update_access_rule_v2(rule_id, **payload)
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
