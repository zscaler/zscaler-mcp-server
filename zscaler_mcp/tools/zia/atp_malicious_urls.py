import json
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_atp_malicious_urls_manager(
    action: Annotated[
        Literal["read", "add", "delete"],
        Field(description="One of: read, add, delete. Defaults to read."),
    ] = "read",
    malicious_urls: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description="Required for 'add' or 'delete'. List of malicious URLs (as list or JSON string)."
        ),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[List[str], str]:
    """
    Manages the malicious URL denylist in the ZIA Advanced Threat Protection (ATP) policy.

    Supported actions:
    - "read":   Retrieves the current malicious URLs denylist.
    - "add":    Adds one or more URLs to the denylist.
    - "delete": Removes one or more URLs from the denylist.

    Args:
        action (str, optional): One of "read", "add", or "delete". Defaults to "read".
        malicious_urls (list[str] or str, optional): Required for "add" and "delete" actions.
            Can be either a Python list or a JSON string representation of a list.

    Returns:
        list[str]: Updated malicious URL list after the requested operation.

    Raises:
        ValueError: If action is "add" or "delete" and no malicious_urls are provided,
                   or if the input cannot be parsed as a list of URLs.
    """
    # Convert string input to list if necessary
    processed_urls = None
    if malicious_urls is not None:
        if isinstance(malicious_urls, str):
            try:
                processed_urls = json.loads(malicious_urls)
                if not isinstance(processed_urls, list):
                    raise ValueError(
                        "malicious_urls must be a list or JSON array string"
                    )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string for malicious_urls: {e}")
        else:
            processed_urls = malicious_urls

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    if action == "read":
        url_list, _, err = client.zia.atp_policy.get_atp_malicious_urls()
    elif action == "add":
        if not processed_urls:
            raise ValueError("You must provide a list of malicious URLs to add.")
        url_list, _, err = client.zia.atp_policy.add_atp_malicious_urls(processed_urls)
    elif action == "delete":
        if not processed_urls:
            raise ValueError("You must provide a list of malicious URLs to delete.")
        url_list, _, err = client.zia.atp_policy.delete_atp_malicious_urls(
            processed_urls
        )
    else:
        raise ValueError("Invalid action. Must be one of: 'read', 'add', 'delete'.")

    if err:
        raise Exception(f"ATP URL list operation failed: {err}")

    return getattr(url_list, "malicious_urls", url_list or [])
