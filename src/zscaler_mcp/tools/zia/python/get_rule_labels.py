from zscaler_mcp.sdk.python.zscaler_client import get_zscaler_client

def get_rule_labels(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str
) -> list[str]:
    """
    Retrieves the names of all ZIA Rule Labels using the Python SDK.

    Args:
        cloud (str): The Zscaler cloud environment (e.g., "production").
        client_id (str): OAuth Client ID for authentication.
        client_secret (str): OAuth Client Secret for authentication.
        customer_id (str): The customer ID for your Zscaler tenant.
        vanity_domain (str): The vanity domain associated with your Zscaler tenant.

    Returns:
        list[str]: A list containing the names of all application segments.
    """
    client = get_zscaler_client(
        client_id=client_id,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        client_secret=client_secret,
        cloud=cloud,
    )

    labels_list, _, err = client.zia.rule_labels.list_labels()

    if err:
        raise Exception(f"Error fetching rule labels: {err}")

    # Extract segment names explicitly from SDK objects
    return [label.name for label in labels_list]
