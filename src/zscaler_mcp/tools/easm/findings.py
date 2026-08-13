"""ZEASM findings — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/easm/findings.py``. The four read-only tools
expose the EASM finding surface for an organization's internet-facing assets:

    * zeasm_list_findings          — one row per finding
    * zeasm_get_finding_details    — the full risk/exposure detail for one finding
    * zeasm_get_finding_evidence   — the scan-evidence subset attributed to a finding
    * zeasm_get_finding_scan_output— the complete scan output for a finding

The SDK ``Findings`` wrapper (results / total_results) is unwrapped to the
identifying + risk-bearing subset; the evidence / scan-output payloads keep the
free-form ``content`` (and ``source_type``) the admin actually asked for.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListFindingsInput(BaseModel):
    """Inputs for listing EASM findings for an organization."""

    org_id: Annotated[
        str,
        Field(description="Organization ID (from `zeasm_list_organizations`)."),
    ]


class GetFindingInput(BaseModel):
    """Inputs for fetching one finding's details / evidence / scan output."""

    org_id: Annotated[
        str,
        Field(description="Organization ID (from `zeasm_list_organizations`)."),
    ]
    finding_id: Annotated[
        str,
        Field(description="Finding ID (from `zeasm_list_findings`)."),
    ]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_findings",
    input_model=ListFindingsInput,
    is_list=True,
)
def zeasm_list_findings(args: ListFindingsInput) -> list[dict[str, Any]]:
    """List EASM findings for an organization.

    Read-only. Returns one triage row per finding (id, category, type, status,
    risk level/score, impacted asset, first/last seen) rather than the raw SDK
    record. Use the returned `id` with `zeasm_get_finding_details`,
    `zeasm_get_finding_evidence`, or `zeasm_get_finding_scan_output`.
    """
    if not args.org_id:
        raise ValueError("org_id is required")

    client = get_zscaler_client(service="zeasm")

    findings, _, err = client.zeasm.findings.list_findings(org_id=args.org_id)
    if err:
        raise RuntimeError(f"Failed to list EASM findings for organization {args.org_id}: {err}")

    results = getattr(findings, "results", None) or []
    return shape_many([f.as_dict() for f in results])


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_findings",
    input_model=GetFindingInput,
    is_list=False,
)
def zeasm_get_finding_details(args: GetFindingInput) -> dict[str, Any]:
    """Get the full detail for one EASM finding.

    Read-only. Adds description, country, CISA/EPSS exploitation-likelihood
    signals, and scan provenance on top of the triage fields.
    """
    if not args.org_id:
        raise ValueError("org_id is required")
    if not args.finding_id:
        raise ValueError("finding_id is required")

    client = get_zscaler_client(service="zeasm")

    finding, _, err = client.zeasm.findings.get_finding_details(
        org_id=args.org_id, finding_id=args.finding_id
    )
    if err:
        raise RuntimeError(f"Failed to get EASM finding details for {args.finding_id}: {err}")

    return shape_one(finding.as_dict())


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_findings",
    input_model=GetFindingInput,
    is_list=False,
    wire_format=WireFormat.JSON,
    # `content` is scanner-captured text from an external internet-facing asset —
    # authored by whoever controls that asset, i.e. a potential external attacker.
    untrusted_content=True,
)
def zeasm_get_finding_evidence(args: GetFindingInput) -> dict[str, Any]:
    """Get the scan evidence attributed to one EASM finding.

    Read-only. Returns the evidence `content` (the subset of scan output
    attributable to this finding) and its `source_type`. The content can be
    large free-form scanner text and is preserved verbatim.
    """
    if not args.org_id:
        raise ValueError("org_id is required")
    if not args.finding_id:
        raise ValueError("finding_id is required")

    client = get_zscaler_client(service="zeasm")

    evidence, _, err = client.zeasm.findings.get_finding_evidence(
        org_id=args.org_id, finding_id=args.finding_id
    )
    if err:
        raise RuntimeError(f"Failed to get EASM finding evidence for {args.finding_id}: {err}")

    return shape_one(evidence.as_dict())


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_findings",
    input_model=GetFindingInput,
    is_list=False,
    wire_format=WireFormat.JSON,
    # Full scan output captured from an external internet-facing asset — same
    # externally-authored content as the evidence tool above.
    untrusted_content=True,
)
def zeasm_get_finding_scan_output(args: GetFindingInput) -> dict[str, Any]:
    """Get the complete scan output for one EASM finding.

    Read-only. Returns the full scan `content` and its `source_type`. The
    content can be large free-form scanner text and is preserved verbatim.
    """
    if not args.org_id:
        raise ValueError("org_id is required")
    if not args.finding_id:
        raise ValueError("finding_id is required")

    client = get_zscaler_client(service="zeasm")

    scan_output, _, err = client.zeasm.findings.get_finding_scan_output(
        org_id=args.org_id, finding_id=args.finding_id
    )
    if err:
        raise RuntimeError(f"Failed to get EASM finding scan output for {args.finding_id}: {err}")

    return shape_one(scan_output.as_dict())
