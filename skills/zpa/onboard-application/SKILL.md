---
name: zpa-onboard-application
description: "End-to-end onboarding of a new application in Zscaler Private Access. Walks through the complete dependency chain: (1) App connector group, (2) Server group, (3) Segment group, (4) Application segment with domain names and ports, (5) Access policy rule to grant user/group access. Use when an administrator needs to make an internal application accessible through ZPA."
---

# ZPA: Onboard Application

## Keywords

onboard application, new application, add application, zpa application, publish application, application segment, private access, zpa setup, application access, zero trust application

## Overview

Onboard a new application in Zscaler Private Access by walking through the full resource dependency chain. This skill creates all required ZPA constructs -- from connector groups to access policies -- ensuring the application is reachable and properly secured.

**Use this skill when:** An administrator wants to make a new internal application accessible through ZPA, or needs a guided walkthrough of the full ZPA application onboarding process.

---

## Workflow

Follow this 7-step process for complete application onboarding.

### Step 1: Gather Application Details

Collect the following from the administrator:

**Required:**

- Application name
- Domain name(s) or IP address(es) the application runs on
- TCP and/or UDP port(s) (e.g., 443, 80, 8080, 3389)
- Who should have access (users, groups, or departments)

**Optional:**

- Description and purpose of the application
- Geographic location of the application servers
- Whether to reuse existing ZPA resources (connector groups, server groups, segment groups)
- Health check requirements
- Whether CNAME resolution is needed

---

### Step 2: Set Up App Connector Group

Check for existing connector groups or create a new one.

**List existing:**

```text
zpa_list_app_connector_groups()
```text

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
```text

Save the connector group `id` for the next step.

---

### Step 3: Set Up Server Group

Check for existing server groups or create a new one.

**List existing:**

```text
zpa_list_server_groups()
```text

**Create if needed:**

```text
zpa_create_server_group(
  name="<application_name>-Servers",
  description="Server group for <application_name>",
  app_connector_group_ids=["<connector_group_id>"],
  enabled=True,
  dynamic_discovery=True
)
```text

Save the server group `id` for Step 5.

---

### Step 4: Set Up Segment Group

Segment groups logically organize application segments. Check for an existing one or create a new one.

**List existing:**

```text
zpa_list_segment_groups()
```text

**Create if needed:**

```text
zpa_create_segment_group(
  name="<application_name>-Segment-Group",
  description="Segment group for <application_name>",
  enabled=True
)
```text

Save the segment group `id` for the next step.

---

### Step 5: Create Application Segment

This is the core resource that defines the application's reachability.

```text
zpa_create_application_segment(
  name="<application_name>",
  description="<description>",
  segment_group_id="<segment_group_id>",
  domain_names=["app.internal.example.com"],
  tcp_port_range=[{"from": "443", "to": "443"}, {"from": "80", "to": "80"}],
  server_group_ids=["<server_group_id>"],
  enabled=True,
  health_reporting="ON_ACCESS",
  is_cname_enabled=True
)
```text

**Port configuration options:**

For single ports:

```text
tcp_port_range=[{"from": "443", "to": "443"}]
```text

For port ranges:

```text
tcp_port_range=[{"from": "8000", "to": "8999"}]
```text

For UDP (e.g., DNS):

```text
udp_port_range=[{"from": "53", "to": "53"}]
```text

For mixed TCP+UDP:

```text
tcp_port_range=[{"from": "443", "to": "443"}],
udp_port_range=[{"from": "53", "to": "53"}]
```text

Save the application segment `id` for the access policy.

---

### Step 6: Create Access Policy Rule

Grant access to the application for specific users or groups.

First, look up the identity entities to reference in the policy:

```text
get_zpa_scim_group(search="<group_name>")
get_zpa_saml_attribute(search="<attribute_name>")
```text

Then create the access policy rule:

```text
zpa_create_access_policy_rule(
  name="Allow <group> to <application_name>",
  description="Grants <group> access to <application_name>",
  action_type="ALLOW",
  conditions={
    "operands": [
      {
        "objectType": "APP",
        "values": ["<application_segment_id>"]
      },
      {
        "objectType": "SCIM_GROUP",
        "values": ["<scim_group_id>"]
      }
    ]
  }
)
```text

**Common action types:**

- `ALLOW` -- permit access
- `DENY` -- block access
- `REQUIRE_APPROVAL` -- require explicit approval before access

---

### Step 7: Verify and Summarize

Verify each resource was created correctly:

```text
zpa_get_app_connector_group(group_id="<id>")
zpa_get_server_group(group_id="<id>")
zpa_get_segment_group(group_id="<id>")
zpa_get_application_segment(segment_id="<id>")
zpa_get_access_policy_rule(rule_id="<id>")
```text

#### Present Summary

```text
Application onboarding complete.

**Application:** <name>
- Domains: app.internal.example.com
- Ports: TCP 443, TCP 80
- Health Reporting: ON_ACCESS

**Infrastructure:**
- App Connector Group: <name> (ID: <id>)
- Server Group: <name> (ID: <id>)
- Segment Group: <name> (ID: <id>)

**Access Policy:**
- Rule: Allow <group> to <name>
- Action: ALLOW
- Granted To: <group_name>

**Resource Dependency Map:**
  App Connector Group ─► Server Group ─► Application Segment ◄─ Segment Group
                                                  │
                                                  ▼
                                         Access Policy Rule

**What happens next:**
1. Users in <group> can now reach <domain> on port(s) <ports> through ZPA
2. Traffic flows: User → ZPA Cloud → App Connector → Application Server
3. Monitor access in ZPA Admin Portal or via ZDX
```text

---

## Common Application Templates

### Web Application (HTTPS)

```text
domain_names=["webapp.internal.corp.com"]
tcp_port_range=[{"from": "443", "to": "443"}]
health_reporting="ON_ACCESS"
is_cname_enabled=True
```text

### Remote Desktop (RDP)

```text
domain_names=["rdp-server.internal.corp.com"]
tcp_port_range=[{"from": "3389", "to": "3389"}]
```text

### SSH Access

```text
domain_names=["bastion.internal.corp.com"]
tcp_port_range=[{"from": "22", "to": "22"}]
```text

### Database Access (PostgreSQL + MySQL)

```text
domain_names=["db.internal.corp.com"]
tcp_port_range=[{"from": "5432", "to": "5432"}, {"from": "3306", "to": "3306"}]
```text

### Multi-Service Application

```text
domain_names=["api.internal.corp.com", "web.internal.corp.com", "ws.internal.corp.com"]
tcp_port_range=[{"from": "80", "to": "80"}, {"from": "443", "to": "443"}, {"from": "8080", "to": "8443"}]
```text

---

## Edge Cases

### Reusing All Existing Resources

If the admin wants to add an application to existing infrastructure, skip Steps 2-4 and jump to Step 5 with existing IDs:

```text
zpa_list_server_groups()
zpa_list_segment_groups()

zpa_create_application_segment(
  name="New App",
  segment_group_id="<existing_segment_group_id>",
  server_group_ids=["<existing_server_group_id>"],
  domain_names=["newapp.internal.corp.com"],
  tcp_port_range=[{"from": "443", "to": "443"}]
)
```text

### Wildcard Domains

For applications with many subdomains:

```text
domain_names=["*.internal.corp.com"]
```text

### Multiple Access Policies

Create separate rules for different access levels:

```text
zpa_create_access_policy_rule(
  name="Admin Access - Full",
  action_type="ALLOW",
  conditions={...admin_conditions...}
)

zpa_create_access_policy_rule(
  name="Developer Access - Read Only Ports",
  action_type="ALLOW",
  conditions={...dev_conditions...}
)
```text

---

## When NOT to Use This Skill

- Modifying an existing application -- use individual update tools instead
- Just creating a server group -- use the "create-server-group" skill
- Troubleshooting connectivity -- use the "troubleshoot-user-connectivity" cross-product skill
- Listing or auditing existing applications -- use `zpa_list_application_segments()` directly

---

## Quick Reference

**Full dependency chain:**

1. `zpa_create_app_connector_group` (or reuse existing)
2. `zpa_create_server_group` (requires connector group IDs)
3. `zpa_create_segment_group` (or reuse existing)
4. `zpa_create_application_segment` (requires segment group ID + server group IDs)
5. `zpa_create_access_policy_rule` (references application segment)

**Verification tools:**

- `zpa_get_app_connector_group(group_id)`
- `zpa_get_server_group(group_id)`
- `zpa_get_segment_group(group_id)`
- `zpa_get_application_segment(segment_id)`
- `zpa_get_access_policy_rule(rule_id)`

**Identity lookup tools:**

- `get_zpa_scim_group(search)` -- find SCIM groups for policy conditions
- `get_zpa_saml_attribute(search)` -- find SAML attributes for policy conditions
