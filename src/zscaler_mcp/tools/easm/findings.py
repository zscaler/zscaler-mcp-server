"""ZEASM findings — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/easm/findings.py``. The four read-only tools
expose the EASM finding surface for an organization's internet-facing assets:

    * zeasm_list_findings          — one curated row per finding (triage view)
    * zeasm_get_finding_details    — the full risk/exposure detail for one finding
    * zeasm_get_finding_evidence   — the scan-evidence subset attributed to a finding
    * zeasm_get_finding_scan_output— the complete scan output for a finding

The SDK ``Findings`` wrapper (results / total_results) is curated down to the
identifying + risk-bearing subset; the evidence / scan-output payloads keep the
free-form ``content`` (and ``source_type``) the admin actually asked for.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many

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


class FindingSummary(AgentView):
    """Lean view — what an agent needs to TRIAGE and reference a finding.

    Every field is identifying, decision-bearing (risk/severity/status), or
    relational (which asset is impacted). Provenance noise is dropped.
    """

    id: str = Field(description="Finding ID. Use with the get_finding_* tools.")
    name: Optional[str] = Field(default=None, description="Finding name/title.")
    category: Optional[str] = Field(default=None, description="Finding category.")
    type: Optional[str] = Field(default=None, description="Finding type.")
    status: Optional[str] = Field(default=None, description="Finding status (open/resolved/...).")
    risk_level: Optional[str] = Field(default=None, description="Risk level (decision-bearing).")
    risk_score: Optional[float] = Field(default=None, description="Numeric risk score.")
    severity_score: Optional[float] = Field(default=None, description="Numeric severity score.")
    impacted_asset_id: Optional[str] = Field(
        default=None, description="ID of the impacted internet-facing asset (relational)."
    )
    impacted_asset_name: Optional[str] = Field(
        default=None, description="Name/host of the impacted asset (relational)."
    )
    is_stale: Optional[bool] = Field(
        default=None, description="Whether the finding is stale (no longer observed)."
    )
    first_seen: Optional[str] = Field(default=None, description="When the finding was first seen.")
    last_seen: Optional[str] = Field(default=None, description="When the finding was last seen.")


class FindingDetail(FindingSummary):
    """Full view — summary plus the exposure/likelihood + scan provenance fields."""

    description: Optional[str] = Field(default=None, description="Detailed finding description.")
    country: Optional[str] = Field(default=None, description="Country attributed to the asset.")
    cisa_likelihood: Optional[Any] = Field(
        default=None, description="CISA exploitation-likelihood signal."
    )
    epss_likelihood: Optional[Any] = Field(
        default=None, description="EPSS exploitation-probability signal."
    )
    scan_type: Optional[str] = Field(
        default=None, description="Scan type that produced the finding."
    )
    profile_id: Optional[str] = Field(default=None, description="Scan/assessment profile ID.")


class FindingPayload(AgentView):
    """Evidence / scan-output payload — the free-form scan content for a finding.

    Both the evidence and scan-output endpoints return a ``content`` blob (often
    large, free-form scanner output) and a ``source_type``. The content is the
    payload the admin asked for, so it is preserved verbatim.
    """

    content: Optional[str] = Field(
        default=None, description="Raw scan content/evidence text for the finding."
    )
    source_type: Optional[str] = Field(
        default=None, description="Where the content came from (the scan source)."
    )


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_finding_summary(raw: dict[str, Any]) -> FindingSummary:
    return FindingSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        category=pick(raw, "category"),
        type=pick(raw, "type"),
        status=pick(raw, "status"),
        risk_level=pick(raw, "risk_level", "riskLevel"),
        risk_score=pick(raw, "risk_score", "riskScore"),
        severity_score=pick(raw, "severity_score", "severityScore"),
        impacted_asset_id=_opt_str(pick(raw, "impacted_asset_id", "impactedAssetId")),
        impacted_asset_name=pick(raw, "impacted_asset_name", "impactedAssetName"),
        is_stale=pick(raw, "is_stale", "isStale"),
        first_seen=pick(raw, "first_seen", "firstSeen"),
        last_seen=pick(raw, "last_seen", "lastSeen"),
    )


def _shape_finding_detail(raw: dict[str, Any]) -> FindingDetail:
    return FindingDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        category=pick(raw, "category"),
        type=pick(raw, "type"),
        status=pick(raw, "status"),
        risk_level=pick(raw, "risk_level", "riskLevel"),
        risk_score=pick(raw, "risk_score", "riskScore"),
        severity_score=pick(raw, "severity_score", "severityScore"),
        impacted_asset_id=_opt_str(pick(raw, "impacted_asset_id", "impactedAssetId")),
        impacted_asset_name=pick(raw, "impacted_asset_name", "impactedAssetName"),
        is_stale=pick(raw, "is_stale", "isStale"),
        first_seen=pick(raw, "first_seen", "firstSeen"),
        last_seen=pick(raw, "last_seen", "lastSeen"),
        description=pick(raw, "description"),
        country=pick(raw, "country"),
        cisa_likelihood=pick(raw, "cisa_likelihood", "cisaLikelihood"),
        epss_likelihood=pick(raw, "epss_likelihood", "epssLikelihood"),
        scan_type=pick(raw, "scan_type", "scanType"),
        profile_id=_opt_str(pick(raw, "profile_id", "profileId")),
    )


def _shape_finding_payload(raw: dict[str, Any]) -> FindingPayload:
    return FindingPayload(
        content=pick(raw, "content"),
        source_type=pick(raw, "source_type", "sourceType"),
    )


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
    output_view=FindingSummary,
    is_list=True,
)
def zeasm_list_findings(args: ListFindingsInput) -> list[dict[str, Any]]:
    """List EASM findings for an organization as curated, agent-facing views.

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
    return shape_many([f.as_dict() for f in results], _shape_finding_summary)


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_findings",
    input_model=GetFindingInput,
    output_view=FindingDetail,
    is_list=False,
)
def zeasm_get_finding_details(args: GetFindingInput) -> dict[str, Any]:
    """Get the full detail for one EASM finding as a curated, agent-facing view.

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

    return _shape_finding_detail(finding.as_dict()).model_dump()


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_findings",
    input_model=GetFindingInput,
    output_view=FindingPayload,
    is_list=False,
    wire_format=WireFormat.JSON,
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

    return _shape_finding_payload(evidence.as_dict()).model_dump()


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_findings",
    input_model=GetFindingInput,
    output_view=FindingPayload,
    is_list=False,
    wire_format=WireFormat.JSON,
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

    return _shape_finding_payload(scan_output.as_dict()).model_dump()
