from src.sdk.zscaler_client import get_zscaler_client
from typing import Union


def posture_profile_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    profile_id: str = None,
    name: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> Union[dict, list[dict], str]:
    """
    Tool for retrieving ZPA Posture Profiles.

    Supported actions:
    - read: Fetch all posture profiles, one by profile_id, or match by name.

    Args:
        action (str): Must be "read".
        profile_id (str): Optional posture profile ID for direct lookup.
        name (str): Optional posture profile name to search for.
        query_params (dict): Optional filters (e.g., search, pagination).

    Returns:
        dict | list[dict] | str
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        use_legacy=use_legacy,
        service=service,
    )

    api = client.zpa.posture_profiles

    if action == "read":
        query_params = query_params or {}

        if profile_id:
            profile, _, err = api.get_profile(profile_id)
            if err:
                raise Exception(f"Failed to fetch posture profile {profile_id}: {err}")
            return profile.as_dict()

        if name:
            query_params["search"] = name
            profiles, _, err = api.list_posture_profiles(query_params=query_params)
            if err:
                raise Exception(f"Failed to search posture profiles: {err}")
            matched = next((p for p in profiles if p.name == name), None)
            if not matched:
                raise Exception(f"No posture profile found with name '{name}'")
            return matched.as_dict()

        profiles, _, err = api.list_posture_profiles(query_params=query_params)
        if err:
            raise Exception(f"Failed to list posture profiles: {err}")
        return [p.as_dict() for p in profiles]

    raise ValueError(f"Unsupported action: {action}")
