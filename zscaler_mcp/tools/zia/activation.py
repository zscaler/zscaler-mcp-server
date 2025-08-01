from zscaler_mcp.client import get_zscaler_client
from typing import Annotated
from pydantic import Field


def zia_activation_manager(
    action: Annotated[
        str, Field(description="Action to perform: 'status' or 'activate'.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> str:
    """
    Tool to check or activate ZIA configuration changes.

    Supported actions:
    - status: Returns the current activation status.
    - activate: Activates changes only if the status is PENDING.

    Activation statuses:
    - ACTIVE: Configuration is already active.
    - PENDING: Configuration changes are pending and activation will be triggered.
    - INPROGRESS: Another activation is already in progress.
    """

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    config_api = client.zia.activate

    if action == "status":
        status_obj, _, err = config_api.status()
        if err:
            raise Exception(f"Failed to retrieve activation status: {err}")
        return f"Current activation status: {status_obj.status}"

    elif action == "activate":
        status_obj, _, err = config_api.status()
        if err:
            raise Exception(f"Failed to retrieve activation status: {err}")

        status = status_obj.status.upper()

        if status == "ACTIVE":
            return "Configuration is already active. No action needed."
        elif status == "INPROGRESS":
            return "An activation is already in progress. Please wait."
        elif status == "PENDING":
            result, _, err = config_api.activate()
            if err:
                raise Exception(f"Activation failed: {err}")
            return "Configuration activation has been triggered."
        else:
            return f"Unexpected status received: {status}"

    else:
        raise ValueError(f"Unsupported action: {action}")
