import warnings
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# Suppress SyntaxWarnings from the zscaler SDK
warnings.filterwarnings("ignore", category=SyntaxWarning, module="zscaler.zia.dlp_dictionary")


def zia_dlp_dictionary_manager(
    action: Annotated[
        Literal["read", "read_lite"],
        Field(
            description="DLP dictionary operation: read (list all or retrieve specific by dict_id), read_lite (list with minimal data)."
        ),
    ] = "read",
    dict_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Optional dictionary ID to retrieve a specific dictionary."),
    ] = None,
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing dictionaries by name or description."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict]]:
    """
    Manages ZIA DLP Dictionaries for data loss prevention pattern and phrase matching.
    
    DLP Dictionaries contain patterns and phrases used to identify sensitive data in web traffic.
    They can be custom-defined or predefined by Zscaler, and are used by DLP engines to detect
    potential data loss prevention violations.
    
    Args:
        action (str): Operation to perform: read (list all or retrieve specific by dict_id), read_lite (list with minimal data).
        dict_id (int/str, optional): Optional dictionary ID to retrieve a specific dictionary.
        search (str, optional): Search string to match against dictionary name or description.
        use_legacy (bool, optional): Whether to use the legacy API (default: False).
        service (str, optional): The service to use (default: "zia").
    
    Returns:
        dict | list[dict]: Dictionary object(s) depending on action.
    
    Examples:
        List all DLP dictionaries:
        >>> dictionaries = zia_dlp_dictionary_manager(action="read")
        
        List dictionaries with name and ID only (faster):
        >>> dictionaries = zia_dlp_dictionary_manager(action="read_lite")
        
        Search for dictionaries containing "GDPR":
        >>> dictionaries = zia_dlp_dictionary_manager(action="read", search="GDPR")
        
        Get a specific dictionary by ID:
        >>> dictionary = zia_dlp_dictionary_manager(action="read", dict_id="12345")
        
        Search for dictionaries containing "credit card":
        >>> dictionaries = zia_dlp_dictionary_manager(action="read", search="credit card")
    
    Note:
        - The read action returns full dictionary details including patterns and phrases.
        - When dict_id is provided with read action, it retrieves a specific dictionary.
        - When dict_id is not provided with read action, it lists all dictionaries.
        - The read_lite action returns only name and ID information for faster retrieval.
        - Search is performed against both dictionary name and description fields.
        - Dictionaries can contain patterns (regex) and phrases (exact text matches).
        - Predefined dictionaries are provided by Zscaler and cannot be modified.
        - Custom dictionaries can be created with specific patterns and phrases.
        - Dictionaries are used by DLP engines to create detection rules.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    dlp_dict = client.zia.dlp_dictionary

    if action == "read":
        if dict_id:
            # Retrieve a specific dictionary by ID
            dictionary, _, err = dlp_dict.get_dict(dict_id)
            if err:
                raise Exception(f"Failed to retrieve dictionary {dict_id}: {err}")
            return dictionary.as_dict()
        else:
            # List all dictionaries
            query = {"search": search} if search else {}
            dictionaries, _, err = dlp_dict.list_dicts(query_params=query)
            if err:
                raise Exception(f"Failed to list DLP dictionaries: {err}")
            return [d.as_dict() for d in dictionaries]

    elif action == "read_lite":
        query = {"search": search} if search else {}
        dictionaries, _, err = dlp_dict.list_dicts_lite(query_params=query)
        if err:
            raise Exception(f"Failed to list DLP dictionaries (lite): {err}")
        return [d.as_dict() for d in dictionaries]

    else:
        raise ValueError(f"Unsupported action: {action}")
