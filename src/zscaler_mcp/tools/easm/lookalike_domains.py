"""ZEASM lookalike domains — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/easm/lookalike_domains.py``. Two read-only
tools surface the lookalike/impersonation domains EASM detects for an
organization's brand:

    * zeasm_list_lookalike_domains — one row per detected lookalike domain
    * zeasm_get_lookalike_domain   — full detail for one lookalike domain by name

The SDK ``LookALikeDomains`` wrapper (results / total_results) is unwrapped to
the identifying + risk-bearing subset an analyst reasons about (which domain,
what it impersonates, how risky, is it live, how to remediate).
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one

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


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_lookalike_domains",
    input_model=ListLookalikeDomainsInput,
    is_list=True,
    # Same records as the GET counterpart below: the lookalike hostname and
    # registrant/registrar fields are authored by whoever registered the
    # lookalike domain — by definition an external threat actor.
    untrusted_content=True,
)
def zeasm_list_lookalike_domains(args: ListLookalikeDomainsInput) -> list[dict[str, Any]]:
    """List EASM lookalike domains for an organization.

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
    return shape_many([d.as_dict() for d in results])


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm_lookalike_domains",
    input_model=GetLookalikeDomainInput,
    is_list=False,
    # WHOIS registrant fields are authored by whoever registered the lookalike
    # domain — by definition an external threat actor.
    untrusted_content=True,
)
def zeasm_get_lookalike_domain(args: GetLookalikeDomainInput) -> dict[str, Any]:
    """Get full detail for one EASM lookalike domain.

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

    return shape_one(domain.as_dict())
