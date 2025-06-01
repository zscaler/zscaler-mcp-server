from src.sdk.zscaler_client import get_zscaler_client

def enrollment_certificate_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    certificate_id: str = None,
    name: str = None,
    query_params: dict = None,
) -> dict | list[dict] | str:
    """
    Get-only tool for retrieving ZPA Enrollment Certificates.

    Supported actions:
    - read: retrieves a certificate by name (preferred) or by ID (fallback).

    Args:
        action (str): Must be "read".
        name (str, optional): Certificate name to search for.
        certificate_id (str, optional): Fallback if name search is not used.
        query_params (dict, optional): Used for filtering via search key.

    Returns:
        dict or list[dict] or str
    """
    if action != "read":
        raise ValueError("Only 'read' action is supported.")

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    api = client.zpa.enrollment_certificates

    if name:
        query_params = query_params or {}
        query_params["search"] = name
        certs, _, err = api.list_enrolment(query_params=query_params)
        if err:
            raise Exception(f"Search by name failed: {err}")
        matches = [c for c in certs if c.name.lower() == name.lower()]
        if not matches:
            return f"No certificate found matching name '{name}'"
        return matches[0].as_dict()

    elif certificate_id:
        cert, _, err = api.get_enrolment(certificate_id)
        if err:
            raise Exception(f"Lookup by ID failed: {err}")
        return cert.as_dict()

    else:
        certs, _, err = api.list_enrolment()
        if err:
            raise Exception(f"Listing certificates failed: {err}")
        return [c.as_dict() for c in (certs or [])]
