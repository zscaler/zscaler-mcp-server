import os
from typing import Union
from src.sdk.zscaler_client import get_zscaler_client


def sandbox_file_submit(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    file_path: str,
    force: bool = False,
    sandbox_token: str = None,
    sandbox_cloud: str = None,
) -> Union[dict, str]:
    """
    Submits a file to ZIA Advanced Cloud Sandbox for analysis.

    Args:
        cloud (str): Zscaler cloud (e.g., "beta", "zscalerthree").
        client_id (str): ZIA OAuth client ID.
        client_secret (str): ZIA OAuth client secret.
        customer_id (str): ZIA customer ID.
        vanity_domain (str): ZIA vanity domain.
        file_path (str): Absolute or relative path to the file to submit.
        force (bool): Whether to force reanalysis (default: False).
        sandbox_token (str): Required token for authenticating sandbox submission.
        sandbox_cloud (str): Zscaler cloud for sandbox API (e.g., "zscalertwo", "zscalerthree").

    Returns:
        dict: API response body.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        sandbox_token=sandbox_token,
        sandbox_cloud=sandbox_cloud,
    )
    result, _, err = client.zia.sandbox.submit_file(file_path=file_path, force=force)
    if err:
        raise Exception(f"File submission failed: {err}")
    return result
