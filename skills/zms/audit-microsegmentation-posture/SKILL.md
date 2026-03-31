---
name: zms-audit-microsegmentation-posture
description: "Audit the overall Zscaler Microsegmentation (ZMS) deployment posture. Reviews agent fleet health, workload protection coverage, resource group structure, policy rules, app zones, application catalog, and tag-based classification. Use when an administrator asks: 'What is our microsegmentation coverage?', 'How many workloads are protected?', 'Show me our ZMS policies', 'Review our microsegmentation deployment', or 'Audit our ZMS posture.'"
---

# ZMS: Audit Microsegmentation Posture

## Keywords
microsegmentation, ZMS audit, workload protection, agent health, policy rules, resource groups, app zones, microsegmentation coverage, zero trust, lateral movement, workload segmentation, protection status, security posture

## Overview

Perform a comprehensive audit of your Zscaler Microsegmentation (ZMS) deployment by examining agent fleet health, workload protection coverage, resource group structure, segmentation policies, app zone boundaries, and the application catalog. Microsegmentation is a critical Zero Trust capability that prevents lateral movement by enforcing granular communication policies between workloads.

The ZMS API is a GraphQL endpoint on OneAPI that supports two root operation types:
- **Query** (read-only): Retrieve agents, groups, statistics, metadata, nonces, resources, policies, and app zones. All current MCP tools use this type.
- **Mutation** (write): Create, update, and delete agents, groups, nonces, policy rules, and resource groups. These operations are available in the API but are not yet exposed through MCP tools.

**Use this skill when:** A security architect or administrator needs to assess microsegmentation coverage, verify policy configurations, review resource grouping strategy, identify unprotected workloads, or generate a posture report for compliance or executive review.

**Important:**
- All ZMS tools require `ZSCALER_CUSTOMER_ID` to be set as an environment variable.
- All current MCP tools are **read-only** (Query operations only).
- The underlying API also supports **Mutation** operations for managing agents, groups, policies, and resources — but these are not yet exposed through MCP tools.
- GraphQL errors may return HTTP 200 with errors in the response body — always check the response for error details.

---

## Workflow

Follow this 7-step process for a comprehensive microsegmentation audit.

### Step 1: Assess Agent Fleet Health

**Get agent connection status overview:**
```
zms_get_agent_connection_status_statistics()
```

This returns total agent count and percentage breakdown by connection status. Key metrics:
- **Total agents**: How many microsegmentation agents are deployed
- **Connected vs disconnected**: What percentage are actively reporting
- **Connection health target**: > 95% connected agents

**Get agent version distribution:**
```
zms_get_agent_version_statistics()
```

Evaluate version consistency:
- Are all agents on the same version?
- How many agents are running outdated versions?
- Is an upgrade rollout in progress?

**List agents with details:**
```
zms_list_agents(page=1, page_size=50)
```

Review individual agent details:
- Connection status per agent
- OS distribution (Linux, Windows, etc.)
- IP addresses and hostnames
- Agent group membership

**Search for specific agents:**
```
zms_list_agents(search="<hostname_or_ip>", page_size=20)
```

---

### Step 2: Review Workload Protection Coverage

**Get resource protection status:**
```
zms_get_resource_protection_status()
```

This returns the critical coverage metric:
- **Protected resources**: Workloads with active segmentation policies
- **Unprotected resources**: Workloads without policy coverage
- **Protection percentage**: Target > 90% for mature deployments

**List all resources (workloads):**
```
zms_list_resources(page_num=1, page_size=50)
```

For each resource, review:
- Resource type (VM, container, bare metal)
- Cloud provider (AWS, Azure, GCP, on-premises)
- Region / availability zone
- Hostname and OS
- App zone mapping
- Protection status

**Include deleted resources for full inventory:**
```
zms_list_resources(page_num=1, page_size=50, include_deleted=True)
```

**Get resource event metadata:**
```
zms_get_metadata()
```

---

### Step 3: Analyze Resource Group Structure

**List all resource groups:**
```
zms_list_resource_groups(page_num=1, page_size=50)
```

Resource groups define how workloads are logically grouped for policy enforcement. The ZMS platform supports three distinct group types:

- **Managed groups**: Membership is dynamically determined by tag-based rules. When workload tags change, group membership updates automatically. Best for cloud-native environments where workloads are tagged via AWS, Azure, or GCP. The API supports creating (`managedResourceGroupCreate`) and updating (`managedResourceGroupUpdate`) these groups via mutations.
- **Unmanaged groups**: Membership is statically defined by CIDR blocks and/or FQDNs. Best for on-premises workloads or fixed infrastructure. The API supports creating (`unmanagedResourceGroupCreate`) and updating (`unmanagedResourceGroupUpdate`) these groups via mutations.
- **Recommended groups**: ML-based recommendations from ZMS that suggest resource groupings based on observed traffic patterns. The API provides a `recommendedResourceGroups` query and `managedRecommendedResourceGroupUpdate` mutation for acting on these recommendations. (Not yet available via MCP tools.)

Additional review points:
- **Member count**: Groups with 0 members may be unused
- **Naming convention**: Groups should follow a clear naming standard
- **Origin**: Whether the group was created manually, imported, or ML-recommended

**Get resource group protection status:**
```
zms_get_resource_group_protection_status()
```

Identify which resource groups have policies applied and which are unprotected.

**Inspect members of a specific group:**
```
zms_get_resource_group_members(
    group_id="<group_id>",
    page_num=1,
    page_size=50
)
```

Verify:
- Expected workloads are in the correct groups
- Cloud provider and region distribution within the group
- No stale or decommissioned workloads in active groups

---

### Step 4: Review Segmentation Policies

**List all policy rules:**
```
zms_list_policy_rules(page_num=1, page_size=50)
```

Policy rules define the allowed or denied communication paths between resource groups. The ZMS API supports full CRUD for policy rules via mutations (`policyRuleCreate`, `policyRuleUpdate`, `policyRuleDelete`), but current MCP tools are read-only.

For each rule, review:
- **Name and description**: Clear, descriptive naming
- **Action**: Allow or Block
- **Priority**: Rule ordering matters -- higher priority rules are evaluated first
- **Source/destination target types**: Which resource groups can communicate
- **Ports and protocols**: Specific port/protocol restrictions (TCP, UDP, ICMP, specific port ranges)
- **Last hit time (`lastHit`)**: Rules that haven't been matched recently may be obsolete
- **Creation time**: When the rule was created — helps identify legacy rules

**Fetch all rules (bypassing pagination):**
```
zms_list_policy_rules(fetch_all=True)
```

**List default (baseline) policies:**
```
zms_list_default_policy_rules()
```

Default rules define the baseline security posture. The API supports batch operations on default rules (`defaultPolicyRulesCreate`, `defaultPolicyRulesUpdate`, `defaultPolicyRulesDelete`):
- **Default deny**: All traffic blocked unless explicitly allowed (recommended for Zero Trust)
- **Default allow**: All traffic allowed unless explicitly blocked (permissive — not recommended)
- **Direction**: Inbound vs outbound default behavior
- **Scope type**: Whether the default applies globally or to specific segments

---

### Step 5: Review App Zones

**List all app zones:**
```
zms_list_app_zones(page_num=1, page_size=50)
```

App zones define logical application boundaries that control the scope of microsegmentation enforcement. The API supports filtering and sorting for app zone queries. Review:
- **Zone names and descriptions**: Should map to application architecture tiers
- **Member count per zone**: How many resources belong to each zone
- **VPC/subnet inclusion settings**: Whether entire VPCs/subnets are included
- **Architecture alignment**: Zones should reflect application tiers (e.g., web tier, app tier, database tier, shared services)
- **Cross-zone communication**: Identify which zones need inter-zone policy rules

---

### Step 6: Review Application Catalog

**List discovered applications:**
```
zms_list_app_catalog(page_num=1, page_size=50)
```

The app catalog shows applications discovered by the microsegmentation agents:
- Application name and category
- Port and protocol requirements
- Associated processes
- Discovery timestamps

Use this to:
- Verify application discovery is working
- Identify applications that need segmentation policies
- Understand port/protocol requirements for policy creation

---

### Step 7: Review Tags and Classification

**List tag namespaces:**
```
zms_list_tag_namespaces(page_num=1, page_size=50)
```

Tag namespaces organize classification metadata:
- **CUSTOM**: User-defined tags
- **EXTERNAL**: Cloud provider tags (AWS, Azure, GCP)
- **ML**: Machine-learning discovered tags
- **UNKNOWN**: Unclassified tags

**Explore tag keys within a namespace:**
```
zms_list_tag_keys(
    namespace_id="<namespace_id>",
    page_num=1,
    page_size=50
)
```

**Explore tag values for a key:**
```
zms_list_tag_values(
    tag_id="<tag_id>",
    namespace_origin="EXTERNAL",
    page_num=1,
    page_size=50
)
```

Tags are critical for dynamic resource group membership. Verify:
- Cloud provider tags are being imported correctly
- Custom tags follow organizational standards
- ML-discovered tags align with actual workload classification

---

### Present Audit Report

```
Microsegmentation Posture Audit Report
==========================================
Date: <current_date>
Auditor: AI Assistant

## Executive Summary

- **Total Agents:** 245
- **Connected:** 238 (97.1%) -- HEALTHY
- **Agent Versions:** 3 versions in use (latest: v4.2.1)
- **Total Workloads:** 312
- **Protected:** 287 (92.0%) -- MEETS TARGET
- **Unprotected:** 25 (8.0%) -- NEEDS ATTENTION
- **Resource Groups:** 18
- **Policy Rules:** 42 custom rules + 3 default rules
- **App Zones:** 8
- **Overall Posture:** STRONG with improvements needed

---

## Agent Fleet Health

| Metric                | Value      | Target  | Status   |
|----------------------|-----------|---------|----------|
| Total Agents          | 245       | N/A     | --       |
| Connected             | 238 (97%) | > 95%   | PASS     |
| Disconnected          | 7 (3%)    | < 5%    | PASS     |
| Latest Version        | 230 (94%) | > 90%   | PASS     |
| Outdated Versions     | 15 (6%)   | < 10%   | PASS     |

**Disconnected agents (7):**
| Hostname           | Last Seen    | OS       | Action        |
|-------------------|-------------|----------|---------------|
| web-srv-03         | 3 days ago  | Ubuntu   | Investigate   |
| db-replica-02      | 1 week ago  | CentOS   | Decommission? |
| ...                | ...         | ...      | ...           |

---

## Protection Coverage

| Category           | Count | Protected | Unprotected | Coverage |
|-------------------|-------|-----------|-------------|----------|
| VMs                | 180   | 172       | 8           | 95.6%    |
| Containers         | 95    | 85        | 10          | 89.5%    |
| Bare Metal         | 37    | 30        | 7           | 81.1%    |
| **Total**          | **312** | **287** | **25**      | **92.0%** |

Bare metal servers have the lowest coverage at 81.1%.
Recommend prioritizing policy creation for these workloads.

---

## Policy Analysis

| Metric                | Value  | Assessment           |
|----------------------|--------|---------------------|
| Custom Rules          | 42     | Adequate coverage    |
| Default Posture       | Deny   | Best practice        |
| Rules Never Hit       | 5      | Review for removal   |
| Rules Hit (7 days)    | 37     | Active enforcement   |
| Overly Broad Rules    | 2      | Tighten scope        |

**Rules never hit** (candidates for removal):
- "Legacy App Migration" -- created 6 months ago, 0 hits
- "Temp Debug Access" -- created 3 months ago, 0 hits
- ...

---

## Resource Group Structure

| Type     | Groups | Members | Avg Size | Assessment     |
|----------|--------|---------|----------|----------------|
| Managed  | 12     | 245     | 20.4     | Well-structured |
| Unmanaged| 6      | 67      | 11.2     | Review CIDRs   |
| Empty    | 2      | 0       | 0        | Remove          |

---

## Recommendations

### Critical
1. Create segmentation policies for 25 unprotected workloads
2. Investigate 7 disconnected agents
3. Remove 2 empty resource groups

### High
4. Upgrade 15 agents running outdated versions
5. Review 5 policy rules with no hits -- remove if obsolete
6. Tighten 2 overly broad policy rules

### Medium
7. Improve bare metal coverage from 81.1% to > 90%
8. Standardize tag naming conventions
9. Review unmanaged resource group CIDR definitions

### Low
10. Document app zone architecture decisions
11. Schedule quarterly posture reviews
```

---

## Edge Cases

### No Agents Deployed

```
No ZMS agents found in your environment.

This means microsegmentation has not been deployed yet, or
agents are registered under a different customer ID.

Action: Verify ZSCALER_CUSTOMER_ID and check agent deployment status.
```

### ZSCALER_CUSTOMER_ID Not Set

```
ZSCALER_CUSTOMER_ID environment variable is required for all ZMS tools.

Set this variable to your Zscaler customer ID before using ZMS tools.
The customer ID can be found in the Zscaler admin portal under
Administration > Company Profile.
```

### GraphQL Errors with HTTP 200

```
The ZMS API returned HTTP 200 but with GraphQL errors in the
response body.

Common error codes:
- FORBIDDEN (403): API access not authorized for this operation
- INTERNAL_ERROR: Server-side error -- retry or contact support
- BAD_REQUEST: Invalid query parameters

The ZMS GraphQL API may return HTTP 200 even when the query fails.
Always check the response body for the "errors" field.
```

### All Workloads Protected

```
All 312 workloads are protected (100% coverage).

This is excellent! Continue monitoring:
- New workloads should be automatically assigned to resource groups
  (use managed groups with tag-based rules for auto-assignment)
- Policy rules should be reviewed quarterly for relevance
- Agent version consistency should be maintained
- Check for ML-recommended resource groups periodically
```

### Mutation Operations Needed

```
The requested operation (create/update/delete) requires mutation
access which is not available through current MCP tools.

Available mutation operations in the ZMS API:
- Agent management: agentDelete, agentUpdate
- Agent groups: agentGroupCreate/Update/Delete
- Nonces: nonceCreate/Update/Delete, nonceWithAgentGroupCreate
- Policy rules: policyRuleCreate/Update/Delete
- Default rules: defaultPolicyRulesCreate/Update/Delete (batch)
- Resource groups: managedResourceGroupCreate/Update,
  unmanagedResourceGroupCreate/Update, resourceGroupDelete

Action: Perform these operations through the Zscaler admin portal
or the ZMS API directly.
```

---

## Quick Reference

**Primary workflow:** Agents → Protection → Groups → Policies → App Zones → App Catalog → Tags → Report

**Agent tools:**
- `zms_list_agents()` -- list all agents with details
- `zms_get_agent_connection_status_statistics()` -- fleet connection health
- `zms_get_agent_version_statistics()` -- version distribution

**Resource tools:**
- `zms_list_resources()` -- list workloads
- `zms_get_resource_protection_status()` -- protection coverage
- `zms_get_metadata()` -- resource event metadata

**Resource group tools:**
- `zms_list_resource_groups()` -- list all groups
- `zms_get_resource_group_members(group_id)` -- members of a specific group
- `zms_get_resource_group_protection_status()` -- group protection coverage

**Policy tools:**
- `zms_list_policy_rules()` -- custom segmentation rules
- `zms_list_default_policy_rules()` -- baseline policies

**App zone tools:**
- `zms_list_app_zones()` -- application boundaries

**Application catalog tools:**
- `zms_list_app_catalog()` -- discovered applications

**Tag tools:**
- `zms_list_tag_namespaces()` -- tag organization categories
- `zms_list_tag_keys(namespace_id)` -- keys within a namespace
- `zms_list_tag_values(tag_id, namespace_origin)` -- values for a key
