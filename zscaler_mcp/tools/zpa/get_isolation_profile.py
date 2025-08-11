from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def isolation_profile_manager(
    action: Annotated[str, Field(description="Only 'read' is supported.")],
    name: Annotated[
        str, Field(description="Full name of the isolation profile to search for.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[List[dict], dict, str]:
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

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

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
