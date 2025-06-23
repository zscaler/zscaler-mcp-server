from sdk.zscaler_client import get_zscaler_client
from typing import Optional
from datetime import datetime


def zcc_devices_csv_exporter(
    dataset: str = "devices",
    os_type: Optional[str] = None,
    registration_type: Optional[str] = None,
    filename: Optional[str] = None,
    use_legacy: bool = False,
    service: str = "zcc",
) -> str:
    """
    Downloads ZCC device information or service status as a CSV file.

    Filters:
    - dataset (required): Type of report to download. Valid values:
        - devices
        - service_status
    - os_type (optional): Filter by OS type. Valid values:
        - ios, android, windows, macos, linux
    - registration_type (optional): Filter by registration status. Valid values:
        - all, registered, unregistered, removal_pending, removed, quarantined
    - filename (optional): Custom filename for the CSV. Defaults to timestamped file.

    Args:
        cloud (str): Zscaler cloud environment (e.g., 'beta').
        client_id (str): OAuth2 client ID.
        client_secret (str): OAuth2 client secret.
        customer_id (str): Zscaler tenant customer ID.
        vanity_domain (str): Vanity domain associated with the tenant.
        dataset (str, optional): One of 'devices' or 'service_status'.
        os_type (str, optional): OS filter for report.
        registration_type (str, optional): Registration filter.
        filename (str, optional): Custom output filename.

    Returns:
        str: Absolute path to the downloaded CSV file.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if os_type:
        query_params["os_types"] = [os_type]
    if registration_type:
        query_params["registration_types"] = [registration_type]

    if not filename:
        suffix = "devices" if dataset == "devices" else "service-status"
        filename = f"zcc-{suffix}-{datetime.now().strftime('%Y%m%d-%H_%M_%S')}.csv"

    if dataset == "service_status":
        return client.zcc.devices.download_service_status(query_params=query_params, filename=filename)
    elif dataset == "devices":
        return client.zcc.devices.download_devices(query_params=query_params, filename=filename)
    else:
        raise ValueError("Invalid dataset type. Must be 'devices' or 'service_status'.")
