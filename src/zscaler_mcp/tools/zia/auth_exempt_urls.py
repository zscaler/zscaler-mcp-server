"""ZIA cookie-authentication exempt URL list.

Mirrors v1's ``client.zia.authentication_settings`` SDK calls. Add/delete are
additive/subtractive against the exempt list. Writes are staged until
``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, tool
from zscaler_mcp.shaping import AgentView


class _NoArgs(BaseModel):
    pass


class ExemptUrlsInput(BaseModel):
    exempt_urls: Annotated[list[str], Field(description="URLs to add/remove on the exempt list.")]


class UrlList(AgentView):
    urls: list[str] = Field(default_factory=list, description="Exempt URLs.")
    count: int = Field(description="Number of exempt URLs.")


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _url_list(raw: Any) -> UrlList:
    if hasattr(raw, "as_dict"):
        raw = raw.as_dict()
    if isinstance(raw, dict):
        urls = raw.get("urls") or raw.get("exempt_urls") or raw.get("exemptedUrls") or []
    elif isinstance(raw, list):
        urls = raw
    else:
        urls = []
    urls = [str(u) for u in urls]
    return UrlList(urls=urls, count=len(urls))


@tool(
    action=READ,
    service="zia",
    toolset="zia_authentication_settings",
    input_model=_NoArgs,
    output_view=UrlList,
    is_list=False,
)
def zia_list_auth_exempt_urls(args: _NoArgs) -> dict[str, Any]:
    """List the ZIA cookie-auth exempt URL list."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.authentication_settings.get_exempted_urls()
    if err:
        raise RuntimeError(f"Failed to list auth exempt URLs: {err}")
    return _url_list(result).model_dump()


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_authentication_settings",
    input_model=ExemptUrlsInput,
    output_view=UrlList,
    is_list=False,
)
def zia_add_auth_exempt_urls(args: ExemptUrlsInput) -> dict[str, Any]:
    """Add URLs to the ZIA cookie-auth exempt list (additive write). Activate after."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.authentication_settings.add_urls_to_exempt_list(
        parse_list(args.exempt_urls)
    )
    if err:
        raise RuntimeError(f"Failed to add auth exempt URLs: {err}")
    return _url_list(result).model_dump()


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_authentication_settings",
    input_model=ExemptUrlsInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_auth_exempt_urls(args: ExemptUrlsInput) -> dict[str, Any]:
    """Remove URLs from the ZIA cookie-auth exempt list (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.authentication_settings.delete_urls_from_exempt_list(
        parse_list(args.exempt_urls)
    )
    if err:
        raise RuntimeError(f"Failed to delete auth exempt URLs: {err}")
    return OperationResult(
        success=True, message=f"Removed {len(args.exempt_urls)} URL(s) from the exempt list."
    ).model_dump()
