---
name: zcc-generate-logout-otp
description: "Generate a One-Time Logout Password (OTP) for a Zscaler Client Connector (ZCC) user. Walks the admin from a user identifier (email or device name) through device lookup → confirmation → OTP retrieval → secure delivery, surfacing logout_otp from the ZCC OTP bundle. Use when an admin needs to remotely sign a specific user out of ZCC — for example after a credential reset, lost / decommissioned device, suspected compromise (incident response), or routine offboarding. DO NOT USE WHEN: the admin needs to uninstall ZCC, exit ZCC, revert to a prior ZCC version, or temporarily disable a service (ZIA/ZPA/ZDX/ZDP) on the device — those use other OTPs from the same bundle and warrant their own confirmation flow."
---

# ZCC: Generate a One-Time Logout Password

## Keywords

one-time logout password, otp, logout otp, zcc logout, log user out of zcc, sign out client connector, force logout, remote logout, zscaler client connector logout, generate otp, zcc otp

## Overview

Generate a One-Time Logout Password (OTP) that signs a specific user out of Zscaler Client Connector. The skill resolves a user identifier (email or device name) to a ZCC device record, confirms the device with the admin, retrieves the OTP bundle from the ZCC `/getOtp` endpoint, and surfaces the `logout_otp` for delivery via a secure channel.

**Use this skill when:** An admin needs to remotely sign a specific user out of ZCC — typical triggers include credential reset, lost or decommissioned device, suspected compromise, incident response, or routine offboarding.

**DO NOT use this skill when:**

- The admin needs to **uninstall** ZCC, **exit** ZCC, **revert** ZCC to a previous version, or **temporarily disable** a service (ZIA/ZPA/ZDX/ZDP) on the device. The same `/getOtp` call returns OTPs for all of those operations, but each is a distinct admin action — surface the requested OTP only after explicit confirmation. If a different operation skill exists for the workflow, prefer that.
- The admin wants to log out **all** users / a fleet — this skill is per-device. For bulk operations, run it per device after a list-then-confirm step.

---

## Background — what the OTP bundle actually contains

The ZCC `/getOtp` endpoint (wrapped by `zcc_get_device_otp`) returns a **bundle** of short-lived OTPs in one call, not a single password. The fields on the returned dict are:

| Field | Operation it unlocks |
|---|---|
| `logout_otp` | **One-Time Logout Password** — the field this skill cares about |
| `exit_otp` | Allow user to fully exit / quit ZCC |
| `uninstall_otp` | Allow ZCC to be uninstalled |
| `revert_otp` | Revert ZCC to a previous version |
| `zia_disable_otp` | Temporarily disable ZIA enforcement on the device |
| `zpa_disable_otp` | Temporarily disable ZPA enforcement on the device |
| `zdx_disable_otp` | Temporarily disable ZDX on the device |
| `zdp_disable_otp` | Temporarily disable ZDP on the device |
| `anti_tempering_disable_otp` | Disable anti-tampering protection |
| `deception_settings_otp` | Modify Deception settings on the device |
| `otp` | Generic OTP (legacy field; usually mirrors one of the above) |

For the One-Time **Logout** Password use case, the only field to surface is `logout_otp`. Do **not** print or list the rest of the bundle in plain text — they unlock different operations and the admin did not ask for them. If the admin later asks for one of those, repeat the flow with explicit confirmation for the new operation.

---

## Workflow

Follow this 5-step process.

### Step 1: Gather Identifiers

Ask the admin for at least one of:

- **User email** (e.g. `jdoe@acme.com`) — preferred; resolves cleanly even when the user has multiple devices.
- **Device name** (e.g. `JDOE-LAPTOP-01`) — useful when the same user has more than one enrolled device.

Optionally, also ask for:

- **Platform** (`windows`, `macos`, `ios`, `android`, `linux`) — narrows results when a user has devices on multiple OSes.
- **Department** — only useful if the admin is unsure of the email and wants to scope the search.

If the admin provided neither an email nor a device name in the original prompt (per the PRD example `[insert here]` placeholder), ask once and stop.

---

### Step 2: Look Up the Device

Call `zcc_list_devices` with the most specific filter the admin gave you.

**By email (most common):**

```text
zcc_list_devices(username="<email>")
```

**By email + platform (when the user has multiple OS devices):**

```text
zcc_list_devices(username="<email>", os_type="windows")
```

**By device name (search the username field; fall back to a JMESPath match on the device record's name):**

```text
zcc_list_devices(query="[?machine_hostname=='<device_name>' || name=='<device_name>']")
```

Each device record exposes a `udid` field — the canonical identifier the OTP endpoint expects. The record also includes `user`, `machine_hostname`, `os_type`, `os_version`, `last_seen_time`, `enrollment_time`, `state`, etc.

**Empty result:** Stop. Tell the admin no ZCC device was found for the supplied identifier and ask whether they want to try a different email / device name. Do NOT broaden the search silently.

---

### Step 3: Confirm With the Admin

Present a short, plain-language summary of the matched device(s) and ask the admin to pick one if there are multiple matches. Confirm BEFORE generating the OTP.

Surface (per match):

- Username (email)
- Device name / hostname
- OS + version
- Last seen time
- Enrollment state

Example confirmation:

> I found one ZCC device for `jdoe@acme.com`:
>
> - **JDOE-LAPTOP-01** — Windows 11 22H2
> - Last seen: 2026-05-06 14:22 UTC
> - Enrolled and active
>
> Should I generate the One-Time Logout Password for this device?

If multiple devices match, list them all and ask which one (or confirm "all of them" — in which case loop the OTP generation per device). Never pick automatically.

---

### Step 4: Generate the OTP

Once the admin confirms a single device, call:

```text
zcc_get_device_otp(udid="<udid_from_step_2>")
```

The tool returns the full bundle. **Read only `logout_otp` from the response** for this skill. Treat the value as a sensitive short-lived credential.

---

### Step 5: Deliver the OTP Securely

Surface the value with a short usage instruction. Never paste the OTP into a public chat transcript or commit it to logs.

Recommended response shape:

> One-Time Logout Password for **JDOE-LAPTOP-01** (`jdoe@acme.com`):
>
> `123456`
>
> Have the user enter this code in Zscaler Client Connector → **More** → **Logout** when prompted. The code is single-use and expires shortly — if it isn't used in the next few minutes, generate a new one.
>
> Delivery: send via your standard out-of-band channel (helpdesk ticket update, signed email, MFA-protected chat). Do **not** post it in a shared channel.

If the admin requested several devices, repeat steps 4–5 per device and label each OTP with the matching device name + user. Never commingle OTPs in one undifferentiated list.

---

## Validation

There is no "verify" call after OTP generation — the OTP becomes valid the moment the API returns it and is consumed when the user enters it in ZCC. Tell the admin to follow up with the user if the logout doesn't take effect within ~5 minutes (the OTP TTL is short). If the OTP expires, call `zcc_get_device_otp` again — each call returns a fresh bundle.

---

## Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `Either udid or device_id must be supplied` | Skipped device lookup and called the OTP tool with no identifier | Run `zcc_list_devices` first and pass the resulting `udid` |
| OTP returned but logout doesn't happen | Wrong device picked when the user has multiple enrolled devices | Confirm device hostname + last-seen time with the admin; regenerate against the correct `udid` |
| `Failed to retrieve OTP for device ...` | Stale or invalid `udid`, or device de-enrolled between lookup and OTP call | Re-list the user's devices to refresh; check `state` is active |
| Admin pastes the OTP into the wrong place | Surfaced multiple OTPs from the bundle without labelling | Surface ONLY `logout_otp` in this skill; never print the full bundle |
| User reports the code "doesn't work" minutes later | OTP TTL elapsed | Generate a new one; OTPs are single-use and short-lived |
| Search by `username` returns nothing for a user you know exists | Mismatch between the IDP email and the enrolled username (e.g. UPN vs SMTP) | Try the alternate form, or list without `username` and grep client-side via the `query` parameter |

---

## Related Skills

- (None today.) Other OTPs in the bundle (`uninstall_otp`, `exit_otp`, `revert_otp`, per-service disable OTPs) warrant their own skills if/when they become recurring workflows. Do not silently surface them from this skill.

---

## Tool Reference

This skill uses:

- `zcc_list_devices` — find the device by email / OS / hostname.
- `zcc_get_device_otp` — return the OTP bundle for a given `udid`. Surface only `logout_otp`.
