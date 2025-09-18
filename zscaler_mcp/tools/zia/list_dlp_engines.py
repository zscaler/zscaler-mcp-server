from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_dlp_engine_manager(
    action: Annotated[
        Literal["read", "read_lite"],
        Field(
            description="DLP engine operation: read (list all or retrieve specific by engine_id), read_lite (list with minimal data)."
        ),
    ] = "read",
    engine_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Optional engine ID to retrieve a specific engine."),
    ] = None,
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing engines by name or description."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict]]:
    """
    Manages ZIA DLP Engines for data loss prevention rule evaluation.
    
    DLP Engines are logical expressions that combine DLP dictionaries using operators like AND, OR, NOT,
    and Sum to create sophisticated data loss prevention detection rules. They evaluate content against
    patterns and phrases to identify potential data breaches or policy violations.
    
    Args:
        action (str): Operation to perform: read (list all or retrieve specific by engine_id), read_lite (list with minimal data).
        engine_id (int/str, optional): Optional engine ID to retrieve a specific engine.
        search (str, optional): Search string to match against engine name or description.
        use_legacy (bool, optional): Whether to use the legacy API (default: False).
        service (str, optional): The service to use (default: "zia").
    
    Returns:
        dict | list[dict]: Engine object(s) depending on action.
    
    Examples:
        List all DLP engines:
        >>> engines = zia_dlp_engine_manager(action="read")
        
        List engines with name and ID only (faster):
        >>> engines = zia_dlp_engine_manager(action="read_lite")
        
        Search for engines containing "credit card":
        >>> engines = zia_dlp_engine_manager(action="read", search="credit card")
        
        Get a specific engine by ID:
        >>> engine = zia_dlp_engine_manager(action="read", engine_id="12345")
        
        Search for engines containing "SSN":
        >>> engines = zia_dlp_engine_manager(action="read", search="SSN")
    
    Note:
        - The read action returns full engine details including expressions and configuration.
        - When engine_id is provided with read action, it retrieves a specific engine.
        - When engine_id is not provided with read action, it lists all engines.
        - The read_lite action returns only name and ID information for faster retrieval.
        - Search is performed against both engine name and description fields.
        - DLP engines use logical expressions to combine multiple DLP dictionaries.
        - Engine expressions can use operators: All (AND), Any (OR), Exclude (NOT), Sum (count).
        - Engines can be predefined by Zscaler or custom-created by administrators.
        - Custom engines allow for organization-specific data loss prevention rules.
        - Engine expressions reference DLP dictionaries by their IDs (e.g., D63.S > 1).
        - Engines are used in DLP rules to define what content should be monitored or blocked.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    dlp_engine = client.zia.dlp_engine

    if action == "read":
        if engine_id:
            # Retrieve a specific engine by ID
            engine, _, err = dlp_engine.get_dlp_engines(engine_id)
            if err:
                raise Exception(f"Failed to retrieve engine {engine_id}: {err}")
            return engine.as_dict()
        else:
            # List all engines
            query = {"search": search} if search else {}
            engines, _, err = dlp_engine.list_dlp_engines(query_params=query)
            if err:
                raise Exception(f"Failed to list DLP engines: {err}")
            return [e.as_dict() for e in engines]

    elif action == "read_lite":
        query = {"search": search} if search else {}
        engines, _, err = dlp_engine.list_dlp_engines_lite(query_params=query)
        if err:
            raise Exception(f"Failed to list DLP engines (lite): {err}")
        return [e.as_dict() for e in engines]

    else:
        raise ValueError(f"Unsupported action: {action}")
