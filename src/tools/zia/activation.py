from src.sdk.zscaler_client import get_zscaler_client

def zia_activation_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    username: str,
    password: str,
    api_key: str,
    use_legacy: bool = False,
    service: str = "zia",
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
