from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def enrollment_certificate_manager(
    action: Annotated[str, Field(description="Must be 'read'.")],
    certificate_id: Annotated[
        str,
        Field(description="Certificate ID to retrieve (fallback if name is not used)."),
    ] = None,
    name: Annotated[str, Field(description="Certificate name to search for.")] = None,
    query_params: Annotated[
        dict,
        Field(description="Optional query parameters for filtering via search key."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[dict, List[dict], str]:
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

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

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
