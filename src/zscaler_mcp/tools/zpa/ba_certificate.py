"""ZPA Browser Access certificates (read + write).

Mirrors v1's ``ba_certificate.py``.

    zpa_list_ba_certificates    (READ)
    zpa_get_ba_certificate      (READ)
    zpa_create_ba_certificate   (CREATE)
    zpa_delete_ba_certificate   (DELETE)

The curated ``CertSummary`` / ``CertDetail`` views and their shapers live here
(certificates' canonical home) and are reused by the read-only enrollment
certificate tool in ``get_enrollment_certificate.py``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many

__all__ = [
    "CertSummary",
    "CertDetail",
    "shape_cert_summary",
    "shape_cert_detail",
]


class ListBaCertsInput(BaseModel):
    """Inputs for listing BA certificates."""

    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match on `name`.")
    ] = None
    detail: Annotated[
        str, Field(default="summary", pattern="^(summary|full)$", description="Response verbosity.")
    ] = "summary"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class GetBaCertInput(BaseModel):
    """Inputs for getting one BA certificate."""

    certificate_id: Annotated[
        str, Field(description="BA certificate ID (string, even if numeric).")
    ]
    detail: Annotated[
        str, Field(default="full", pattern="^(summary|full)$", description="Response verbosity.")
    ] = "full"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CreateBaCertInput(BaseModel):
    """Inputs for creating a BA certificate."""

    name: Annotated[str, Field(description="Display name for the certificate.")]
    cert_blob: Annotated[str, Field(description="PEM-encoded certificate (and key) blob.")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteBaCertInput(BaseModel):
    """Inputs for deleting a BA certificate (destructive)."""

    certificate_id: Annotated[
        str, Field(description="BA certificate ID (string, even if numeric).")
    ]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CertSummary(AgentView):
    """Lean view — identify a certificate (BA or enrollment)."""

    id: str = Field(description="Certificate ID. Use this in follow-up calls.")
    name: str = Field(description="Display name.")
    valid_to: Optional[str] = Field(default=None, description="Expiry (renewal-planning signal).")


class CertDetail(CertSummary):
    """Full view — summary plus subject/issuer/validity + provenance."""

    description: Optional[str] = Field(default=None, description="Admin description.")
    cname: Optional[str] = Field(default=None, description="Certificate common name.")
    issued_to: Optional[str] = Field(default=None, description="Issued-to subject.")
    issued_by: Optional[str] = Field(default=None, description="Issuing authority.")
    valid_from: Optional[str] = Field(default=None, description="Validity start.")
    serial_no: Optional[str] = Field(default=None, description="Certificate serial number.")
    microtenant_id: Optional[str] = Field(default=None, description="Owning microtenant, if any.")


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def shape_cert_summary(raw: dict[str, Any]) -> CertSummary:
    return CertSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        valid_to=pick(raw, "valid_to_in_epochsec", "validToInEpochSec", "valid_to", "validTo"),
    )


def shape_cert_detail(raw: dict[str, Any]) -> CertDetail:
    return CertDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        valid_to=pick(raw, "valid_to_in_epochsec", "validToInEpochSec", "valid_to", "validTo"),
        description=pick(raw, "description"),
        cname=pick(raw, "cname"),
        issued_to=pick(raw, "issued_to", "issuedTo"),
        issued_by=pick(raw, "issued_by", "issuedBy"),
        valid_from=pick(
            raw, "valid_from_in_epochsec", "validFromInEpochSec", "valid_from", "validFrom"
        ),
        serial_no=pick(raw, "serial_no", "serialNo"),
        microtenant_id=pick(raw, "microtenant_id", "microtenantId"),
    )


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_ba_certificates",
    input_model=ListBaCertsInput,
    output_view=CertSummary,
    is_list=True,
)
def zpa_list_ba_certificates(args: ListBaCertsInput) -> list[dict[str, Any]]:
    """List ZPA Browser Access certificates (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    certs, _, err = client.zpa.certificates.list_issued_certificates(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list BA certificates: {err}")
    shaper = shape_cert_detail if args.detail == "full" else shape_cert_summary
    return shape_many([c.as_dict() for c in (certs or [])], shaper)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_ba_certificates",
    input_model=GetBaCertInput,
    output_view=CertDetail,
    is_list=False,
)
def zpa_get_ba_certificate(args: GetBaCertInput) -> dict[str, Any]:
    """Get one ZPA Browser Access certificate by ID (read-only)."""
    if not args.certificate_id:
        raise ValueError("certificate_id is required")
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    cert, _, err = client.zpa.certificates.get_certificate(args.certificate_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get BA certificate {args.certificate_id}: {err}")
    shaper = shape_cert_detail if args.detail == "full" else shape_cert_summary
    return shaper(cert.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_ba_certificates",
    input_model=CreateBaCertInput,
    output_view=CertDetail,
    is_list=False,
)
def zpa_create_ba_certificate(args: CreateBaCertInput) -> dict[str, Any]:
    """Create a ZPA Browser Access certificate from a PEM blob (write).

    Gated by HMAC + `--write-tools`.
    """
    if not args.name or not args.cert_blob:
        raise ValueError("name and cert_blob are required")
    client = get_zscaler_client(service="zpa")
    body: dict[str, Any] = {"name": args.name, "cert_blob": args.cert_blob}
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id
    created, _, err = client.zpa.certificates.add_certificate(**body)
    if err:
        raise RuntimeError(f"Failed to create BA certificate: {err}")
    return shape_cert_detail(created.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_ba_certificates",
    input_model=DeleteBaCertInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_ba_certificate(args: DeleteBaCertInput) -> dict[str, Any]:
    """Delete a ZPA Browser Access certificate (destructive write). Gated by HMAC + `--write-tools`."""
    if not args.certificate_id:
        raise ValueError("certificate_id is required")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.certificates.delete_certificate(
        args.certificate_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete BA certificate {args.certificate_id}: {err}")
    return OperationResult(
        success=True, message=f"BA certificate {args.certificate_id} deleted successfully."
    ).model_dump()
