from zscaler_mcp.sdk.zscaler_client import get_zscaler_client
from zscaler_mcp import app
from typing import Union, List
from typing import Annotated
from pydantic import Field


@app.tool(
    name="zpa_ba_certificates",
    description="Tool for managing ZPA Browser Access (BA) Certificates.",
)
def ba_certificate_manager(
    action: Annotated[
        str,
        Field(description="Action to perform: 'create', 'read', or 'delete'.")
    ],
    certificate_id: Annotated[
        str,
        Field(description="Certificate ID for read or delete operations.")
    ] = None,
    name: Annotated[
        str,
        Field(description="Name of the certificate.")
    ] = None,
    cert_blob: Annotated[
        str,
        Field(description="Required PEM string when creating a certificate.")
    ] = None,
    microtenant_id: Annotated[
        str,
        Field(description="Microtenant ID for scoping operations.")
    ] = None,
    query_params: Annotated[
        dict,
        Field(description="Optional query parameters for filtering results.")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zpa",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing ZPA Browser Access (BA) Certificates.

    Supported actions:
    - create: Requires cert_blob and name.
    - read: If certificate_id is provided, fetch by ID. Otherwise, list all or filter via query_params.search.
    - delete: Requires certificate_id.

    Args:
        cert_blob (str): Required PEM string when creating a certificate.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    api = client.zpa.certificates

    if action == "create":
        if not name or not cert_blob:
            raise ValueError("Both name and cert_blob are required for certificate creation")

        body = {
            "name": name,
            "cert_blob": cert_blob,
        }
        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        created, _, err = api.add_certificate(**body)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        query_params = query_params or {}
        if microtenant_id:
            query_params["microtenant_id"] = microtenant_id

        if certificate_id:
            cert, _, err = api.get_certificate(certificate_id, query_params=query_params)
            if err:
                raise Exception(f"Read failed: {err}")
            return cert.as_dict()
        else:
            certs, _, err = api.list_issued_certificates(query_params=query_params)
            if err:
                raise Exception(f"List failed: {err}")
            return [c.as_dict() for c in certs]

    elif action == "delete":
        if not certificate_id:
            raise ValueError("certificate_id is required for deletion")

        _, _, err = api.delete_certificate(certificate_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted certificate {certificate_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
