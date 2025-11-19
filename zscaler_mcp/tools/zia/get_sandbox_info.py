from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def _get_sandbox_client(use_legacy: bool, service: str):
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    return client.zia.sandbox


def zia_get_sandbox_quota(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Return ZIA sandbox quota usage."""
    sandbox_api = _get_sandbox_client(use_legacy, service)
    result, _, err = sandbox_api.get_quota()
    if err:
        raise Exception(f"Failed to retrieve sandbox quota: {err}")
    return result


def zia_get_sandbox_behavioral_analysis(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[List, dict]:
    """Return the list of MD5 hashes blocked by sandbox."""
    sandbox_api = _get_sandbox_client(use_legacy, service)
    result, _, err = sandbox_api.get_behavioral_analysis()
    if err:
        raise Exception(f"Failed to retrieve sandbox behavioral analysis: {err}")
    return result


def zia_get_sandbox_file_hash_count(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Return sandbox blocked-hash usage statistics."""
    sandbox_api = _get_sandbox_client(use_legacy, service)
    result, _, err = sandbox_api.get_file_hash_count()
    if err:
        raise Exception(f"Failed to retrieve sandbox file hash count: {err}")
    return result


def zia_get_sandbox_report(
    md5_hash: Annotated[str, Field(description="MD5 hash of the file analyzed by sandbox.")],
    report_details: Annotated[
        str,
        Field(description="Report detail level: 'summary' (default) or 'full'.")
    ] = "summary",
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """Return sandbox analysis report for the provided MD5 hash."""
    sandbox_api = _get_sandbox_client(use_legacy, service)
    result, _, err = sandbox_api.get_report(md5_hash, report_details=report_details)
    if err:
        raise Exception(f"Failed to retrieve sandbox report for hash {md5_hash}: {err}")
    return result


def sandbox_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'quota', 'behavioral_analysis', or 'file_hash_count'."
        ),
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List, str]:
    """
    Backwards-compatible sandbox tool that dispatches to the specialized helpers.
    """
    if action == "quota":
        return zia_get_sandbox_quota(use_legacy=use_legacy, service=service)
    if action == "behavioral_analysis":
        return zia_get_sandbox_behavioral_analysis(use_legacy=use_legacy, service=service)
    if action == "file_hash_count":
        return zia_get_sandbox_file_hash_count(use_legacy=use_legacy, service=service)
    raise ValueError(
        "Unsupported action. Must be one of: 'quota', 'behavioral_analysis', 'file_hash_count'"
    )
