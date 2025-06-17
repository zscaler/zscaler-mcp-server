from src.sdk.zscaler_client import get_zscaler_client

def app_protection_profile_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    name: str = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> list[dict] | dict:
    """
    Tool for listing and searching ZPA App Protection Profiles (Inspection Profiles).

    Supported actions:
    - read: returns all profiles or a specific profile by name.

    Args:
        action (str): Must be 'read'.
        name (str, optional): Name of the profile to match. If provided, only profiles with matching name will be returned.

    Returns:
        list[dict] or dict: A single profile dict if name is matched, or a list of all profiles.
    """
    if action != "read":
        raise ValueError("Only 'read' action is supported")

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        use_legacy=use_legacy,
        service=service,
    )

    query_params = {"search": name} if name else {}

    profiles, _, err = client.zpa.app_protection.list_profiles(query_params=query_params)
    if err:
        raise Exception(f"Failed to list app protection profiles: {err}")

    profile_dicts = [p.as_dict() for p in (profiles or [])]

    if name:
        for p in profile_dicts:
            if p.get("name") == name:
                return p
        raise ValueError(f"No profile found with name: {name}")

    return profile_dicts
