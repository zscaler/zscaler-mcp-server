# ZCC (Zscaler Client Connector) Steering

## Overview

ZCC is the endpoint agent that connects users to the Zscaler Zero Trust Exchange. It runs on user devices and routes traffic through ZPA (for private apps) and ZIA (for internet/SaaS). ZCC provides device enrollment status, forwarding profiles, trusted network configuration, and per-device OTP/passcode retrieval for support workflows.

## Available Skills

Kiro should prefer the **guided skill** below when a user's intent matches. It drives the right tool sequence end-to-end with appropriate confirmations.

| Skill | Path | When to use |
|-------|------|-------------|
| Generate logout OTP | `skills/zcc/generate-logout-otp/SKILL.md` | "I need a logout OTP for user X", "Generate a ZCC passcode so this user can sign out", "ZCC won't let the user log out without a code" |

Cross-product fallback: ZCC enrollment is usually the first thing to check in connectivity issues — for full-stack diagnosis use `skills/cross-product/troubleshoot-user-connectivity/SKILL.md`.

## Key Concepts

- **Devices**: Endpoints with ZCC installed — includes enrollment status, OS, version, and last-seen information
- **Trusted Networks**: Network definitions where ZCC behavior may differ (e.g., corporate LAN may bypass certain tunnels)
- **Forwarding Profiles**: Define how traffic is routed through Zscaler (which traffic goes to ZPA vs ZIA vs direct)
- **Device OTP**: One-time passcode for a specific user/device. Required by ZCC for actions like sign-out, removal, and disable when the admin has not pre-shared an unlock password. Retrieved via `zcc_get_device_otp`.
- **CSV Export**: Bulk device data export for analysis and reporting

## Common Workflows

### Device Inventory & Status Check

Use for understanding the fleet of enrolled devices.

```text
1. zcc_list_devices          → Get all enrolled devices with status, OS, version
2. Filter results by enrollment status:
   - Enrolled: Device is active and connected
   - Pending: Device enrollment in progress
   - Unenrolled: Device has been removed
```

### Traffic Forwarding Review

Use to understand how traffic is being routed.

```
1. zcc_list_forwarding_profiles → Check forwarding configurations
2. Review: which traffic types go through ZPA, ZIA, or bypass
3. zcc_list_trusted_networks    → Check if trusted networks may alter routing
```

### Cross-Product Correlation

ZCC data is the starting point for cross-product troubleshooting:

```
1. zcc_list_devices          → Find user's device, confirm enrollment
2. Then correlate with:
   - ZDX: zdx_list_devices   → Get device health metrics
   - ZPA: zpa_list_access_policy_rules → Check access policies
   - ZIA: zia_list_url_filtering_rules → Check internet access policies
```

### Generate a Sign-Out / Removal OTP

When a user contacts the helpdesk asking to sign out of ZCC and the admin has not pre-shared an unlock password, retrieve a one-time passcode for that device:

```
1. zcc_list_devices                → Confirm the user has an enrolled device and grab the device identifier
2. zcc_get_device_otp(udid=<udid>) → Returns the OTP / passcode block for that device
3. Share the appropriate code with the user (logout, removal, disable, anti-tamper) over an authenticated channel
```

The skill `skills/zcc/generate-logout-otp/SKILL.md` walks through identifier resolution (email → device row → udid) and the safest disclosure pattern.

## Available Tools

| Tool | Description |
|------|-------------|
| `zcc_list_devices` | List all enrolled devices with status |
| `zcc_list_trusted_networks` | List trusted network definitions |
| `zcc_list_forwarding_profiles` | List forwarding profiles |
| `zcc_get_device_otp` | Retrieve the OTP / passcode block for a specific enrolled device (logout, removal, disable, anti-tamper) |

All ZCC tools are **read-only**.

## Device Status Values

| Status | Meaning |
|--------|---------|
| Enrolled | Device is registered and actively connected |
| Pending | Device enrollment is in progress |
| Unenrolled | Device has been removed from management |

## Best Practices

1. **Check enrollment first in troubleshooting** — An unenrolled or pending device explains most "can't access anything" issues
2. **Review forwarding profiles** — Misconfigured forwarding profiles can cause traffic to bypass ZPA/ZIA
3. **Check trusted networks** — Users on trusted networks may bypass ZPA/ZIA, which changes access behavior
4. **Combine with ZDX** — ZCC shows device enrollment; ZDX shows device health metrics. Both are needed for full device troubleshooting.
