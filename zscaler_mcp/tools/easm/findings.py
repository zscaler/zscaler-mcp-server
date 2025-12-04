from typing import Annotated, Any, Dict

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================


def zeasm_list_findings(
    org_id: Annotated[str, Field(description="The unique identifier for the organization.")],
    service: Annotated[str, Field(description="The service to use.")] = "zeasm",
) -> Dict[str, Any]:
    """
    List all findings identified and tracked for an organization's internet-facing assets.
    
    This is a read-only operation that retrieves findings detected by EASM scanning.
    
    Args:
        org_id (str): The unique identifier for the organization.
        service (str): The service to use (default: "zeasm").
    
    Returns:
        dict: Dictionary containing:
            - results: List of finding objects
            - total_results: Total number of findings
    
    Example:
        List all findings for an organization:
        >>> findings = zeasm_list_findings(org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c")
        >>> print(f"Total: {findings['total_results']}")
        >>> for finding in findings['results']:
        ...     print(f"  {finding['id']}: {finding['category']}")
    """
    client = get_zscaler_client(use_legacy=False, service=service)
    
    findings, _, err = client.zeasm.findings.list_findings(org_id=org_id)
    if err:
        raise Exception(f"Failed to list EASM findings for organization {org_id}: {err}")
    
    return findings.as_dict()


def zeasm_get_finding_details(
    org_id: Annotated[str, Field(description="The unique identifier for the organization.")],
    finding_id: Annotated[str, Field(description="The unique identifier for the finding.")],
    service: Annotated[str, Field(description="The service to use.")] = "zeasm",
) -> Dict[str, Any]:
    """
    Get details for a specific EASM finding by ID.
    
    This is a read-only operation that retrieves detailed information about a specific finding.
    
    Args:
        org_id (str): The unique identifier for the organization.
        finding_id (str): The unique identifier for the finding.
        service (str): The service to use (default: "zeasm").
    
    Returns:
        dict: Finding details object
    
    Example:
        Get details for a specific finding:
        >>> details = zeasm_get_finding_details(
        ...     org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
        ...     finding_id="8abfc6a2b3058cb75de44c4c65ca4641"
        ... )
        >>> print(details)
    """
    client = get_zscaler_client(use_legacy=False, service=service)
    
    finding, _, err = client.zeasm.findings.get_finding_details(org_id=org_id, finding_id=finding_id)
    if err:
        raise Exception(f"Failed to get EASM finding details for {finding_id}: {err}")
    
    return finding.as_dict()


def zeasm_get_finding_evidence(
    org_id: Annotated[str, Field(description="The unique identifier for the organization.")],
    finding_id: Annotated[str, Field(description="The unique identifier for the finding.")],
    service: Annotated[str, Field(description="The service to use.")] = "zeasm",
) -> Dict[str, Any]:
    """
    Get scan evidence for a specific EASM finding.
    
    This is a read-only operation that retrieves the scan evidence that can be
    attributed to the finding. This is a subset of the scan output.
    
    Args:
        org_id (str): The unique identifier for the organization.
        finding_id (str): The unique identifier for the finding.
        service (str): The service to use (default: "zeasm").
    
    Returns:
        dict: Evidence object containing content and source_type
    
    Example:
        Get evidence for a finding:
        >>> evidence = zeasm_get_finding_evidence(
        ...     org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
        ...     finding_id="8abfc6a2b3058cb75de44c4c65ca4641"
        ... )
        >>> print(evidence['content'])
    """
    client = get_zscaler_client(use_legacy=False, service=service)
    
    evidence, _, err = client.zeasm.findings.get_finding_evidence(org_id=org_id, finding_id=finding_id)
    if err:
        raise Exception(f"Failed to get EASM finding evidence for {finding_id}: {err}")
    
    return evidence.as_dict()


def zeasm_get_finding_scan_output(
    org_id: Annotated[str, Field(description="The unique identifier for the organization.")],
    finding_id: Annotated[str, Field(description="The unique identifier for the finding.")],
    service: Annotated[str, Field(description="The service to use.")] = "zeasm",
) -> Dict[str, Any]:
    """
    Get complete scan output for a specific EASM finding.
    
    This is a read-only operation that retrieves the full scan output for a finding.
    
    Args:
        org_id (str): The unique identifier for the organization.
        finding_id (str): The unique identifier for the finding.
        service (str): The service to use (default: "zeasm").
    
    Returns:
        dict: Scan output object containing content and source_type
    
    Example:
        Get scan output for a finding:
        >>> scan_output = zeasm_get_finding_scan_output(
        ...     org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
        ...     finding_id="8abfc6a2b3058cb75de44c4c65ca4641"
        ... )
        >>> print(scan_output['content'])
    """
    client = get_zscaler_client(use_legacy=False, service=service)
    
    scan_output, _, err = client.zeasm.findings.get_finding_scan_output(org_id=org_id, finding_id=finding_id)
    if err:
        raise Exception(f"Failed to get EASM finding scan output for {finding_id}: {err}")
    
    return scan_output.as_dict()
