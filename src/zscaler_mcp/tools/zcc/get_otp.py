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
from zscaler_mcp.shaping import shape_one


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


@tool(
    action=READ,
    service="zcc",
    toolset="zcc_devices",
    input_model=GetDeviceOtpInput,
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

    return shape_one(otp.as_dict())
