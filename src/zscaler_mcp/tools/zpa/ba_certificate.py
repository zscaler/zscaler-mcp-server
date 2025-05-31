from zscaler_mcp.sdk.zscaler_client import get_zscaler_client
from typing import Union

def ba_certificate_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    certificate_id: str = None,
    name: str = None,
    cert_blob: str = None,
    microtenant_id: str = None,
    query_params: dict = None,
) -> Union[dict, list[dict], str]:
    """
    Tool for managing ZPA Browser Access (BA) Certificates.

    Supported actions:
    - create: Requires cert_blob and name.
    - read: If certificate_id is provided, fetch by ID. Otherwise, list all or filter via query_params.search.
    - delete: Requires certificate_id.

    Args:
        cert_blob (str): Required PEM string when creating a certificate.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

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
