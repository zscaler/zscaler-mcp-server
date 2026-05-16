---
name: zpa-application_segment-ba-onboard
description: "End-to-end onboarding of a new Browser Access (BA) application in Zscaler Private Access. Walks through the full dependency chain — App connector group, server group, segment group, BA TLS certificate, BA application segment with apps_config, and access policy rule — for web apps that should be reachable through the browser without Zscaler Client Connector. Use only when the admin explicitly asks for Browser Access. DO NOT USE WHEN: the admin wants a regular client-routed application segment (use zpa-application_segment-onboard instead)."
---

# ZPA: Onboard Browser Access Application

## Keywords

browser access, ba application, clientless access, agentless zpa, web app publish, browser-only application, onboard browser access, no client connector, agentless access, ba app segment

## Overview

Onboard a new **Browser Access (BA)** application in Zscaler Private Access. BA segments publish web applications to authorized users through the browser, without requiring Zscaler Client Connector. This skill walks through the full dependency chain — connector group → server group → segment group → **BA TLS certificate** → **BA application segment with `apps_config`** → access policy rule.

**Use this skill when:** The admin explicitly mentions Browser Access, agentless access, clientless ZPA, or publishing a web app to users who do not have ZCC installed.

**DO NOT use this skill when:**

- The admin wants a regular client-routed application segment (any TCP/UDP app reachable via ZCC) — use `zpa-application_segment-onboard` instead.
- The admin asks about Privileged Remote Access (PRA) for SSH/RDP — that is a separate flow.

---

## What makes BA different from a regular app segment

| Concept | Regular segment | Browser Access segment |
|---|---|---|
| SDK / tool family | `zpa_*_application_segment` | `zpa_*_application_segment_ba` |
| Client requirement | ZCC required | Browser only |
| Per-app config block | none | **`common_apps_dto.apps_config` is required** |
| Per-app TLS cert | n/a | every published domain needs a `certificate_id` (a BA cert) |
| Typical ports | any TCP/UDP | almost always TCP 443 (HTTPS) or 80 (HTTP) |
| Access policy operand type | `APP` (segment ID) | `APP` (segment ID) — same |

The single biggest source of BA onboarding failures is forgetting one of:

1. The BA TLS certificate (`certificate_id`) for each published domain.
2. Listing the same domain in **both** the segment's `domain_names` and inside `apps_config[].domain`.

Both are validated client-side by `zpa_create_application_segment_ba` so the API doesn't have to.

---

## Workflow

Follow this 7-step process for complete BA application onboarding.

### Step 1: Gather Application Details

Collect the following from the administrator:

**Required:**

- Application name
- One or more public-facing domain names users will type into the browser (e.g. `hr.acme.com`, `intranet.acme.com`)
- Protocol per domain: `HTTP` or `HTTPS`
- Port per domain (almost always `443` for HTTPS, `80` for HTTP)
- Who should have access (users, groups, or departments)

**Optional:**

- Description and purpose of the application
- Geographic location of the application servers
- Whether to reuse existing ZPA resources (connector groups, server groups, segment groups, BA certificates)
- Health check requirements
- Whether CNAME resolution is needed

If the admin says "I want to publish X to the browser without installing the client" — this is BA. If they say "I want users on ZCC to reach X" — this is the regular flow, **stop and use `zpa-application_segment-onboard`**.

---

### Step 2: Set Up App Connector Group

Check for existing connector groups or create a new one. The same connector groups are used by regular and BA segments — there is no BA-specific connector group.

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

The create tool already resolves the tenant's enrollment certificate ID automatically — no manual lookup needed.

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

Save the server group `id` for Step 6.

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

Save the segment group `id` for Step 6.

---

### Step 5: Look Up the BA TLS Certificate

Browser Access requires a **BA TLS certificate** per published domain (typically a wildcard cert covering the domain). This is the certificate the user's browser sees when they navigate to the published URL.

**List existing BA certificates:**

```text
zpa_list_ba_certificates()
```

Pick the cert whose Subject / SAN covers the domain(s) the admin wants to publish (e.g. a `*.acme.com` cert covers `hr.acme.com` and `intranet.acme.com`).

**If no suitable cert exists**, ask the admin for the cert + private key in PEM format and create one:

```text
zpa_create_ba_certificate(
  name="<short-cert-name>",
  cert_blob="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
)
```

Save the certificate `id` — every entry in `apps_config` will reference it (or a different cert, if different domains use different certs).

**Reusing one cert across multiple domains is normal** when the cert is a wildcard or has multi-SAN coverage. Each `apps_config[].certificate_id` can point to the same cert.

---

### Step 6: Create the Browser Access Application Segment

This is the BA-specific step. The `apps_config` block is **required** and must list one entry per domain in `domain_names`.

```text
zpa_create_application_segment_ba(
  name="<application_name>",
  description="<purpose>",
  enabled=True,
  segment_group_id="<segment_group_id>",
  server_group_ids=["<server_group_id>"],
  domain_names=["hr.acme.com", "intranet.acme.com"],
  tcp_port_range=[{"from": "443", "to": "443"}],
  apps_config=[
    {
      "domain": "hr.acme.com",
      "application_port": "443",
      "application_protocol": "HTTPS",
      "certificate_id": "<ba_certificate_id>"
    },
    {
      "domain": "intranet.acme.com",
      "application_port": "443",
      "application_protocol": "HTTPS",
      "certificate_id": "<ba_certificate_id>"
    }
  ],
  bypass_type="NEVER",
  health_check_type="DEFAULT",
  health_reporting="ON_ACCESS",
  is_cname_enabled=True
)
```

**Hard rules enforced client-side by the tool:**

- Every `apps_config[].domain` MUST appear in `domain_names`. The tool rejects mismatches before the API round-trip.
- `application_protocol` MUST be `"HTTP"` or `"HTTPS"`.
- `application_port`, `domain`, `application_protocol`, and `certificate_id` are all required per app.
- At least one of `tcp_port_range` / `tcp_port_ranges` / `udp_port_range` / `udp_port_ranges` must be supplied; for BA this is almost always TCP 443 or 80.

Save the segment `id` for Step 7.

---

### Step 7: Create the Access Policy Rule

Grant access to the BA segment.

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
  name="Allow <user_group> to <application_name> (BA)",
  description="Browser Access for <application_name>",
  action="ALLOW",
  conditions=[
    {
      "operands": [
        {"object_type": "APP", "values": ["<ba_segment_id>"]}
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
  ]
)
```

The operand type for a BA segment is the same `APP` operand used for regular segments — the policy engine doesn't distinguish.

---

## Validation

After completion, confirm:

**Resource creation:**

```text
zpa_get_application_segment_ba(segment_id="<ba_segment_id>")
zpa_get_segment_group(group_id="<segment_group_id>")
zpa_get_server_group(group_id="<server_group_id>")
zpa_get_app_connector_group(group_id="<connector_group_id>")
```

The `get` response should include `common_apps_dto.apps_config` populated with each domain, port, protocol, and certificate.

**End-to-end test:**

1. From a browser belonging to a user in the access policy, navigate to one of the published domains.
2. The user is challenged through the IDP (SAML/OIDC) — **not** ZCC.
3. After auth, the page loads as if served by the internal app.

---

## Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `apps_config[N].domain '...' is not present in the segment's domain_names` | Domain typo or omission | Make sure every domain in `apps_config` is also in `domain_names` |
| API returns generic `INVALID_INPUT` on create | Wrong `application_protocol` | Use literally `"HTTP"` or `"HTTPS"` (uppercase) |
| Browser shows a TLS warning when users hit the published URL | Wrong / missing BA certificate | Re-check the `certificate_id` covers the published domain (CN or SAN match) |
| 403 / no access despite policy | User isn't in the SCIM/user group | Verify the IDP and group membership; check the policy rule's `conditions` |
| Update silently dropped published apps | Supplied `apps_config` omitted a domain that previously existed | The SDK auto-deletes BA apps whose domain is no longer in `apps_config`. Re-include any domain you want to keep. |
| User sees the app but ZCC also tries to claim the domain | The same domain is also in a regular app segment | A domain may belong to **either** a BA segment or a regular segment, not both. Remove it from one. |

---

## Related Skills

- `zpa-application_segment-onboard` — onboard a regular (client-routed) application segment.
- `zpa-create-server-group` — focused workflow for just the server group step.
- `zpa-create-access-policy-rule` — focused workflow for just the policy rule step.

---

## Tool Reference

This skill uses:

- `zpa_list_app_connector_groups`, `zpa_create_app_connector_group`, `zpa_get_app_connector_group`
- `zpa_list_server_groups`, `zpa_create_server_group`, `zpa_get_server_group`
- `zpa_list_segment_groups`, `zpa_create_segment_group`, `zpa_get_segment_group`
- `zpa_list_ba_certificates`, `zpa_create_ba_certificate`, `zpa_get_ba_certificate`
- `zpa_list_application_segments_ba`, `zpa_create_application_segment_ba`, `zpa_get_application_segment_ba`, `zpa_update_application_segment_ba`
- `zpa_list_user_groups`, `zpa_list_idp`, `zpa_list_scim_groups`
- `zpa_create_access_policy_rule`
