"""ZCC One-Time Password (OTP) Tool.

Wraps ``client.zcc.secrets.get_otp`` from the Python SDK.

A single call to the ZCC ``/getOtp`` endpoint returns a bundle of OTPs
for one device — not a single password. The bundle includes the
``logout_otp`` (the one-time logout password admins use to sign a user
out of Zscaler Client Connector) plus other operation-scoped OTPs:
``exit_otp``, ``uninstall_otp``, ``revert_otp``, and per-service disable
OTPs (``zia_disable_otp``, ``zpa_disable_otp``, ``zdx_disable_otp``,
``zdp_disable_otp``, ``anti_tempering_disable_otp``,
``deception_settings_otp``).

The single tool below returns the full bundle so the same call can serve
multiple admin workflows (logout, uninstall, temporarily disable a
service, exit). Callers and skills should select the field they need —
typically ``logout_otp`` for the One-Time Logout Password use case — and
treat every value as a sensitive short-lived credential.
"""

from typing import Annotated, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATION
# =============================================================================


def zcc_get_device_otp(
    udid: Annotated[
        Optional[str],
        Field(
            description=(
                "The device's UDID (the canonical identifier ZCC uses for the "
                "enrolled endpoint). Look it up via `zcc_list_devices` — the "
                "field is exposed as `udid` on each device record. Either "
                "`udid` or `device_id` must be supplied; if both are given, "
                "`udid` wins."
            )
        ),
    ] = None,
    device_id: Annotated[
        Optional[str],
        Field(
            description=(
                "Alias for `udid`. Accepted for parity with the SDK's "
                "`device_id` query parameter — the SDK maps it to `udid` "
                "automatically before hitting the API."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zcc",
) -> dict:
    """Get the One-Time Password (OTP) bundle for a Zscaler Client Connector device.

    The ZCC ``/getOtp`` endpoint returns several OTPs for a single device
    in one call. Each OTP is short-lived and unlocks a specific admin
    operation on that device:

    - ``logout_otp`` — One-Time Logout Password. Sign the user out of ZCC.
      This is the OTP for the standard "I need to log my user out of
      Zscaler Client Connector" workflow.
    - ``exit_otp`` — Allow the user to fully exit / quit ZCC.
    - ``uninstall_otp`` — Allow ZCC to be uninstalled.
    - ``revert_otp`` — Revert ZCC to a previous version.
    - ``zia_disable_otp`` — Temporarily disable ZIA enforcement on the device.
    - ``zpa_disable_otp`` — Temporarily disable ZPA enforcement on the device.
    - ``zdx_disable_otp`` — Temporarily disable ZDX on the device.
    - ``zdp_disable_otp`` — Temporarily disable ZDP on the device.
    - ``anti_tempering_disable_otp`` — Disable anti-tampering protection.
    - ``deception_settings_otp`` — Modify Deception settings on the device.
    - ``otp`` — Generic OTP (legacy field; usually mirrors one of the above).

    🔒 READ-ONLY OPERATION (the API verb is GET and no tenant state is
    mutated), but the returned values ARE sensitive short-lived credentials.
    Treat them like passwords: do not log them, do not echo them in plain
    text outside the admin's secure channel, and do not paste them into
    public chat history.

    Required input:

    - Either ``udid`` or ``device_id`` (alias). Look up the UDID by
      calling ``zcc_list_devices(username="<email>")`` first, then pass
      the resulting ``udid`` here.

    Returns:
        A dict with the full OTP bundle (snake_case keys), e.g.::

            {
                "logout_otp": "123456",
                "exit_otp": "654321",
                "uninstall_otp": "...",
                "revert_otp": "...",
                "zia_disable_otp": "...",
                "zpa_disable_otp": "...",
                "zdx_disable_otp": "...",
                "zdp_disable_otp": "...",
                "anti_tempering_disable_otp": "...",
                "deception_settings_otp": "...",
                "otp": "..."
            }

    Examples:
        >>> # Generate the One-Time Logout Password for a device.
        >>> bundle = zcc_get_device_otp(udid="d-29-9b-7c-c5-3f-d2-90-3c-d5-")
        >>> logout_password = bundle["logout_otp"]
    """
    if not udid and not device_id:
        raise ValueError(
            "Either udid or device_id must be supplied. Look up the device's "
            "udid via zcc_list_devices(username='<email>') first."
        )

    client = get_zscaler_client(service=service)

    query_params = {"udid": udid or device_id}

    otp, _, err = client.zcc.secrets.get_otp(query_params=query_params)
    if err:
        raise Exception(f"Failed to retrieve OTP for device {query_params['udid']}: {err}")

    return otp.as_dict()
