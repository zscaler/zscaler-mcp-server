"""ZIA DLP dictionaries — read-only manager.

Mirrors v1's ``list_dlp_dictionaries.py`` exactly: a single multiplexed read tool
registered under the v1 name ``get_zia_dlp_dictionaries`` (list all, list lite, or
fetch one by ID). Backed by ``client.zia.dlp_dictionary``.

Only the output is changed vs v1: the curated ``DlpDictionarySummary`` view is
returned instead of the raw SDK dict, to keep token usage low.
"""

from __future__ import annotations

import warnings
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many

warnings.filterwarnings("ignore", category=SyntaxWarning, module="zscaler.zia.dlp_dictionary")


class DlpDictionaryInput(BaseModel):
    """Inputs for reading ZIA DLP dictionaries.

    Provide nothing to list all; provide ``dict_id`` to fetch one (returned as a
    single-item list); use ``action='read_lite'`` for the minimal id/name listing.
    """

    action: Annotated[
        Literal["read", "read_lite"],
        Field(default="read", description="'read' for full data, 'read_lite' for id/name only."),
    ] = "read"
    dict_id: Annotated[
        Optional[str], Field(default=None, description="Dictionary ID for direct lookup.")
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on name/description.")
    ] = None


class DlpDictionarySummary(AgentView):
    id: str = Field(description="Dictionary ID. Use in DLP-engine / web-DLP rules.")
    name: str = Field(description="Display name.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    custom: Optional[bool] = Field(default=None, description="Whether the dictionary is custom.")


def shape_summary(raw: dict[str, Any]) -> DlpDictionarySummary:
    return DlpDictionarySummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        description=pick(raw, "description"),
        custom=pick(raw, "custom", "custom_phrase_supported"),
    )


@tool(
    action=READ,
    service="zia",
    toolset="zia_dlp",
    input_model=DlpDictionaryInput,
    output_view=DlpDictionarySummary,
    is_list=True,
)
def get_zia_dlp_dictionaries(args: DlpDictionaryInput) -> list[dict[str, Any]]:
    """Read ZIA DLP dictionaries: list all/lite, or fetch one by ID (read-only)."""
    client = get_zscaler_client(service="zia")
    api = client.zia.dlp_dictionary
    qp = {"search": args.search} if args.search else {}

    if args.action == "read" and args.dict_id:
        dictionary, _, err = api.get_dict(args.dict_id)
        if err:
            raise RuntimeError(f"Failed to get DLP dictionary {args.dict_id}: {err}")
        return shape_many([dictionary.as_dict()], shape_summary)

    if args.action == "read_lite":
        dicts, _, err = api.list_dicts_lite(query_params=qp)
    else:
        dicts, _, err = api.list_dicts(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list DLP dictionaries: {err}")
    return shape_many([d.as_dict() for d in (dicts or [])], shape_summary)
