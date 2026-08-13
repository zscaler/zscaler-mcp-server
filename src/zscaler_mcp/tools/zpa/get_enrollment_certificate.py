"""ZPA Enrollment Certificates — read-only lookup.

Mirrors v1's ``get_enrollment_certificate.py``. Registered under the exact v1
tool name ``get_zpa_enrollment_certificate`` (a single read tool that lists all
certs, or fetches one by name or by ID). Enrollment certs are referenced by
connector provisioning keys.

Only the output is changed vs v1: the curated ``CertDetail`` view (id + name +
expiry) is returned instead of the raw SDK dict, to keep token usage low.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class EnrollmentCertInput(BaseModel):
    """Inputs for reading ZPA enrollment certificates.

    Provide nothing to list all; provide ``name`` (exact, case-insensitive) or
    ``certificate_id`` to narrow to one (returned as a single-item list).
    """

    certificate_id: Annotated[
        Optional[str], Field(default=None, description="Certificate ID for direct lookup.")
    ] = None
    name: Annotated[
        Optional[str], Field(default=None, description="Exact certificate name (case-insensitive).")
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match on `name`.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=500, description="Items per page (API default 20, max 500)."),
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_provisioning_keys",
    name="get_zpa_enrollment_certificate",
    input_model=EnrollmentCertInput,
    is_list=True,
)
def get_zpa_enrollment_certificate(args: EnrollmentCertInput) -> list[dict[str, Any]]:
    """Read ZPA enrollment certificates: list all, or look one up by name or ID (read-only)."""
    client = get_zscaler_client(service="zpa")
    api = client.zpa.enrollment_certificates

    if args.name:
        certs, _, err = api.list_enrolment(query_params={"search": args.name})
        if err:
            raise RuntimeError(f"Search by name failed: {err}")
        matches = [c for c in (certs or []) if getattr(c, "name", "").lower() == args.name.lower()]
        if not matches:
            raise ValueError(f"No enrollment certificate found matching name '{args.name}'")
        return shape_many([matches[0].as_dict()])

    if args.certificate_id:
        cert, _, err = api.get_enrolment(args.certificate_id)
        if err:
            raise RuntimeError(f"Failed to get enrollment certificate {args.certificate_id}: {err}")
        return shape_many([cert.as_dict()])

    qp: dict[str, Any] = {"search": args.search} if args.search else {}
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    certs, _, err = api.list_enrolment(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list enrollment certificates: {err}")
    return shape_many([c.as_dict() for c in (certs or [])])
