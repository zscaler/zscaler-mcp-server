"""ZCC device enrollment — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zcc/list_devices.py`` but adds the v2 shaping
layer: the verbose SDK device record (~40 fields of enrollment/telemetry detail)
is curated down to the identifying + decision-bearing subset an admin actually
reasons about. See DESIGN.md §5.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListDevicesInput(BaseModel):
    """Inputs for listing ZCC enrolled devices."""

    username: Annotated[
        Optional[str],
        Field(default=None, description="Filter by username (e.g. 'jdoe@acme.com')."),
    ] = None
    os_type: Annotated[
        Optional[str],
        Field(default=None, description="OS filter: ios, android, windows, macos, linux."),
    ] = None
    detail: Annotated[
        str,
        Field(
            default="summary",
            pattern="^(summary|full)$",
            description=(
                "Response verbosity. 'summary' (default) returns the lean, "
                "agent-purposed view (identity, OS, agent, registration state, "
                "assigned policy). 'full' adds the rest of the enrollment / "
                "telemetry record (owner, MAC, manufacturer, VPN/tunnel state, "
                "and the registration/keep-alive timestamps)."
            ),
        ),
    ] = "summary"
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=5000, description="Items per page (default 50, max 5000)."),
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class DeviceSummary(AgentView):
    """Lean view — what an agent needs to identify and reason about a device."""

    udid: str = Field(description="Device UDID — the canonical identifier; use in follow-up calls.")
    user: Optional[str] = Field(default=None, description="Enrolled user (email/username).")
    machine_hostname: Optional[str] = Field(default=None, description="Device hostname.")
    os_version: Optional[str] = Field(default=None, description="Operating system + version.")
    agent_version: Optional[str] = Field(default=None, description="ZCC agent version.")
    registration_state: Optional[str] = Field(
        default=None, description="Enrollment/registration state (decision-bearing)."
    )
    policy_name: Optional[str] = Field(
        default=None,
        description="Name of the ZCC app/forwarding policy assigned to this device.",
    )


class DeviceDetail(DeviceSummary):
    """Full view — summary plus the rest of the enrollment / telemetry record.

    Returned only when ``detail='full'``. Restores the fields the SDK device
    record carries beyond the summary subset (company, ownership, hardware,
    VPN/tunnel state, and the enrollment/keep-alive timestamps). Timestamps are
    surfaced verbatim as the epoch-second strings the API returns.
    """

    company_name: Optional[str] = Field(default=None, description="Owning company/tenant name.")
    owner: Optional[str] = Field(default=None, description="Device owner (may differ from user).")
    device_type: Optional[int] = Field(default=None, description="Device type code (SDK `type`).")
    state: Optional[int] = Field(default=None, description="Device state code (SDK `state`).")
    mac_address: Optional[str] = Field(default=None, description="Primary MAC address.")
    manufacturer: Optional[str] = Field(default=None, description="Hardware manufacturer.")
    hardware_detail: Optional[str] = Field(
        default=None, description="Hardware/platform description (SDK `detail`)."
    )
    vpn_state: Optional[int] = Field(default=None, description="VPN state code.")
    tunnel_version: Optional[str] = Field(default=None, description="Tunnel version, if connected.")
    upm_version: Optional[str] = Field(default=None, description="UPM component version.")
    zapp_arch: Optional[str] = Field(default=None, description="ZCC agent architecture (e.g. x64).")
    download_count: Optional[int] = Field(default=None, description="Config download count.")
    registration_time: Optional[str] = Field(
        default=None, description="Enrollment time (epoch seconds, string)."
    )
    deregistration_timestamp: Optional[str] = Field(
        default=None, description="Deregistration time (epoch seconds, string)."
    )
    config_download_time: Optional[str] = Field(
        default=None, description="Last config download time (epoch seconds, string)."
    )
    keep_alive_time: Optional[str] = Field(
        default=None, description="Last keep-alive time (epoch seconds, string)."
    )
    last_seen_time: Optional[str] = Field(
        default=None, description="Last-seen time (epoch seconds, string)."
    )


def _policy_name(raw: dict[str, Any]) -> Optional[str]:
    return pick(raw, "policy_name", "policyName")


def _shape_device(raw: dict[str, Any]) -> DeviceSummary:
    return DeviceSummary(
        udid=str(pick(raw, "udid", "udId", "device_id", default="")),
        user=pick(raw, "user", "owner", "username"),
        machine_hostname=pick(raw, "machine_hostname", "machineHostname", "hostname"),
        os_version=pick(raw, "os_version", "osVersion"),
        agent_version=pick(raw, "agent_version", "agentVersion"),
        registration_state=pick(raw, "registration_state", "registrationState"),
        policy_name=_policy_name(raw),
    )


def _shape_device_detail(raw: dict[str, Any]) -> DeviceDetail:
    return DeviceDetail(
        udid=str(pick(raw, "udid", "udId", "device_id", default="")),
        user=pick(raw, "user", "username"),
        machine_hostname=pick(raw, "machine_hostname", "machineHostname", "hostname"),
        os_version=pick(raw, "os_version", "osVersion"),
        agent_version=pick(raw, "agent_version", "agentVersion"),
        registration_state=pick(raw, "registration_state", "registrationState"),
        policy_name=_policy_name(raw),
        company_name=pick(raw, "company_name", "companyName"),
        owner=pick(raw, "owner"),
        device_type=pick(raw, "type", "device_type"),
        state=pick(raw, "state"),
        mac_address=pick(raw, "mac_address", "macAddress"),
        manufacturer=pick(raw, "manufacturer"),
        hardware_detail=pick(raw, "detail"),
        vpn_state=pick(raw, "vpn_state", "vpnState"),
        tunnel_version=pick(raw, "tunnel_version", "tunnelVersion"),
        upm_version=pick(raw, "upm_version", "upmVersion"),
        zapp_arch=pick(raw, "zapp_arch", "zappArch"),
        download_count=pick(raw, "download_count", "downloadCount"),
        registration_time=pick(raw, "registration_time", "registrationTime"),
        deregistration_timestamp=pick(
            raw, "deregistration_timestamp", "deregistrationTimestamp"
        ),
        config_download_time=pick(raw, "config_download_time", "configDownloadTime"),
        keep_alive_time=pick(raw, "keep_alive_time", "keepAliveTime"),
        last_seen_time=pick(raw, "last_seen_time", "lastSeenTime"),
    )


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zcc",
    toolset="zcc_devices",
    input_model=ListDevicesInput,
    output_view=DeviceSummary,  # the default-detail shape
    is_list=True,
)
def zcc_list_devices(args: ListDevicesInput) -> list[dict[str, Any]]:
    """List ZCC enrolled devices as curated, agent-facing views.

    Read-only. Returns lean summaries by default (`detail='summary'`): the
    identifying + state fields (udid, user, hostname, OS, agent version,
    registration state) plus the assigned `policy_name`. Pass `detail='full'`
    to also get the rest of the enrollment/telemetry record (owner, MAC,
    manufacturer, VPN/tunnel state, download count, and the enrollment /
    keep-alive timestamps). Use the returned `udid` with `zcc_get_device_otp`.
    """
    client = get_zscaler_client(service="zcc")

    qp: dict[str, Any] = {}
    if args.username:
        qp["username"] = args.username
    if args.os_type:
        qp["os_type"] = args.os_type
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size

    devices, _, err = client.zcc.devices.list_devices(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZCC devices: {err}")

    shaper = _shape_device_detail if args.detail == "full" else _shape_device
    return shape_many([d.as_dict() for d in (devices or [])], shaper)
