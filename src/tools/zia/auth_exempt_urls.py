from typing import Optional, Union, Literal, Annotated
import json
from sdk.zscaler_client import get_zscaler_client


def zia_auth_exempt_urls_manager(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    action: Annotated[
        Literal["get", "add", "delete"],
        "One of: get, add, delete. Defaults to get.",
    ] = "get",
    exempt_urls: Annotated[
        Optional[Union[list[str], str]],
        "Required for 'add' or 'delete'. List of exempt URLs (as list or JSON string).",
    ] = None,
) -> Union[list[str], str]:
    """
    Manages the list of cookie authentication exempt URLs in ZIA.

    Supported actions:
    - "get":    Retrieves the current exemption list.
    - "add":    Adds one or more URLs to the exempt list.
    - "delete": Removes one or more URLs from the exempt list.

    Args:
        cloud (str): Zscaler cloud environment (e.g., 'beta').
        client_id (str): OAuth2 client ID.
        client_secret (str): OAuth2 client secret.
        customer_id (str): Zscaler tenant customer ID.
        vanity_domain (str): Vanity domain associated with the tenant.
        action (str, optional): One of "get", "add", or "delete". Defaults to "get".
        exempt_urls (list[str] or str, optional): Required for "add" and "delete" actions.
            Can be either a Python list or a JSON string representation of a list.

    Returns:
        list[str]: Updated list of exempted URLs.

    Raises:
        ValueError: If action is "add" or "delete" and no exempt_urls are provided,
                   or if the input cannot be parsed as a list of URLs.
    """
    # Convert string input to list if necessary
    processed_urls = None
    if exempt_urls is not None:
        if isinstance(exempt_urls, str):
            try:
                processed_urls = json.loads(exempt_urls)
                if not isinstance(processed_urls, list):
                    raise ValueError("exempt_urls must be a list or JSON array string")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string for exempt_urls: {e}")
        else:
            processed_urls = exempt_urls

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    if action == "get":
        url_list, _, err = client.zia.authentication_settings.get_exempted_urls()
        if err:
            raise Exception(f"Exempt URL list retrieval failed: {err}")
        # 🟢 Ensure we always return a plain list
        return url_list or []

    elif action == "add":
        if not processed_urls:
            raise ValueError("You must provide a list of exempt URLs to add.")
        url_list, _, err = client.zia.authentication_settings.add_urls_to_exempt_list(processed_urls)
    elif action == "delete":
        if not processed_urls:
            raise ValueError("You must provide a list of exempt URLs to delete.")
        url_list, _, err = client.zia.authentication_settings.delete_urls_from_exempt_list(processed_urls)
    else:
        raise ValueError("Invalid action. Must be one of: 'get', 'add', 'delete'.")

    if err:
        raise Exception(f"Exempt URL list operation failed: {err}")

    return getattr(url_list, "urls", url_list or [])
