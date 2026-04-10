---
name: zms-troubleshoot-agent-deployment
description: "Troubleshoot Zscaler Microsegmentation (ZMS) agent deployment and connectivity issues. Investigates agent fleet health, connection status, version compliance, agent group configuration, provisioning keys, and TOTP secrets. Use when an administrator reports: 'Agents are disconnected', 'Agent enrollment failing', 'How do I provision new agents?', 'Check agent versions', or 'Agent not connecting.'"
---

# ZMS: Troubleshoot Agent Deployment

## Keywords

agent deployment, agent enrollment, agent disconnected, provisioning key, nonce, TOTP, agent version, agent connectivity, agent group, agent health, microsegmentation agent, agent upgrade, agent troubleshoot

## Overview

Troubleshoot Zscaler Microsegmentation (ZMS) agent deployment, enrollment, and connectivity issues. This skill systematically investigates agent fleet health, identifies disconnected or outdated agents, verifies agent group configuration, checks provisioning key availability, and retrieves enrollment credentials. It covers the full agent lifecycle from initial provisioning through ongoing health monitoring.

The ZMS API is a GraphQL endpoint on OneAPI. The full API supports both Query (read) and Mutation (write) operations for agents, agent groups, and nonces:

- **Query operations** (available via MCP): `agents`, `agentGroups`, `AgentConnectionStatusStatisticsConnection`, `agentVersionStatistics`, `nonces`, `nonce`
- **Mutation operations** (not yet in MCP, available via API/portal): `agentUpdate`, `agentDelete`, `agentGroupCreate/Update/Delete`, `agentGroupUpgradeStatusReset`, `nonceCreate/Update/Delete`, `nonceWithAgentGroupCreate`

**Use this skill when:** An administrator reports agents not connecting, enrollment failures, version mismatches, or needs to set up provisioning for new agent deployments.

**Important:**

- All ZMS tools require `ZSCALER_CUSTOMER_ID` to be set as an environment variable.
- All current MCP tools are **read-only** (Query operations). Write operations (create/update/delete agents, groups, nonces) must be performed through the Zscaler admin portal or the ZMS API directly.
- GraphQL errors may return HTTP 200 with errors in the response body — always check for the `errors` field.

---

## Workflow

Follow this 6-step process to troubleshoot agent deployment.

### Step 1: Identify the Problem

Gather from the administrator:

**Required:**

- What is the symptom? (agent not connecting, enrollment failure, version mismatch, missing agent)
- Which agents or hosts? (hostname, IP, agent group)
- When did the issue start?

**Helpful:**

- Is this a new deployment or an existing agent?
- Cloud provider (AWS, Azure, GCP, on-premises)?
- OS type and version?
- Any recent infrastructure changes?
- Error messages from the agent installer?

---

### Step 2: Check Overall Fleet Health

**Get connection status statistics:**

```text
zms_get_agent_connection_status_statistics()
```text

This provides the fleet-wide overview:

- Total agent count
- Connected vs disconnected counts and percentages
- Per-type and per-status breakdown

**Assess fleet health:**

- **> 95% connected**: Healthy fleet -- issue is likely isolated
- **90-95% connected**: Some connectivity issues -- check network
- **< 90% connected**: Widespread issue -- check infrastructure

**Get version statistics:**

```text
zms_get_agent_version_statistics()
```text

Check for:

- Number of distinct versions in use (should be minimal)
- Agents on deprecated or unsupported versions
- Upgrade rollout progress

---

### Step 3: Find the Specific Agent

**Search for the problematic agent:**

```text
zms_list_agents(search="<hostname_or_ip>", page_size=20)
```text

**If agent is found**, check:

- **connectionStatus**: Is the agent connected, disconnected, or in another state?
- **version**: Is the agent running the latest version?
- **os**: Is the OS supported?
- **ipAddresses**: Are the IP addresses correct for the expected network?
- **agentGroup**: Is the agent in the correct group?
- **lastSeen**: When was the agent last active?

**If agent is NOT found:**

- The agent was never enrolled, or enrollment failed
- The agent may be registered under a different hostname/IP
- Try broader search or list all agents:

```text
zms_list_agents(page=1, page_size=100)
```

---

### Step 4: Verify Agent Group Configuration

**List agent groups:**

```text
zms_list_agent_groups(page=1, page_size=50)
```text

For each group, verify:

- **Type**: Cloud provider type or on-premises
- **Agent count**: Expected number of agents
- **Policy status**: Whether policies are applied to the group
- **Auto-upgrade settings**: Whether agents auto-upgrade
- **Upgrade schedule**: Scheduled upgrade windows
- **Tamper protection**: Whether tamper protection is enabled

**Sort by name for easier navigation:**

```text
zms_list_agent_groups(sort="name", sort_dir="ASC", page_size=50)
```text

**Get TOTP secrets for enrollment (if enrollment is the issue):**

```text
zms_get_agent_group_totp_secrets(eyez_id="<agent_group_eyez_id>")
```text

The TOTP secret is required for agent enrollment. This returns:

- **TOTP secret**: The secret key for generating one-time passwords
- **QR code**: For scanning with an authenticator app
- **Generation timestamp**: When the secret was created

---

### Step 5: Check Provisioning Keys (Nonces)

**List available provisioning keys:**

```text
zms_list_nonces(page=1, page_size=50)
```text

Provisioning keys (nonces) are one-time keys used to register new agents. For each key, check:

- **name**: Descriptive key name
- **value**: The actual provisioning key string
- **maxUsage**: Maximum number of times the key can be used
- **usageCount**: How many times the key has been used
- **agentGroup**: Which agent group the key enrolls agents into
- **productType**: The product type the key is for
- **created/modified**: Key timestamps

**Common provisioning key issues:**

- **Key exhausted**: `usageCount >= maxUsage` -- create a new key (via `nonceCreate` mutation in the API/portal)
- **Wrong agent group**: Key enrolls into the wrong group -- verify with `zms_get_nonce()`
- **Expired key**: Key was created long ago and may have been deactivated
- **Need key + new group**: The API supports `nonceWithAgentGroupCreate` to create both a provisioning key and a new agent group simultaneously (via portal/API only)

**Search for a specific key:**

```text
zms_list_nonces(search="<key_name>")
```text

**Get specific key details:**

```text
zms_get_nonce(eyez_id="<nonce_eyez_id>")
```text

---

### Step 6: Present Diagnosis and Resolution

#### Diagnosis Template

```text
ZMS Agent Deployment Troubleshooting Report
=============================================
Date: <current_date>
Reported by: <administrator>

## Issue Summary

- **Symptom:** <Agent not connecting / Enrollment failing / Version mismatch>
- **Affected:** <hostname(s) / agent group / all agents>
- **Duration:** <Since when>
- **Severity:** <Critical / High / Medium / Low>
- **Status:** <Root cause identified / Investigating>

---

## Fleet Health Overview

| Metric              | Value       | Status     |
|--------------------|------------|-----------|
| Total Agents        | 245        | --         |
| Connected           | 238 (97%)  | Healthy    |
| Disconnected        | 7 (3%)     | 3 expected |
| Agent Versions      | 3 in use   | Review     |
| Latest Version      | v4.2.1     | Target     |

---

## Investigation Results

### Agent Status
- **Hostname:** web-srv-03
- **Connection Status:** DISCONNECTED
- **Last Seen:** 3 days ago
- **Version:** v4.1.8 (OUTDATED -- latest is v4.2.1)
- **OS:** Ubuntu 22.04
- **Agent Group:** Production Web Servers
- **IP Address:** 10.0.1.45

### Agent Group Configuration
- **Group:** Production Web Servers
- **Auto-Upgrade:** Disabled
- **Tamper Protection:** Enabled
- **Policy Status:** Active
- **Agent Count:** 12

### Provisioning Key Status
- **Available Keys:** 3
- **"Prod Web Key":** 45/50 used (90% -- nearing limit)
- **"Staging Key":** 12/100 used (12% -- available)

---

## Root Cause

<Describe the identified root cause>

Examples:
- Agent disconnected due to network configuration change on the host
- Enrollment failing because provisioning key has reached max usage
- Agent running outdated version that is incompatible with current policies
- Agent group auto-upgrade is disabled, preventing version updates

---

## Resolution Steps

### For Disconnected Agent
1. Verify network connectivity from the host to Zscaler cloud
2. Check agent service status on the host (`systemctl status zms-agent`)
3. Review agent logs for connection errors
4. Verify firewall rules allow outbound to Zscaler endpoints
5. If agent is unresponsive, restart the agent service

### For Enrollment Failure
1. Verify provisioning key has remaining usage
2. Confirm the key is associated with the correct agent group
3. Retrieve TOTP secrets for the target agent group
4. Verify the enrollment command includes the correct customer ID
5. Check that the host can reach the Zscaler enrollment endpoint

### For Version Mismatch
1. Enable auto-upgrade on the agent group (via `agentGroupUpdate` mutation in portal/API)
2. Schedule an upgrade window during maintenance
3. Reset upgrade status if stuck (via `agentGroupUpgradeStatusReset` mutation in portal/API)
4. For critical agents, plan manual upgrades with rollback plan
5. Verify new version compatibility with the host OS

### For Missing Agent
1. Confirm the agent was installed on the target host
2. Verify the provisioning key used during installation
3. Check if the agent registered under a different hostname
4. Review agent installer logs for errors
5. If agent was accidentally removed, re-install using a valid provisioning key

### For Removing a Decommissioned Agent
1. Identify the agent via `zms_list_agents(search="<hostname>")`
2. Remove via the Zscaler admin portal or `agentDelete` mutation (not available via MCP)
3. Verify removal by re-searching for the agent
```text

---

## Common Issues Quick Reference

| Symptom | Likely Cause | Quick Check |
|---------|-------------|------------|
| Agent disconnected | Network/host issue | `zms_list_agents(search="<host>")` |
| All agents disconnected | Infrastructure issue | `zms_get_agent_connection_status_statistics()` |
| Enrollment failed | Key exhausted | `zms_list_nonces()` |
| Wrong agent group | Wrong provisioning key | `zms_get_nonce(eyez_id)` |
| Version mismatch | Auto-upgrade disabled | `zms_get_agent_version_statistics()` |
| Agent not found | Never enrolled | `zms_list_agents(page_size=100)` |
| TOTP required | Need enrollment creds | `zms_get_agent_group_totp_secrets(eyez_id)` |

---

## Edge Cases

### ZSCALER_CUSTOMER_ID Not Set

```text
ZSCALER_CUSTOMER_ID environment variable is required for all ZMS tools.

Set this variable before using ZMS tools. The customer ID can be
found in the Zscaler admin portal under Administration > Company Profile.
```text

### No Agents Found

```text
No agents found in the ZMS deployment.

Possible causes:
- Microsegmentation has not been deployed yet
- Agents are registered under a different customer ID
- The customer ID environment variable is incorrect

Action: Verify ZSCALER_CUSTOMER_ID and confirm agent deployment
status with the infrastructure team.
```text

### All Provisioning Keys Exhausted

```text
All provisioning keys have reached their maximum usage limit.

Available keys:
- "Prod Key": 50/50 used (exhausted)
- "Dev Key": 25/25 used (exhausted)

Action: Create new provisioning keys via the Zscaler admin portal
or the ZMS GraphQL API (nonceCreate or nonceWithAgentGroupCreate
mutations). Current MCP tools are read-only and cannot create keys.
```text

### GraphQL Errors with HTTP 200

```text
The ZMS API returned HTTP 200 but with GraphQL errors in the
response body.

Common error patterns:
- "Data fetching Failed: Forbidden to use API" with code FORBIDDEN
  → API access not authorized, check permissions
- INTERNAL_ERROR classification
  → Server-side error, retry or contact support
- Invalid query parameters
  → Check pagination, sorting, and filter values

The ZMS GraphQL API may return HTTP 200 even when the query fails.
Always check the response body for the "errors" field with its
"message", "path", and "extensions" fields.
```text

---

## Quick Reference

**Primary workflow:** Identify Issue → Fleet Health → Find Agent → Agent Groups → Provisioning Keys → Diagnose

**Agent tools:**

- `zms_list_agents(search, page, page_size)` -- find and list agents
- `zms_get_agent_connection_status_statistics()` -- fleet connection health
- `zms_get_agent_version_statistics()` -- version distribution

**Agent group tools:**

- `zms_list_agent_groups()` -- list all agent groups
- `zms_get_agent_group_totp_secrets(eyez_id)` -- TOTP enrollment credentials

**Provisioning key tools:**

- `zms_list_nonces()` -- list all provisioning keys
- `zms_get_nonce(eyez_id)` -- specific key details

**Troubleshooting checklist:**

1. Is the agent enrolled? → `zms_list_agents(search)`
2. Is the agent connected? → Check `connectionStatus` field
3. Is the version current? → `zms_get_agent_version_statistics()`
4. Is the agent group configured? → `zms_list_agent_groups()`
5. Are provisioning keys available? → `zms_list_nonces()`
6. Are TOTP secrets accessible? → `zms_get_agent_group_totp_secrets()`

**API mutation operations** (available via portal/API, not MCP):

- `agentUpdate` / `agentDelete` -- manage individual agents
- `agentGroupCreate` / `agentGroupUpdate` / `agentGroupDelete` -- manage groups
- `agentGroupUpgradeStatusReset` -- reset stuck upgrade status
- `nonceCreate` / `nonceUpdate` / `nonceDelete` -- manage provisioning keys
- `nonceWithAgentGroupCreate` -- create key and group together
