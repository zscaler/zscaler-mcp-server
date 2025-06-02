from sdk.zscaler_client import get_zscaler_client
from typing import Union

def zcc_devices_manager(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    username: str = None,
    os_type: str = None,
    page: int = None,
    page_size: int = None,
) -> Union[list[dict], str]:
    """
    Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal.

    Filters:
    - username (optional): Filter devices by enrolled username (e.g., 'jdoe@acme.com').
    - os_type (optional): Device operating system type. Valid options:
        - ios
        - android
        - windows
        - macos
        - linux
    - page (optional): Page number for paginated results.
    - page_size (optional): Number of results per page. Default is 50. Max is 5000.

    Args:
        cloud (str): Zscaler cloud environment (e.g., 'beta').
        client_id (str): OAuth2 client ID.
        client_secret (str): OAuth2 client secret.
        customer_id (str): Zscaler tenant customer ID.
        vanity_domain (str): Vanity domain associated with the tenant.
        username (str, optional): Username to filter by.
        os_type (str, optional): OS type to filter by.
        page (int, optional): Page number.
        page_size (int, optional): Number of entries per page.

    Returns:
        list[dict]: List of ZCC device records.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    query_params = {}
    if username:
        query_params["username"] = username
    if os_type:
        query_params["os_type"] = os_type
    if page:
        query_params["page"] = page
    if page_size:
        query_params["page_size"] = page_size

    devices, _, err = client.zcc.devices.list_devices(query_params=query_params)
    if err:
        raise Exception(f"Error listing ZCC devices: {err}")
    return [d.as_dict() for d in devices]
