from src.sdk.zscaler_client import get_zscaler_client
from typing import Union

def app_segments_by_type_manager(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    application_type: str,
    expand_all: bool = False,
    query_params: dict = None,
) -> Union[list[dict], str]:
    """
    Tool to retrieve ZPA application segments by type.

    Args:
        application_type (str): Required. Must be one of "BROWSER_ACCESS", "INSPECT", or "SECURE_REMOTE_ACCESS".
        expand_all (bool, optional): Whether to expand all related data. Defaults to False.
        query_params (dict, optional): Filters like 'search', 'page_size', or 'microtenant_id'.

    Returns:
        list[dict]: List of matching application segments.
    """
    if application_type not in ("BROWSER_ACCESS", "INSPECT", "SECURE_REMOTE_ACCESS"):
        raise ValueError("Invalid application_type. Must be one of 'BROWSER_ACCESS', 'INSPECT', or 'SECURE_REMOTE_ACCESS'.")

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    api = client.zpa.app_segment_by_type
    query_params = query_params or {}

    segments, _, err = api.get_segments_by_type(
        application_type=application_type,
        expand_all=expand_all,
        query_params=query_params,
    )
    if err:
        raise Exception(f"Failed to retrieve application segments: {err}")

    return [segment.as_dict() for segment in segments]
