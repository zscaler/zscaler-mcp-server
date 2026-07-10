"""ZEASM lookalike domains — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/easm/lookalike_domains.py``. Two read-only
tools surface the lookalike/impersonation domains EASM detects for an
organization's brand:

    * zeasm_list_lookalike_domains — one curated row per detected lookalike domain
    * zeasm_get_lookalike_domain   — full detail for one lookalike domain by name

The SDK ``LookALikeDomains`` wrapper (results / total_results) is curated down to
the identifying + risk-bearing subset an analyst reasons about (which domain,
what it impersonates, how risky, is it live, how to remediate).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListLookalikeDomainsInput(BaseModel):
    """Inputs for listing EASM lookalike domains for an organization."""

    org_id: Annotated[
        str,
        Field(description="Organization ID (from `zeasm_list_organizations`)."),
    ]


class GetLookalikeDomainInput(BaseModel):
    """Inputs for fetching one EASM lookalike domain by its raw domain name."""

    org_id: Annotated[
        str,
        Field(description="Organization ID (from `zeasm_list_organizations`)."),
    ]
    lookalike_raw: Annotated[
        str,
        Field(
            description=(
                "The lookalike domain name to fetch (e.g. 'example-domain.com'). "
                "Use the `lookalike_raw` value from `zeasm_list_lookalike_domains`."
            )
        ),
    ]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class LookalikeDomainSummary(AgentView):
    """Lean view — what an analyst needs to TRIAGE a lookalike domain.

    Identifying (the lookalike + the domain it impersonates), decision-bearing
    (risk, registration state, status), and relational (deception methods).
    """

    lookalike_raw: str = Field(
        description="The detected lookalike domain. The canonical identifier; use it in get calls."
    )
    original_domain: Optional[str] = Field(
        default=None, description="The legitimate domain this lookalike impersonates (relational)."
    )
    risk_category: Optional[str] = Field(default=None, description="Risk category classification.")
    risk_score: Optional[float] = Field(default=None, description="Numeric risk score.")
    status: Optional[str] = Field(default=None, description="Tracking status of the lookalike.")
    is_registered: Optional[bool] = Field(
        default=None, description="Whether the lookalike domain is currently registered (live)."
    )
    deception_method: list[str] = Field(
        default_factory=list, description="Detected impersonation/deception techniques."
    )


class LookalikeDomainDetail(LookalikeDomainSummary):
    """Full view — summary plus registration provenance + remediation guidance."""

    description: Optional[str] = Field(default=None, description="Detailed description.")
    registrar: Optional[str] = Field(default=None, description="Domain registrar, if registered.")
    registered_by: Optional[str] = Field(
        default=None, description="Registrant/owner of the lookalike domain, if known."
    )
    created_date: Optional[str] = Field(default=None, description="Domain creation date.")
    expiration_date: Optional[str] = Field(default=None, description="Domain expiration date.")
    updated_date: Optional[str] = Field(default=None, description="Last-updated date.")
    remediation: Optional[Any] = Field(
        default=None, description="Suggested remediation guidance for this lookalike."
    )


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_lookalike_summary(raw: dict[str, Any]) -> LookalikeDomainSummary:
    return LookalikeDomainSummary(
        lookalike_raw=str(pick(raw, "lookalike_raw", "lookalikeRaw", default="")),
        original_domain=pick(raw, "original_domain", "originalDomain"),
        risk_category=pick(raw, "risk_category", "riskCategory"),
        risk_score=pick(raw, "risk_score", "riskScore"),
        status=pick(raw, "status"),
        is_registered=pick(raw, "is_registered", "isRegistered"),
        deception_method=[str(m) for m in coalesce(raw, "deception_method", "deceptionMethod")],
    )


def _shape_lookalike_detail(raw: dict[str, Any]) -> LookalikeDomainDetail:
    return LookalikeDomainDetail(
        lookalike_raw=str(pick(raw, "lookalike_raw", "lookalikeRaw", default="")),
        original_domain=pick(raw, "original_domain", "originalDomain"),
        risk_category=pick(raw, "risk_category", "riskCategory"),
        risk_score=pick(raw, "risk_score", "riskScore"),
        status=pick(raw, "status"),
        is_registered=pick(raw, "is_registered", "isRegistered"),
        deception_method=[str(m) for m in coalesce(raw, "deception_method", "deceptionMethod")],
        description=pick(raw, "description"),
        registrar=pick(raw, "registrar"),
        registered_by=pick(raw, "registered_by", "registeredBy"),
        created_date=pick(raw, "created_date", "createdDate"),
        expiration_date=pick(raw, "expiration_date", "expirationDate"),
        updated_date=pick(raw, "updated_date", "updatedDate"),
        remediation=pick(raw, "remediation"),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_lookalike_domains",
    input_model=ListLookalikeDomainsInput,
    output_view=LookalikeDomainSummary,
    is_list=True,
)
def zeasm_list_lookalike_domains(args: ListLookalikeDomainsInput) -> list[dict[str, Any]]:
    """List EASM lookalike domains for an organization as curated views.

    Read-only. Returns one triage row per detected lookalike/impersonation
    domain (the lookalike, the domain it impersonates, risk, registration
    state, deception methods). Use the returned `lookalike_raw` with
    `zeasm_get_lookalike_domain` for full detail.
    """
    if not args.org_id:
        raise ValueError("org_id is required")

    client = get_zscaler_client(service="zeasm")

    domains, _, err = client.zeasm.lookalike_domains.list_lookalike_domains(org_id=args.org_id)
    if err:
        raise RuntimeError(
            f"Failed to list EASM lookalike domains for organization {args.org_id}: {err}"
        )

    results = getattr(domains, "results", None) or []
    return shape_many([d.as_dict() for d in results], _shape_lookalike_summary)


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_lookalike_domains",
    input_model=GetLookalikeDomainInput,
    output_view=LookalikeDomainDetail,
    is_list=False,
)
def zeasm_get_lookalike_domain(args: GetLookalikeDomainInput) -> dict[str, Any]:
    """Get full detail for one EASM lookalike domain as a curated view.

    Read-only. Adds description, registrar/registrant + lifecycle dates, and
    remediation guidance on top of the triage fields. Look the domain up by its
    `lookalike_raw` name (from `zeasm_list_lookalike_domains`).
    """
    if not args.org_id:
        raise ValueError("org_id is required")
    if not args.lookalike_raw:
        raise ValueError("lookalike_raw is required")

    client = get_zscaler_client(service="zeasm")

    domain, _, err = client.zeasm.lookalike_domains.get_lookalike_domain(
        org_id=args.org_id, lookalike_raw=args.lookalike_raw
    )
    if err:
        raise RuntimeError(
            f"Failed to get EASM lookalike domain details for {args.lookalike_raw}: {err}"
        )

    return _shape_lookalike_detail(domain.as_dict()).model_dump()
