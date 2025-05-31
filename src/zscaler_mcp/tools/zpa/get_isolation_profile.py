from zscaler_mcp.sdk.zscaler_client import get_zscaler_client

def isolation_profile_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    name: str = None,
) -> list[dict] | dict | str:
    """
    Tool for retrieving ZPA Cloud Browser Isolation (CBI) profiles.

    Supported actions:
    - 'read': Lists all available isolation profiles or returns a specific profile by exact name match.

    Behavior:
    - If `name` is provided, the tool searches the full profile list and returns the matching profile as a dict.
      The user must explicitly supply the full name of the profile in their request.
    - If `name` is not provided, the tool returns a list of all isolation profiles.
    - The returned profile always includes the 'id' field, which can be extracted and reused in rule creation or updates.

    Args:
        action (str): Only 'read' is supported.
        name (str, optional): Full name of the isolation profile to search for.

    Returns:
        dict: A single profile (when name is matched)
        list[dict]: A list of all profiles when no name is provided
        str: Error message if no match is found or action is unsupported
    """
    if action != "read":
        raise ValueError("Only 'read' action is supported for isolation profiles.")

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    profiles, _, err = client.zpa.cbi_profile.list_cbi_profiles()
    if err:
        raise Exception(f"Failed to list CBI profiles: {err}")

    profiles_data = [p.as_dict() for p in profiles]

    if name:
        for profile in profiles_data:
            if profile.get("name") == name:
                return profile
        raise Exception(f"No CBI profile found with name: {name}")

    return profiles_data
