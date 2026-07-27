"""ZIA Advanced Threat Protection (ATP) policy — settings, security exceptions,
malicious-URL denylist.

Mirrors v1's ``client.zia.atp_policy`` SDK calls. ATP settings + security
exceptions are PUT-replace; the malicious-URL denylist uses add/delete. Writes
are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import shape_one

from ._settings import OperationResult


class _NoArgs(BaseModel):
    pass


class UpdateSettingsInput(BaseModel):
    settings: Annotated[
        dict[str, Any],
        Field(description="Complete ATP policy dict (PUT-replace). Fetch + merge first."),
    ]


class UpdateExceptionsInput(BaseModel):
    bypass_urls: Annotated[
        list[str], Field(description="Full bypass-URL allowlist (replaces existing list).")
    ]


class MaliciousUrlsInput(BaseModel):
    malicious_urls: Annotated[list[str], Field(description="URLs to add/remove on the denylist.")]


# =============================================================================
# ATP SETTINGS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_atp_policy",
    input_model=_NoArgs,
    is_list=False,
)
def zia_get_atp_settings(args: _NoArgs) -> dict[str, Any]:
    """Get the ZIA tenant-wide ATP policy block."""
    client = get_zscaler_client(service="zia")
    settings, _, err = client.zia.atp_policy.get_atp_settings()
    if err:
        raise RuntimeError(f"Failed to get ATP settings: {err}")
    return shape_one(settings)


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_atp_policy",
    input_model=UpdateSettingsInput,
    is_list=False,
)
def zia_update_atp_settings(args: UpdateSettingsInput) -> dict[str, Any]:
    """Update ZIA ATP settings (strict PUT-replace write). Activate after."""
    client = get_zscaler_client(service="zia")
    updated, _, err = client.zia.atp_policy.update_atp_settings(**args.settings)
    if err:
        raise RuntimeError(f"Failed to update ATP settings: {err}")
    return shape_one(updated)


# =============================================================================
# ATP SECURITY EXCEPTIONS (allowlist)
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_atp_policy",
    input_model=_NoArgs,
    is_list=False,
)
def zia_get_atp_security_exceptions(args: _NoArgs) -> dict[str, Any]:
    """Get the ZIA ATP security-exception bypass URL allowlist."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.atp_policy.get_atp_security_exceptions()
    if err:
        raise RuntimeError(f"Failed to get ATP security exceptions: {err}")
    return shape_one(result)


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_atp_policy",
    input_model=UpdateExceptionsInput,
    is_list=False,
)
def zia_update_atp_security_exceptions(args: UpdateExceptionsInput) -> dict[str, Any]:
    """Replace the ZIA ATP security-exception allowlist (full-list write). Activate after."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.atp_policy.update_atp_security_exceptions(
        bypass_urls=parse_list(args.bypass_urls)
    )
    if err:
        raise RuntimeError(f"Failed to update ATP security exceptions: {err}")
    return shape_one(result)


# =============================================================================
# ATP MALICIOUS URLS (denylist)
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_atp_policy",
    input_model=_NoArgs,
    is_list=False,
)
def zia_list_atp_malicious_urls(args: _NoArgs) -> dict[str, Any]:
    """List the ZIA ATP malicious-URL denylist."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.atp_policy.get_atp_malicious_urls()
    if err:
        raise RuntimeError(f"Failed to list ATP malicious URLs: {err}")
    return shape_one(result)


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_atp_policy",
    input_model=MaliciousUrlsInput,
    is_list=False,
)
def zia_add_atp_malicious_urls(args: MaliciousUrlsInput) -> dict[str, Any]:
    """Add URLs to the ZIA ATP malicious-URL denylist (additive write). Activate after."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.atp_policy.add_atp_malicious_urls(
        malicious_urls=parse_list(args.malicious_urls)
    )
    if err:
        raise RuntimeError(f"Failed to add ATP malicious URLs: {err}")
    return shape_one(result)


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_atp_policy",
    input_model=MaliciousUrlsInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_atp_malicious_urls(args: MaliciousUrlsInput) -> dict[str, Any]:
    """Remove URLs from the ZIA ATP malicious-URL denylist (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.atp_policy.delete_atp_malicious_urls(
        malicious_urls=parse_list(args.malicious_urls)
    )
    if err:
        raise RuntimeError(f"Failed to delete ATP malicious URLs: {err}")
    return OperationResult(
        success=True, message=f"Removed {len(args.malicious_urls)} URL(s) from the ATP denylist."
    ).model_dump()
