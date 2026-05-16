---
name: zpa-application_segment-pra-onboard
description: "End-to-end onboarding of a new Privileged Remote Access (PRA) application in Zscaler Private Access. Walks through the full dependency chain — App connector group, server group, segment group, PRA credential, PRA portal, PRA application segment with apps_config (RDP/SSH targets), and access policy rule — for RDP and SSH targets brokered through the PRA portal without requiring a native RDP/SSH client or Zscaler Client Connector. Use only when the admin explicitly asks for Privileged Remote Access (PRA), RDP, SSH, jump-host, or bastion access. DO NOT USE WHEN: the admin wants a regular client-routed application segment (use zpa-application_segment-onboard) or a clientless web app (use zpa-application_segment-ba-onboard)."
---

# ZPA: Onboard Privileged Remote Access (PRA) Application

## Keywords

privileged remote access, pra, rdp access, ssh access, jump host, bastion host, jumpbox, pra portal, pra credential, agentless rdp, agentless ssh, browser rdp, browser ssh, secure remote access

## Overview

Onboard a new **Privileged Remote Access (PRA)** application in Zscaler Private Access. PRA segments publish RDP and SSH targets to authorized users through Zscaler's PRA portal — the end user connects through their browser without a native RDP/SSH client and without ZCC. The connection is brokered by the PRA portal and authenticated using PRA credentials managed as separate ZPA resources.

This skill walks through the full dependency chain: connector group → server group → segment group → **PRA credential** → **PRA portal** → **PRA application segment with `apps_config`** → access policy rule.

**Use this skill when:** The admin explicitly mentions Privileged Remote Access, PRA, RDP, SSH, jump host, bastion, or "publish a Windows/Linux server for browser-based remote access."

**DO NOT use this skill when:**

- The admin wants a regular client-routed application segment (any TCP/UDP app reachable via ZCC) — use `zpa-application_segment-onboard` instead.
- The admin wants to publish a clientless **web** application — use `zpa-application_segment-ba-onboard` instead.

---

## What makes PRA different from a regular or BA app segment

| Concept | Regular segment | Browser Access (BA) | Privileged Remote Access (PRA) |
|---|---|---|---|
| SDK / tool family | `zpa_*_application_segment` | `zpa_*_application_segment_ba` | `zpa_*_application_segment_pra` |
| Client requirement | ZCC | Browser only | Browser only (via PRA portal) |
| Per-app config block | none | `common_apps_dto.apps_config` (per domain) | `common_apps_dto.apps_config` (per RDP/SSH target) |
| Per-app `application_protocol` | n/a | `HTTP` / `HTTPS` | **`RDP` / `SSH`** |
| Per-app TLS cert | n/a | `certificate_id` required | n/a |
| RDP-only field | n/a | n/a | `connection_security` (`ANY`, `NLA`, `NLA_EXT`, `TLS`, `VM_CONNECT`, `RDP`) |
| Auto-injected `app_types` | n/a | `BROWSER_ACCESS` | `SECURE_REMOTE_ACCESS` |
| Update-diff field | n/a | `deleted_ba_apps` | `deleted_pra_apps` |
| Auth to the target | client supplies creds | n/a (web SSO) | **PRA credential** (managed as `pra_credential`) bound to the user via the access policy |
| Portal | n/a | n/a | **PRA portal** (`pra_portal`) — the URL users connect to |
| Typical port | any TCP/UDP | TCP 443 / 80 | **TCP+UDP 3389** (RDP) or **TCP 22** (SSH) |
| Access-policy operand type | `APP` | `APP` | `APP` — same |

The biggest source of PRA onboarding mistakes:

1. Forgetting to create / select a **PRA portal** users will connect to.
2. Forgetting to create / select a **PRA credential** for the target host.
3. Putting `connection_security` on an SSH app — it's RDP-only.
4. Forgetting that the same domain in `apps_config[].domain` must also appear in the segment's `domain_names`.

The `zpa_create_application_segment_pra` tool validates #3 and #4 client-side.

---

## Workflow

Follow this 8-step process for complete PRA application onboarding.

### Step 1: Gather Application Details

Collect the following from the administrator:

**Required:**

- Application name (e.g. "DC1 Jump Hosts", "Linux Bastions")
- One or more target host FQDNs / IPs (e.g. `rdp01.acme.com`, `bastion.acme.com`)
- Protocol per target: `RDP` or `SSH`
- Port per target (almost always `3389` for RDP, `22` for SSH)
- For RDP targets: desired `connection_security` mode — `ANY` is the safe default, `NLA` if Network Level Authentication is required
- Who should have access (users, groups, or departments)
- The credential users will authenticate to the target with (username + secret)

**Optional:**

- Description and purpose of the application
- Geographic location of the target servers
- Whether to reuse existing ZPA resources (connector groups, server groups, segment groups, PRA portals, PRA credentials)
- Health check requirements

If the admin says "I want users to RDP/SSH to my servers without installing anything" — this is PRA. If they say "I want users on ZCC to reach an internal API" — **stop and use `zpa-application_segment-onboard`** instead. If they say "publish my intranet website to the browser" — **stop and use `zpa-application_segment-ba-onboard`** instead.

---

### Step 2: Set Up App Connector Group

Check for existing connector groups or create a new one. The same connector groups are used by regular, BA, and PRA segments — there is no PRA-specific connector group.

**List existing:**

```text
zpa_list_app_connector_groups()
```

**Create if needed:**

```text
zpa_create_app_connector_group(
  name="<location>-Connectors",
  description="Connectors serving <application_name>",
  enabled=True,
  latitude="<lat>",
  longitude="<lon>",
  location="<datacenter_or_office>",
  country_code="<country>"
)
```

The create tool already resolves the tenant's enrollment certificate ID automatically.

Save the connector group `id` for the next step.

---

### Step 3: Set Up Server Group

Check for existing server groups or create a new one.

**List existing:**

```text
zpa_list_server_groups()
```

**Create if needed:**

```text
zpa_create_server_group(
  name="<application_name>-Servers",
  description="Server group for <application_name>",
  app_connector_group_ids=["<connector_group_id>"],
  enabled=True,
  dynamic_discovery=True
)
```

Save the server group `id` for Step 7.

---

### Step 4: Set Up Segment Group

Check for existing segment groups or create a new one.

**List existing:**

```text
zpa_list_segment_groups()
```

**Create if needed:**

```text
zpa_create_segment_group(
  name="<application_grouping>",
  description="Segment group for <application_grouping>",
  enabled=True
)
```

Save the segment group `id` for Step 7.

---

### Step 5: Set Up the PRA Credential

A PRA credential carries the username + secret used to authenticate the user **into the RDP/SSH target host**. PRA brokers the connection but the target still needs a real OS-level credential.

**List existing PRA credentials:**

```text
zpa_list_pra_credentials()
```

Pick one if a suitable shared credential already exists (e.g. an Active Directory service account that can RDP to all jump hosts, or a sudo-capable user on the SSH bastions).

**Create if needed:**

```text
zpa_create_pra_credential(
  name="<descriptive-name>",
  description="<purpose>",
  credential_type="USERNAME_PASSWORD",  # or PASSWORD, SSH_KEY, etc.
  user_domain="<AD_domain_if_RDP>",
  username="<account>",
  password="<secret>"
)
```

Save the credential `id` for Step 8 (it gets referenced by the access policy rule, NOT by the segment itself).

> **Note:** Don't put real secrets into a chat. Confirm the credential storage path with the admin and have them create or paste the secret directly into the tenant if needed.

---

### Step 6: Set Up the PRA Portal

A PRA portal is the URL endpoint users navigate to in their browser to launch a PRA session. One portal can serve many PRA segments; reuse an existing portal if one already exists.

**List existing PRA portals:**

```text
zpa_list_pra_portals()
```

**Create if needed:**

```text
zpa_create_pra_portal(
  name="<portal-name>",
  domain="<portal.example.com>",
  enabled=True,
  certificate_id="<ba_or_pra_tls_certificate_id>",
  user_notification_enabled=True,
  user_notification="Welcome to <company> Privileged Remote Access"
)
```

The portal needs a TLS certificate covering its `domain` (look up via `zpa_list_ba_certificates` — BA certs and PRA portal certs come from the same store).

Save the portal `id` for Step 8 (also referenced by the access policy rule).

---

### Step 7: Create the PRA Application Segment

This is the PRA-specific segment step. The `apps_config` block is **required** and must list one entry per RDP/SSH target. Every `apps_config[].domain` must also appear in `domain_names`.

**RDP example** (most common — TCP 3389 + UDP 3389):

```text
zpa_create_application_segment_pra(
  name="DC1 RDP Jumpboxes",
  description="Windows jump hosts in DC1",
  enabled=True,
  segment_group_id="<segment_group_id>",
  server_group_ids=["<server_group_id>"],
  domain_names=["rdp01.acme.com", "rdp02.acme.com"],
  tcp_port_range=[{"from": "3389", "to": "3389"}],
  udp_port_range=[{"from": "3389", "to": "3389"}],
  apps_config=[
    {
      "name": "rdp01",
      "domain": "rdp01.acme.com",
      "application_port": "3389",
      "application_protocol": "RDP",
      "connection_security": "ANY",
      "enabled": True
    },
    {
      "name": "rdp02",
      "domain": "rdp02.acme.com",
      "application_port": "3389",
      "application_protocol": "RDP",
      "connection_security": "ANY",
      "enabled": True
    }
  ],
  bypass_type="NEVER",
  health_check_type="DEFAULT",
  health_reporting="ON_ACCESS"
)
```

**SSH example** (TCP 22 only — no UDP, no `connection_security`):

```text
zpa_create_application_segment_pra(
  name="Linux Bastions",
  description="SSH bastion hosts",
  enabled=True,
  segment_group_id="<segment_group_id>",
  server_group_ids=["<server_group_id>"],
  domain_names=["bastion.acme.com"],
  tcp_port_range=[{"from": "22", "to": "22"}],
  apps_config=[
    {
      "name": "bastion",
      "domain": "bastion.acme.com",
      "application_port": "22",
      "application_protocol": "SSH",
      "enabled": True
    }
  ]
)
```

**Hard rules enforced client-side by the tool:**

- Every `apps_config[].domain` MUST appear in `domain_names`.
- `application_protocol` MUST be `"RDP"` or `"SSH"`.
- `connection_security` is **RDP-only** — supplying it on an SSH app is rejected. Allowed values: `ANY`, `NLA`, `NLA_EXT`, `TLS`, `VM_CONNECT`, `RDP`.
- Required per-app keys: `name`, `domain`, `application_port`, `application_protocol`.
- At least one of `tcp_port_range` / `tcp_port_ranges` / `udp_port_range` / `udp_port_ranges` must be supplied.

Save the segment `id` for Step 8.

---

### Step 8: Create the Access Policy Rule

Grant access to the PRA segment, binding the PRA credential and PRA portal to the rule.

**Look up the requesting principals:**

```text
zpa_list_segment_groups()        # confirm segment group ID
zpa_list_user_groups()            # for group-based access
zpa_list_idp()                    # find the IDP backing the criteria
zpa_list_scim_groups(idp_id="<idp_id>")  # for SCIM group-based criteria
```

**Create the access rule:**

```text
zpa_create_access_policy_rule(
  name="Allow <user_group> to <application_name> (PRA)",
  description="Privileged Remote Access for <application_name>",
  action="ALLOW",
  conditions=[
    {
      "operands": [
        {"object_type": "APP", "values": ["<pra_segment_id>"]}
      ]
    },
    {
      "operands": [
        {
          "object_type": "SCIM_GROUP",
          "entry_values": [
            {"rhs": "<scim_group_id>", "lhs": "<idp_id>"}
          ]
        }
      ]
    }
  ],
  credential_id="<pra_credential_id>",
  console_ids=["<pra_portal_id>"]
)
```

The operand type for a PRA segment is the same `APP` operand used for regular and BA segments — the policy engine doesn't distinguish. The PRA-specific binding lives in `credential_id` (which credential to inject into the session) and `console_ids` (which portal to launch the session from).

---

## Validation

After completion, confirm:

**Resource creation:**

```text
zpa_get_application_segment_pra(segment_id="<pra_segment_id>")
zpa_get_segment_group(group_id="<segment_group_id>")
zpa_get_server_group(group_id="<server_group_id>")
zpa_get_app_connector_group(group_id="<connector_group_id>")
zpa_get_pra_credential(credential_id="<pra_credential_id>")
zpa_get_pra_portal(portal_id="<pra_portal_id>")
```

The `get_application_segment_pra` response should include `common_apps_dto.apps_config` populated with each RDP/SSH target, port, protocol, and (for RDP) `connection_security`.

**End-to-end test:**

1. From a browser belonging to a user covered by the access policy, navigate to the PRA portal URL.
2. The user is challenged through the IDP (SAML/OIDC) — **not** ZCC.
3. After auth, the portal lists the published PRA apps the user has access to.
4. Clicking an app launches an in-browser RDP/SSH session, with the PRA credential injected automatically.

---

## Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `apps_config[N].domain '...' is not present in the segment's domain_names` | Domain typo or omission | Make sure every domain in `apps_config` is also in `domain_names` |
| `apps_config[N].connection_security is only valid when application_protocol == 'RDP'` | Supplied `connection_security` on an SSH app | Drop `connection_security` for SSH entries |
| API returns generic `INVALID_INPUT` on create | Wrong `application_protocol` | Use literally `"RDP"` or `"SSH"` (uppercase) |
| RDP session opens but immediately disconnects | `connection_security` mismatch with target | Try `ANY` first; switch to `NLA` only if the target requires it |
| Portal loads but lists no apps | Access policy missing `APP` operand for this segment | Re-check the rule's `conditions` |
| Portal launches the app but auth to the target fails | Wrong / missing PRA credential on the rule | Verify `credential_id` on the access policy rule and the credential's stored secret |
| Portal URL shows TLS warning | Wrong / missing certificate on the PRA portal | Re-check `certificate_id` on the portal covers the portal's `domain` |
| Update silently dropped a published RDP/SSH target | Supplied `apps_config` omitted a domain that previously existed | The SDK auto-deletes PRA apps whose domain is no longer in `apps_config`. Re-include any domain you want to keep. |
| User connects but UDP RDP doesn't work | Forgot to add UDP 3389 alongside TCP 3389 | Add `udp_port_range=[{"from": "3389", "to": "3389"}]` |

---

## Related Skills

- `zpa-application_segment-onboard` — onboard a regular (client-routed) application segment.
- `zpa-application_segment-ba-onboard` — onboard a Browser Access (clientless web) application segment.
- `zpa-create-server-group` — focused workflow for just the server group step.
- `zpa-create-access-policy-rule` — focused workflow for just the policy rule step.

---

## Tool Reference

This skill uses:

- `zpa_list_app_connector_groups`, `zpa_create_app_connector_group`, `zpa_get_app_connector_group`
- `zpa_list_server_groups`, `zpa_create_server_group`, `zpa_get_server_group`
- `zpa_list_segment_groups`, `zpa_create_segment_group`, `zpa_get_segment_group`
- `zpa_list_pra_credentials`, `zpa_create_pra_credential`, `zpa_get_pra_credential`
- `zpa_list_pra_portals`, `zpa_create_pra_portal`, `zpa_get_pra_portal`
- `zpa_list_ba_certificates` (for the PRA portal's TLS cert)
- `zpa_list_application_segments_pra`, `zpa_create_application_segment_pra`, `zpa_get_application_segment_pra`, `zpa_update_application_segment_pra`
- `zpa_list_user_groups`, `zpa_list_idp`, `zpa_list_scim_groups`
- `zpa_create_access_policy_rule`
