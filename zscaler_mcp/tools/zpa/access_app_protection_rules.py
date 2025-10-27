from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.utils.utils import convert_v1_to_v2_response, convert_v2_to_sdk_format

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_app_protection_rules(
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA inspection policy rules (app protection)."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.policies
    policy_type = "inspection"
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    rules, _, err = api.list_rules(policy_type, query_params=qp)
    if err:
        raise Exception(f"Failed to list app protection rules: {err}")
    return [r.as_dict() for r in (rules or [])]


def zpa_get_app_protection_rule(
    rule_id: Annotated[str, Field(description="Rule ID for the app protection rule.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA inspection policy rule (app protection) by ID."""
    if not rule_id:
        raise ValueError("rule_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.policies
    policy_type = "inspection"
    
    result, _, err = api.get_rule(policy_type, rule_id, query_params={"microtenantId": microtenant_id})
    if err:
        raise Exception(f"Failed to get app protection rule {rule_id}: {err}")
    
    rule_data = result.as_dict()
    # Convert response to standardized v2 format
    if "conditions" in rule_data:
        rule_data["conditions"] = convert_v1_to_v2_response(rule_data["conditions"])
    return rule_data


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_app_protection_rule(
    name: Annotated[str, Field(description="Name of the inspection policy rule.")],
    action_type: Annotated[str, Field(description="Action type for the policy rule.")],
    zpn_inspection_profile_id: Annotated[Optional[str], Field(description="Inspection profile ID (required if action_type is 'inspect').")] = None,
    description: Annotated[Optional[str], Field(description="Description of the inspection policy rule.")] = None,
    rule_order: Annotated[Optional[str], Field(description="Rule order for the inspection policy rule.")] = None,
    conditions: Annotated[Optional[List], Field(description="Conditions for the policy rule.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA inspection policy rule (app protection)."""
    if not name or not action_type:
        raise ValueError("'name' and 'action_type' are required for creating an inspection rule")
    if action_type.lower() == "inspect" and not zpn_inspection_profile_id:
        raise ValueError("'zpn_inspection_profile_id' is required when action_type is 'inspect'")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.policies
    
    try:
        processed_conditions = convert_v2_to_sdk_format(conditions)
    except Exception as e:
        raise ValueError(f"Invalid conditions format: {str(e)}")
    
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
        raise Exception(f"Failed to create app protection rule: {err}")
    return created.as_dict()


def zpa_update_app_protection_rule(
    rule_id: Annotated[str, Field(description="Rule ID for the app protection rule.")],
    name: Annotated[Optional[str], Field(description="Name of the inspection policy rule.")] = None,
    action_type: Annotated[Optional[str], Field(description="Action type for the policy rule.")] = None,
    zpn_inspection_profile_id: Annotated[Optional[str], Field(description="Inspection profile ID.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the inspection policy rule.")] = None,
    rule_order: Annotated[Optional[str], Field(description="Rule order for the inspection policy rule.")] = None,
    conditions: Annotated[Optional[List], Field(description="Conditions for the policy rule.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA inspection policy rule (app protection)."""
    if not rule_id:
        raise ValueError("'rule_id' is required for updating an inspection rule")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.policies
    
    try:
        processed_conditions = convert_v2_to_sdk_format(conditions)
    except Exception as e:
        raise ValueError(f"Invalid conditions format: {str(e)}")
    
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
        raise Exception(f"Failed to update app protection rule {rule_id}: {err}")
    
    rule_data = updated.as_dict()
    if "conditions" in rule_data:
        rule_data["conditions"] = convert_v1_to_v2_response(rule_data["conditions"])
    return rule_data


def zpa_delete_app_protection_rule(
    rule_id: Annotated[str, Field(description="Rule ID for the app protection rule.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA inspection policy rule (app protection)."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_app_protection_rule",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not rule_id:
        raise ValueError("'rule_id' is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.policies
    policy_type = "inspection"
    
    _, _, err = api.delete_rule(policy_type, rule_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete app protection rule {rule_id}: {err}")
    return f"Successfully deleted app protection rule {rule_id}"
