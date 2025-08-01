from zscaler_mcp.client import get_zscaler_client
from typing import Union, List
from typing import Annotated
from pydantic import Field
from zscaler_mcp.utils.utils import convert_v2_to_sdk_format, convert_v1_to_v2_response


def app_protection_policy_manager(
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
    name: Annotated[
        str, Field(description="Name of the inspection policy rule.")
    ] = None,
    description: Annotated[
        str, Field(description="Description of the inspection policy rule.")
    ] = None,
    action_type: Annotated[
        str, Field(description="Action type for the policy rule.")
    ] = None,
    zpn_inspection_profile_id: Annotated[
        str,
        Field(
            description="Inspection profile ID (required if action_type is 'inspect')."
        ),
    ] = None,
    conditions: Annotated[
        List, Field(description="Conditions for the policy rule.")
    ] = None,
    rule_order: Annotated[
        str, Field(description="Rule order for the inspection policy rule.")
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
    CRUD handler for ZPA Inspection Policy Rules via the Python SDK.

    IMPORTANT: The 'conditions' parameter must be in the exact v2 format expected by the SDK:
    - Use lists/tuples, NOT dictionaries
    - Follow the precise structure shown in examples below

    Conditions Format Rules:
    1. Basic conditions:
       ("object_type", ["value1", "value2"])
       Example: ("app", ["72058304855116918"])

    2. Conditions with operators:
       ("AND"/"OR", ("object_type", [("lhs", "rhs")]))
       Example: ("OR", ("posture", [("cfab2ee9...", "true")]))

    3. Special cases:
       - Multi-value:
            (("platform", [("windows", "true"), ("mac", "true")]))

    Full Examples:
    [
        # Simple app condition
        ("app", ["72058304855116918"]),

        # App group condition
        ("app_group", ["72058304855114308"]),

        # Operator group (OR)
        ("OR", ("posture", [
            ("cfab2ee9-9bf4-4482-9dcc-dadf7311c49b", "true"),
            ("72ddbe89-fa08-4071-94bd-964ce264db10", "true")
        ])),

        # Multi-value condition
        (("platform", [
            ("windows", "true"),
            ("mac", "true")
        ])),

        # SCIM_GROUP/SCIM/SAML conditions
        ("AND", ("scim_group", [
            ("72058304855015574", "490880"),
            ("72058304855015574", "490877")
        ]))
    ]

    Note: When sending via JSON, use lists [] instead of tuples ().
    Example JSON-compatible format:
    {
        "conditions": [
            ["app", ["72058304855116918"]],
            ["AND", ["posture", [["cfab2ee9...", "true"]]]]
        ]
    }
    Responses will always be returned in a standardized v2 format that maintains
    the original operator grouping from the API.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    try:
        processed_conditions = convert_v2_to_sdk_format(conditions)
    except Exception as e:
        raise ValueError(f"Invalid conditions format: {str(e)}")

    policy_type = "inspection"
    api = client.zpa.policies

    if action == "create":
        if not name or not action_type:
            raise ValueError(
                "'name' and 'action_type' are required for creating an inspection rule"
            )
        if action_type.lower() == "inspect" and not zpn_inspection_profile_id:
            raise ValueError(
                "'zpn_inspection_profile_id' is required when action_type is 'isolate'"
            )

        payload = {
            "name": name,
            "action": action_type,
            "zpn_inspection_profile_id": zpn_inspection_profile_id,
            "description": description,
            "rule_order": rule_order,
            "conditions": processed_conditions,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        created, _, err = api.add_app_protection_rule_v2(**payload)
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
            raise ValueError("'rule_id' is required for updating an inspection rule")

        payload = {
            "name": name,
            "action": action_type,
            "zpn_inspection_profile_id": zpn_inspection_profile_id,
            "description": description,
            "rule_order": rule_order,
            "conditions": processed_conditions,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        updated, _, err = api.update_app_protection_rule_v2(rule_id, **payload)
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
