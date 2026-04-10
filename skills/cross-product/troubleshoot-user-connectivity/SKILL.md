---
name: cross-product-troubleshoot-user-connectivity
description: "Cross-product troubleshooting of user connectivity issues spanning ZPA, ZIA, ZDX, and ZCC. Investigates end-to-end: (1) ZCC client status and enrollment, (2) ZDX digital experience scores and metrics, (3) ZPA application segment and access policy configuration, (4) ZIA URL filtering and SSL inspection policies. Use when an administrator reports 'user cannot access application', 'connectivity issues', or 'application is slow.'"
---

# Cross-Product: Troubleshoot User Connectivity

## Keywords

troubleshoot connectivity, user cannot access, application slow, connection failed, access denied, zpa not working, connectivity issue, application unreachable, user experience poor, latency, timeout, cross product troubleshoot

## Overview

Perform end-to-end troubleshooting of user connectivity issues by correlating data across multiple Zscaler services: ZCC (client status), ZDX (digital experience metrics), ZPA (private application access), and ZIA (internet access policies). This skill systematically eliminates potential causes from the client device through to the application.

**Use this skill when:** An administrator reports that a user cannot access an application, is experiencing slow performance, or encounters intermittent connectivity issues.

---

## Workflow

Follow this 7-step process for systematic cross-product troubleshooting.

### Step 1: Gather Issue Details

Collect from the administrator:

**Required:**

- User name or email
- Application or URL they are trying to access
- Symptom: cannot connect, slow, intermittent, timeout, access denied

**Helpful:**

- When did the issue start?
- Is it affecting one user or multiple users?
- Which device (laptop, mobile)?
- Error message if any

---

### Step 2: Check ZCC Client Status

Verify the user's Zscaler Client Connector is enrolled and healthy.

```text
zcc_list_devices(search="<username_or_email>")
```text

**Check for:**

- Device enrollment status (enrolled, pending, removed)
- ZCC version -- is it up to date?
- Last seen timestamp -- is the device recently active?
- OS type and version

If multiple devices are returned, ask the administrator which device is affected.

**If device not found:**

```text
The user's device is not enrolled in Zscaler Client Connector.

Possible causes:
- ZCC is not installed
- ZCC is not signed in
- Device was recently re-imaged
- User is connecting without ZCC (direct internet)

Action: Verify ZCC installation and sign-in on the user's device.
```text

**Check forwarding profiles and trusted networks:**

```text
zcc_list_forwarding_profiles()
zcc_list_trusted_networks()
```text

Verify the user's traffic is being forwarded through Zscaler (not bypassed due to a trusted network detection or forwarding profile exception).

---

### Step 3: Check ZDX Digital Experience

If ZDX is available, check the user's application experience scores.

**Check user's device:**

```text
zdx_list_devices(search="<username>")
```text

Note the device ID, then check application metrics:

```text
zdx_get_device(device_id="<device_id>")
```text

**Check application scores:**

```text
zdx_list_applications()
zdx_get_application_score_trend(app_id="<app_id>")
```text

**Check for active alerts:**

```text
zdx_list_alerts()
```text

**Evaluate ZDX data:**

- **Score > 80:** Good experience -- issue is likely policy-based, not performance
- **Score 50-80:** Degraded -- check network path and application health
- **Score < 50:** Poor -- significant performance issue, check hop-by-hop metrics
- **No data:** User/application not monitored by ZDX

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="dns_time"
)
```text

Check key metrics:

- DNS resolution time
- TCP connect time
- SSL handshake time
- Server response time
- Page load time (for web apps)

---

### Step 4: Check ZPA Configuration (for private applications)

If the application is accessed via ZPA (internal/private app):

**Find the application segment:**

```text
zpa_list_application_segments()
```text

Search for the application by name or domain. Verify:

- Application segment exists for the target domain
- It is enabled
- Domain names match what the user is accessing
- Correct ports are configured

**Check the server group:**

```text
zpa_get_application_segment(segment_id="<id>")
```text

Note the `server_group_ids`, then:

```text
zpa_get_server_group(group_id="<server_group_id>")
```text

Verify:

- Server group is enabled
- App connector group IDs are present and valid

**Check app connector health:**

```text
zpa_list_app_connectors(search="<connector_name>")
zpa_get_app_connector(connector_id="<connector_id>")
```text

Verify connectors show `runtime_status` = `ZPN_STATUS_AUTHENTICATED`.

**Check connector group settings:**

```text
zpa_get_app_connector_group(group_id="<connector_group_id>")
```text

**Check access policy:**

```text
zpa_list_access_policy_rules()
```text

Walk through rules to determine if the user is granted access:

- Does a rule exist that includes the user, their group, or their department?
- Is the action set to ALLOW?
- Are there any DENY rules at higher priority that might block?

**Check identity attributes:**

```text
get_zpa_scim_group(search="<user_group>")
get_zpa_saml_attribute(search="<attribute>")
```text

---

### Step 5: Check ZIA Configuration (for internet applications)

If the application is accessed via ZIA (internet/SaaS app):

**Classify the URL:**

```text
zia_url_lookup(urls=["<application_url>"])
```text

**Check URL filtering rules:**

```text
zia_list_url_filtering_rules()
```text

Evaluate rules in order for the user's groups/department (see "check-user-url-access" skill for detailed methodology).

**Check SSL inspection:**

```text
zia_list_ssl_inspection_rules()
```text

SSL inspection issues can cause certificate errors or connectivity failures for apps with certificate pinning.

**Check cloud firewall:**

```text
zia_list_cloud_firewall_rules()
```text

Look for rules that might block the application's ports or protocols.

---

### Step 6: Check for Broader Issues

**Check if the issue affects multiple users:**

```text
zdx_list_alert_affected_devices(alert_id="<alert_id>")
```text

**Check ZDX for application-level issues:**

```text
zdx_list_alerts()
```text

If active alerts exist for the application, this may be an application-side issue rather than a Zscaler policy issue.

**Check ZIA activation status:**

```text
zia_get_activation_status()
```text

If configuration changes were made recently but not activated, policies may be out of sync.

---

### Step 7: Present Diagnosis

#### Report Format

```text
Connectivity Troubleshooting Report
=====================================

**User:** John Smith (john.smith@company.com)
**Application:** internal-app.company.com (port 443)
**Symptom:** Cannot connect / Slow / Access denied
**Device:** MacBook Pro (macOS 14.2), ZCC v4.2.1

---

## Diagnosis: <ROOT CAUSE IDENTIFIED>

---

## Investigation Steps

### 1. ZCC Client Status: OK
- Device enrolled and active
- ZCC version current
- Last seen: 2 minutes ago
- Traffic forwarding: Active (not on trusted network)

### 2. ZDX Experience: DEGRADED (Score: 45)
- DNS resolution: 250ms (normally 15ms)
- TCP connect: 1200ms (normally 80ms)
- Server response: Timeout
- Network path: Packet loss detected at hop 5

### 3. ZPA Configuration: OK
- Application segment "Internal App" exists and is enabled
- Domain: internal-app.company.com, Port: 443
- Server group: "US-East Servers" (enabled, 2 connectors healthy)
- Access policy: "Allow Engineering" grants access to user's group

### 4. ZIA Policies: N/A (private application via ZPA)

### 5. Broader Impact:
- ZDX Alert: "High Latency - US-East Datacenter" (active since 2h ago)
- 12 other users affected by same alert
- Application-side issue suspected

---

## Root Cause

The ZDX metrics show elevated DNS and TCP connection times, with packet
loss at hop 5 in the network path. An active ZDX alert confirms this
is affecting 12+ users accessing applications via the US-East datacenter.

This is a network infrastructure issue, not a Zscaler policy issue.

---

## Recommended Actions

1. **Immediate:** Check network connectivity to US-East datacenter
2. **Immediate:** Review hop 5 (ISP transit) for known outages
3. **Workaround:** If available, temporarily route traffic through
   US-West connectors by updating the server group
4. **Follow-up:** Monitor ZDX alert for resolution
```text

---

## Common Root Causes and Quick Checks

| Symptom | Likely Cause | Quick Check |
|---------|-------------|------------|
| "Access denied" | ZPA access policy | `zpa_list_access_policy_rules()` |
| "Site blocked" | ZIA URL filtering | `zia_list_url_filtering_rules()` |
| "Certificate error" | SSL inspection | `zia_list_ssl_inspection_rules()` |
| "Timeout" | Connector/network | `zdx_get_application_metric()` |
| "Slow" | Network path | `zdx_get_application_score_trend()` |
| "Intermittent" | DNS or routing | `zdx_get_application_metric(metric_name="dns_time")` |
| "Works on VPN, not ZPA" | Missing app segment | `zpa_list_application_segments()` |
| "Works for others" | User-specific policy | `zpa_list_access_policy_rules()` + user lookup |

---

## Edge Cases

### Application Not in ZPA or ZIA

```text
The application "<domain>" was not found in:
- ZPA application segments
- ZIA URL categories

Possible causes:
- The application has not been onboarded to ZPA yet
  → Use the "onboard-application" ZPA skill to set it up
- The domain name the user is accessing differs from what's configured
  → Verify the exact URL the user is trying to reach
- DNS resolution is pointing to a different host
```text

### Multiple Possible Causes

Present all findings and let the administrator prioritize:

```text
Multiple potential issues found:

1. [LIKELY] ZPA access policy does not include user's group
2. [POSSIBLE] ZDX shows elevated latency (but not timeout-level)
3. [UNLIKELY] SSL inspection rule exists but is for a different category

Recommended investigation order: Start with #1 (access policy).
```text

---

## When NOT to Use This Skill

- Just creating an application (not troubleshooting) -- use "onboard-application" ZPA skill
- Auditing SSL rules (not user-specific) -- use "audit-ssl-inspection-bypass" ZIA skill
- Investigating a URL category broadly -- use "investigate-url-category" ZIA skill
- Checking only ZIA policy for a user -- use "check-user-url-access" ZIA skill

---

## Quick Reference

**Primary workflow:** Gather Info → ZCC Status → ZDX Metrics → ZPA Config → ZIA Policies → Broader Issues → Diagnosis

**ZCC tools:**

- `zcc_list_devices(search)` -- device enrollment and status
- `zcc_list_forwarding_profiles()` -- traffic forwarding config
- `zcc_list_trusted_networks()` -- trusted network bypass check

**ZDX tools:**

- `zdx_list_devices(search)` -- find user's device
- `zdx_get_device(device_id)` -- device details
- `zdx_list_applications()` -- list monitored apps
- `zdx_get_application_score_trend(app_id)` -- experience scores
- `zdx_get_application_metric(app_id, metric_name)` -- detailed metrics
- `zdx_list_alerts()` -- active alerts

**ZPA tools:**

- `zpa_list_application_segments()` -- find the application
- `zpa_get_application_segment(segment_id)` -- app details
- `zpa_get_server_group(group_id)` -- server group health
- `zpa_list_app_connectors(search)` -- list connectors with runtime status
- `zpa_get_app_connector(connector_id)` -- individual connector health
- `zpa_get_app_connector_group(group_id)` -- connector group settings
- `zpa_list_access_policy_rules()` -- access policy evaluation

**ZIA tools:**

- `zia_url_lookup(urls)` -- classify URL
- `zia_list_url_filtering_rules()` -- URL policy
- `zia_list_ssl_inspection_rules()` -- SSL policy
- `zia_list_cloud_firewall_rules()` -- firewall policy
- `zia_get_activation_status()` -- check pending changes
