"""ZCC device OTP bundle — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zcc/get_otp.py``. A single ``/getOtp`` call
returns a bundle of short-lived OTPs for one device. The view declares the full
documented bundle explicitly (every field is operationally meaningful here, so
this is a curated *allowlist*, not a trimming) — and the values are sensitive
credentials the output sanitizer leaves intact but callers must treat as secrets.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field, model_validator

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick


class GetDeviceOtpInput(BaseModel):
    """Inputs for fetching a device's OTP bundle. Either udid or device_id is required."""

    udid: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Device UDID (look it up via zcc_list_devices). Wins if both are given.",
        ),
    ] = None
    device_id: Annotated[
        Optional[str],
        Field(default=None, description="Alias for udid (SDK maps device_id -> udid)."),
    ] = None

    @model_validator(mode="after")
    def _require_one(self) -> "GetDeviceOtpInput":
        if not self.udid and not self.device_id:
            raise ValueError(
                "Either udid or device_id must be supplied. Look up the device's "
                "udid via zcc_list_devices(username='<email>') first."
            )
        return self


class DeviceOtpBundle(AgentView):
    """Curated OTP bundle. Every value is a sensitive, short-lived credential."""

    logout_otp: Optional[str] = Field(default=None, description="One-Time Logout Password.")
    exit_otp: Optional[str] = Field(default=None, description="Exit/quit ZCC OTP.")
    uninstall_otp: Optional[str] = Field(default=None, description="Uninstall ZCC OTP.")
    revert_otp: Optional[str] = Field(default=None, description="Revert ZCC version OTP.")
    zia_disable_otp: Optional[str] = Field(default=None, description="Disable ZIA enforcement OTP.")
    zpa_disable_otp: Optional[str] = Field(default=None, description="Disable ZPA enforcement OTP.")
    zdx_disable_otp: Optional[str] = Field(default=None, description="Disable ZDX OTP.")
    zdp_disable_otp: Optional[str] = Field(default=None, description="Disable ZDP OTP.")
    anti_tempering_disable_otp: Optional[str] = Field(
        default=None, description="Disable anti-tampering OTP."
    )
    deception_settings_otp: Optional[str] = Field(
        default=None, description="Modify Deception settings OTP."
    )
    otp: Optional[str] = Field(default=None, description="Generic/legacy OTP field.")


def _shape_otp(raw: dict[str, Any]) -> DeviceOtpBundle:
    return DeviceOtpBundle(
        logout_otp=pick(raw, "logout_otp", "logoutOtp"),
        exit_otp=pick(raw, "exit_otp", "exitOtp"),
        uninstall_otp=pick(raw, "uninstall_otp", "uninstallOtp"),
        revert_otp=pick(raw, "revert_otp", "revertOtp"),
        zia_disable_otp=pick(raw, "zia_disable_otp", "ziaDisableOtp"),
        zpa_disable_otp=pick(raw, "zpa_disable_otp", "zpaDisableOtp"),
        zdx_disable_otp=pick(raw, "zdx_disable_otp", "zdxDisableOtp"),
        zdp_disable_otp=pick(raw, "zdp_disable_otp", "zdpDisableOtp"),
        anti_tempering_disable_otp=pick(
            raw, "anti_tempering_disable_otp", "antiTemperingDisableOtp"
        ),
        deception_settings_otp=pick(raw, "deception_settings_otp", "deceptionSettingsOtp"),
        otp=pick(raw, "otp"),
    )


@tool(
    action=READ,
    service="zcc",
    toolset="zcc_devices",
    input_model=GetDeviceOtpInput,
    output_view=DeviceOtpBundle,
    is_list=False,
)
def zcc_get_device_otp(args: GetDeviceOtpInput) -> dict[str, Any]:
    """Get the OTP bundle for a ZCC device (logout / exit / uninstall / disable OTPs).

    Read-only (GET, no tenant mutation) but the returned values ARE sensitive
    short-lived credentials — treat them like passwords. Requires the device's
    `udid` (from `zcc_list_devices`).
    """
    client = get_zscaler_client(service="zcc")
    qp = {"udid": args.udid or args.device_id}

    otp, _, err = client.zcc.secrets.get_otp(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to retrieve OTP for device {qp['udid']}: {err}")

    return _shape_otp(otp.as_dict()).model_dump()
