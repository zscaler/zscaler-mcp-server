"""ZIA Sandbox reports & quota (read-only).

Mirrors v1's ``client.zia.sandbox`` SDK calls. These are sandbox report/quota
reads — distinct from Sandbox *policy rules* (see sandbox_rules.py).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_one


class _NoArgs(BaseModel):
    pass


class SandboxReportInput(BaseModel):
    md5_hash: Annotated[str, Field(description="MD5 hash of the file to fetch the report for.")]
    report_details: Annotated[
        Optional[str],
        Field(default=None, description="Report detail level (e.g. 'full', 'summary')."),
    ] = None


@tool(
    action=READ,
    service="zia",
    toolset="zia_sandbox",
    input_model=_NoArgs,
    is_list=False,
)
def zia_get_sandbox_quota(args: _NoArgs) -> dict[str, Any]:
    """Get the ZIA Sandbox API submission quota."""
    client = get_zscaler_client(service="zia")
    quota, _, err = client.zia.sandbox.get_quota()
    if err:
        raise RuntimeError(f"Failed to get sandbox quota: {err}")
    return shape_one(quota)


@tool(
    action=READ,
    service="zia",
    toolset="zia_sandbox",
    input_model=_NoArgs,
    is_list=False,
)
def zia_get_sandbox_behavioral_analysis(args: _NoArgs) -> dict[str, Any]:
    """Get the ZIA Sandbox behavioral-analysis configuration."""
    client = get_zscaler_client(service="zia")
    ba, _, err = client.zia.sandbox.get_behavioral_analysis()
    if err:
        raise RuntimeError(f"Failed to get sandbox behavioral analysis: {err}")
    return shape_one(ba)


@tool(
    action=READ,
    service="zia",
    toolset="zia_sandbox",
    input_model=_NoArgs,
    is_list=False,
)
def zia_get_sandbox_file_hash_count(args: _NoArgs) -> dict[str, Any]:
    """Get the ZIA Sandbox custom file-hash blocklist usage/quota."""
    client = get_zscaler_client(service="zia")
    count, _, err = client.zia.sandbox.get_file_hash_count()
    if err:
        raise RuntimeError(f"Failed to get sandbox file hash count: {err}")
    return shape_one(count)


@tool(
    action=READ,
    service="zia",
    toolset="zia_sandbox",
    input_model=SandboxReportInput,
    is_list=False,
)
def zia_get_sandbox_report(args: SandboxReportInput) -> dict[str, Any]:
    """Get the ZIA Sandbox detonation report for a file MD5 hash."""
    client = get_zscaler_client(service="zia")
    if args.report_details:
        report, _, err = client.zia.sandbox.get_report(args.md5_hash, args.report_details)
    else:
        report, _, err = client.zia.sandbox.get_report(args.md5_hash)
    if err:
        raise RuntimeError(f"Failed to get sandbox report for {args.md5_hash}: {err}")
    return shape_one(report)
