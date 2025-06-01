from src.sdk.zscaler_client import get_zscaler_client
from typing import Union


def sandbox_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
) -> Union[dict, list, str]:
    """
    Tool for retrieving ZIA Sandbox information.

    Supported actions:
    - quota: Returns the current sandbox quota information.
    - behavioral_analysis: Returns the list of MD5 hashes blocked by sandbox.
    - file_hash_count: Returns usage of file hash quota (blocked vs available).

    Args:
        action (str): One of ['quota', 'behavioral_analysis', 'file_hash_count'].
        cloud (str): Zscaler cloud.
        client_id (str): OAuth client ID.
        client_secret (str): OAuth client secret.
        customer_id (str): Zscaler customer ID.
        vanity_domain (str): Zscaler vanity subdomain.

    Returns:
        Union[dict, list, str]: Response payload depending on the action.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )
    sandbox_api = client.zia.sandbox

    if action == "quota":
        result, _, err = sandbox_api.get_quota()
        if err:
            raise Exception(f"Failed to retrieve sandbox quota: {err}")
        return result

    elif action == "behavioral_analysis":
        result, _, err = sandbox_api.get_behavioral_analysis()
        if err:
            raise Exception(f"Failed to retrieve behavioral analysis: {err}")
        return result.get("fileHashesToBeBlocked", []) if isinstance(result, dict) else result

    elif action == "file_hash_count":
        result, _, err = sandbox_api.get_file_hash_count()
        if err:
            raise Exception(f"Failed to retrieve file hash count: {err}")
        return result

    else:
        raise ValueError("Unsupported action. Must be one of: 'quota', 'behavioral_analysis', 'file_hash_count'")
