from zscaler_mcp.sdk.zscaler_client import get_zscaler_client
from zscaler_mcp import app
from typing import Union, List
from typing import Annotated
from pydantic import Field
from zscaler_mcp.utils.utils import convert_v2_to_sdk_format, convert_v1_to_v2_response


@app.tool(
    name="zpa_forwarding_policy",
    description="CRUD handler for ZPA Client Forwarding Policy Rules via the Python SDK.",
)
def forwarding_policy_manager(
    action: Annotated[
        str,
        Field(description="Action to perform: 'create', 'read', 'update', or 'delete'.")
    ],
    rule_id: Annotated[
        str,
        Field(description="Rule ID for read, update, or delete operations.")
    ] = None,
    microtenant_id: Annotated[
        str,
        Field(description="Microtenant ID for scoping operations.")
    ] = None,
    name: Annotated[
        str,
        Field(description="Name of the forwarding policy rule.")
    ] = None,
    description: Annotated[
        str,
        Field(description="Description of the forwarding policy rule.")
    ] = None,
    action_type: Annotated[
        str,
        Field(description="Action type for the policy rule.")
    ] = None,
    conditions: Annotated[
        List,
        Field(description="Conditions for the policy rule.")
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
    CRUD handler for ZPA Client Forwarding Policy Rules via the Python SDK.

    Required fields:
    - create: name, action_type
    - update: rule_id, at least one mutable field
    - delete: rule_id
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

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
