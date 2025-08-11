from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def app_segments_by_type_manager(
    application_type: Annotated[
        str,
        Field(
            description="Application type to filter by. Must be one of 'BROWSER_ACCESS', 'INSPECT', or 'SECURE_REMOTE_ACCESS'."
        ),
    ],
    expand_all: Annotated[
        bool, Field(description="Whether to expand all related data.")
    ] = False,
    query_params: Annotated[
        dict,
        Field(
            description="Optional filters like 'search', 'page_size', or 'microtenant_id'."
        ),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[List[dict], str]:
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
        raise ValueError(
            "Invalid application_type. Must be one of 'BROWSER_ACCESS', 'INSPECT', or 'SECURE_REMOTE_ACCESS'."
        )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

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
