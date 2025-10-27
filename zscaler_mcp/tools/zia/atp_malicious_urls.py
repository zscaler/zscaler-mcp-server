import json
from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_atp_malicious_urls(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[str]:
    """Retrieve the current malicious URL denylist from ZIA Advanced Threat Protection (ATP) policy."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    
    url_list, _, err = client.zia.atp_policy.get_atp_malicious_urls()
    if err:
        raise Exception(f"ATP URL list retrieval failed: {err}")
    return getattr(url_list, "malicious_urls", url_list or [])


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_add_atp_malicious_urls(
    malicious_urls: Annotated[Union[List[str], str], Field(description="List of malicious URLs to add to denylist. Accepts list or JSON string.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[str]:
    """Add URLs to the malicious URL denylist in ZIA ATP policy."""
    # Convert string input to list if necessary
    processed_urls = malicious_urls
    if isinstance(malicious_urls, str):
        try:
            processed_urls = json.loads(malicious_urls)
            if not isinstance(processed_urls, list):
                raise ValueError("malicious_urls must be a list or JSON array string")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for malicious_urls: {e}")
    
    if not processed_urls:
        raise ValueError("You must provide a list of malicious URLs to add")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    
    url_list, _, err = client.zia.atp_policy.add_atp_malicious_urls(processed_urls)
    if err:
        raise Exception(f"Failed to add malicious URLs: {err}")
    return getattr(url_list, "malicious_urls", url_list or [])


def zia_delete_atp_malicious_urls(
    malicious_urls: Annotated[Union[List[str], str], Field(description="List of malicious URLs to remove from denylist. Accepts list or JSON string.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> Union[str, List[str]]:
    """Remove URLs from the malicious URL denylist in ZIA ATP policy.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_atp_malicious_urls",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    # Convert string input to list if necessary
    processed_urls = malicious_urls
    if isinstance(malicious_urls, str):
        try:
            processed_urls = json.loads(malicious_urls)
            if not isinstance(processed_urls, list):
                raise ValueError("malicious_urls must be a list or JSON array string")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for malicious_urls: {e}")
    
    if not processed_urls:
        raise ValueError("You must provide a list of malicious URLs to delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    
    url_list, _, err = client.zia.atp_policy.delete_atp_malicious_urls(processed_urls)
    if err:
        raise Exception(f"Failed to delete malicious URLs: {err}")
    return getattr(url_list, "malicious_urls", url_list or [])
