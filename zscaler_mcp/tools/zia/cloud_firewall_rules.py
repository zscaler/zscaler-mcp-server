from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List, Optional, Literal
from pydantic import Field
import json


def zia_firewall_rule_manager(
    action: Annotated[
        Literal["list", "get", "add", "update", "delete"],
        Field(
            description="Firewall rule operation: list, get, add, update, or delete."
        ),
    ] = "list",
    rule_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Required for get, update, and delete."),
    ] = None,
    name: Annotated[
        Optional[str], Field(description="Rule name (required for add/update).")
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    action_type: Annotated[
        Optional[str], Field(description="Action for rule (e.g., ALLOW, BLOCK).")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable.")
    ] = True,
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules.")
    ] = None,
    params: Annotated[
        Optional[Union[str, dict]],
        Field(description="Additional JSON-encoded parameters for add/update."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict], str]:
    """
    Manages ZIA Cloud Firewall Rules.

    Returns:
        dict | list[dict] | str
    """
    # Normalize dynamic parameters
    extra = {}
    if params:
        if isinstance(params, str):
            try:
                extra = json.loads(params)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for params: {e}")
        elif isinstance(params, dict):
            extra = params

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    fw = client.zia.cloud_firewall_rules

    if action == "list":
        query = {"search": search} if search else {}
        rules, _, err = fw.list_rules(query_params=query)
        if err:
            raise Exception(f"Failed to list firewall rules: {err}")
        return [r.as_dict() for r in rules]

    if action == "get":
        if not rule_id:
            raise ValueError("rule_id is required for get.")
        rule, _, err = fw.get_rule(rule_id)
        if err:
            raise Exception(f"Failed to retrieve rule {rule_id}: {err}")
        return rule.as_dict()

    if action == "add":
        if not name or not action_type:
            raise ValueError("name and action_type are required for add.")
        payload = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "action": action_type,
            **extra,
        }
        rule, _, err = fw.add_rule(**payload)
        if err:
            raise Exception(f"Failed to add firewall rule: {err}")
        return rule.as_dict()

    if action == "update":
        if not rule_id or not name or not action_type:
            raise ValueError("rule_id, name, and action_type are required for update.")
        payload = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "action": action_type,
            **extra,
        }
        rule, _, err = fw.update_rule(rule_id, **payload)
        if err:
            raise Exception(f"Failed to update rule {rule_id}: {err}")
        return rule.as_dict()

    if action == "delete":
        if not rule_id:
            raise ValueError("rule_id is required for delete.")
        _, _, err = fw.delete_rule(rule_id)
        if err:
            raise Exception(f"Failed to delete rule {rule_id}: {err}")
        return f"Firewall rule {rule_id} deleted successfully."

    raise ValueError(f"Unsupported action: {action}")
