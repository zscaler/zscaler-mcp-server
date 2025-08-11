from datetime import datetime
from typing import Annotated, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zcc_devices_csv_exporter(
    dataset: Annotated[
        str,
        Field(
            description="Type of report to download. Valid values: 'devices', 'service_status'."
        ),
    ] = "devices",
    os_type: Annotated[
        Optional[str],
        Field(
            description="Device operating system type. Valid values: ios, android, windows, macos, linux."
        ),
    ] = None,
    registration_type: Annotated[
        Optional[str],
        Field(
            description="Registration status. Valid values: all, registered, unregistered, removal_pending, removed, quarantined."
        ),
    ] = None,
    filename: Annotated[
        Optional[str],
        Field(description="Custom filename for the CSV. Defaults to timestamped file."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zcc",
) -> str:
    """
    Downloads ZCC device information or service status as a CSV file.
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
        return client.zcc.devices.download_service_status(
            query_params=query_params, filename=filename
        )
    elif dataset == "devices":
        return client.zcc.devices.download_devices(
            query_params=query_params, filename=filename
        )
    else:
        raise ValueError("Invalid dataset type. Must be 'devices' or 'service_status'.")
