---
name: zms-assess-workload-protection
description: "Assess Zscaler Microsegmentation (ZMS) workload protection coverage and identify protection gaps. Investigates resource protection status, resource group membership, unprotected workloads by cloud and region, and resource group coverage gaps. Use when an administrator asks: 'Which workloads are unprotected?', 'What is our microsegmentation coverage?', 'Find protection gaps', 'Which resource groups have no policies?', 'Show me unprotected resources', or 'What is our workload coverage percentage?'"
---

# ZMS: Assess Workload Protection & Coverage Gaps

## Keywords
workload protection, protection gaps, unprotected resources, protection status, resource groups, resource coverage, microsegmentation coverage, workload inventory, protected workloads, coverage percentage, security gaps, lateral movement risk

## Overview

Perform a focused assessment of workload protection coverage in Zscaler Microsegmentation. This skill systematically identifies unprotected resources, analyzes resource group coverage, breaks down protection status by cloud provider and region, and produces an actionable remediation plan to close coverage gaps.

In a microsegmentation deployment, a workload (resource) is "protected" when:
1. An agent is deployed and connected on the workload
2. The workload belongs to at least one resource group
3. The resource group is referenced by at least one policy rule

A gap at any of these three levels leaves the workload exposed to lateral movement. This skill investigates all three levels to find exactly where coverage breaks down.

**Use this skill when:** An administrator needs to identify unprotected workloads for remediation, prepare protection coverage reports for compliance, assess whether new deployments have adequate segmentation, or track protection percentage over time.

**Important:**
- All ZMS tools require `ZSCALER_CUSTOMER_ID` to be set as an environment variable.
- All current MCP tools are **read-only** (Query operations).
- Remediation (creating resource groups, adding policy rules) must be done through the Zscaler admin portal or the ZMS API directly.

---

## Workflow

Follow this 6-step process for a complete workload protection assessment.

### Step 1: Get the Protection Status Overview

**Get overall resource protection status:**
```
zms_get_resource_protection_status(page_num=1, page_size=100)
```

This returns the headline metric:
- **Total resources**: All workloads discovered by agents
- **Protected count**: Workloads with active segmentation coverage
- **Unprotected count**: Workloads without policy coverage
- **Protection percentage**: The primary coverage KPI

**Target thresholds:**
- **> 95%**: Mature deployment — focus on closing remaining gaps
- **90-95%**: Good coverage — systematic remediation plan needed
- **80-90%**: Moderate coverage — significant gaps exist
- **< 80%**: Low coverage — microsegmentation is partially deployed

---

### Step 2: Inventory All Workloads

**List all resources:**
```
zms_list_resources(page_num=1, page_size=50)
```

For each resource, capture:
- **Name/hostname**: Workload identifier
- **Type**: VM, container, bare metal
- **Cloud provider**: AWS, Azure, GCP, on-premises
- **Region/availability zone**: Geographic location
- **OS**: Operating system
- **IP addresses**: Network addresses
- **App zone**: Application zone membership
- **Protection status**: Whether this specific workload has policy coverage

**Paginate through all resources for large environments:**
```
zms_list_resources(page_num=2, page_size=50)
```

**Include deleted resources for a complete audit trail:**
```
zms_list_resources(page_num=1, page_size=50, include_deleted=True)
```

This helps identify:
- Recently decommissioned workloads that may still appear in resource groups
- Workloads removed from the fleet that had policy coverage
- Ghost entries that need cleanup

---

### Step 3: Analyze Protection by Resource Group

**List all resource groups:**
```
zms_list_resource_groups(page_num=1, page_size=50)
```

**Get group-level protection status:**
```
zms_get_resource_group_protection_status(page_num=1, page_size=50)
```

**For each resource group, classify:**

- **Fully protected**: All members have policy coverage
- **Partially protected**: Some members covered, some not
- **Unprotected**: Group exists but no policy rules reference it
- **Empty**: Group has 0 members (may be misconfigured or unused)

**Investigate specific groups with issues:**
```
zms_get_resource_group_members(
    group_id="<group_id>",
    page_num=1,
    page_size=50
)
```

For groups with protection gaps, list members to identify exactly which workloads are unprotected.

**Document group types:**
- **Managed groups** (tag-driven): Check if tag criteria are too narrow (excluding workloads) or too broad (including unintended workloads)
- **Unmanaged groups** (CIDR/FQDN): Check if CIDR ranges are current and match actual infrastructure

---

### Step 4: Identify Root Causes of Gaps

**For each unprotected workload, determine the root cause:**

**Cause 1: Workload not in any resource group**
- The workload has an agent but isn't classified into any group
- For managed groups: workload tags don't match any group's tag criteria
- For unmanaged groups: workload IP is outside all defined CIDRs
- **Fix**: Add appropriate tags or update CIDR ranges

**Cause 2: Resource group has no policy rules**
- The workload is in a resource group, but no policy rule references that group
- **Fix**: Create policy rules (via admin portal) that include this resource group as source or destination

**Cause 3: Agent not deployed or disconnected**
- The workload exists in cloud infrastructure but has no agent
- Or the agent was deployed but is disconnected

**Verify agent coverage:**
```
zms_get_agent_connection_status_statistics()
```

**Correlate with resource list:**
```
zms_list_agents(page=1, page_size=50)
```

Compare the agent list with the resource list. Resources without a corresponding connected agent represent deployment gaps.

**Cause 4: Stale resource group membership**
- Managed group tag criteria no longer match the workload's current tags
- Unmanaged group CIDRs are outdated after infrastructure changes
- **Fix**: Update tag criteria or CIDR definitions

---

### Step 5: Break Down Coverage by Dimensions

**Analyze coverage across dimensions using the resource list from Step 2:**

**By cloud provider:**
```
Coverage by Cloud Provider
============================
AWS:          145/160 protected (90.6%)
Azure:         87/95  protected (91.6%)
GCP:           35/40  protected (87.5%)
On-Premises:   20/25  protected (80.0%)
```

**By resource type:**
```
Coverage by Resource Type
===========================
VMs:           172/180 protected (95.6%)
Containers:     85/95  protected (89.5%)
Bare Metal:     30/37  protected (81.1%)
```

**By app zone:**
```
Coverage by App Zone
======================
Web Tier:       48/48  protected (100%)
App Tier:       62/65  protected (95.4%)
DB Tier:        30/30  protected (100%)
Shared Services: 25/25 protected (100%)
Unzoned:        22/44  protected (50.0%)  ← CRITICAL
```

**"Unzoned" workloads** — resources not assigned to any app zone — are often the largest protection gap. They tend to be newly deployed workloads or infrastructure that was overlooked during initial segmentation rollout.

---

### Step 6: Build Remediation Plan

**Get resource event metadata for additional context:**
```
zms_get_metadata()
```

---

### Present Protection Assessment Report

```
Workload Protection Assessment Report
========================================
Date: <current_date>
Auditor: AI Assistant

## Executive Summary

- **Total Workloads:** 312
- **Protected:** 287 (92.0%)
- **Unprotected:** 25 (8.0%)
- **Target Coverage:** > 95%
- **Gap to Target:** 3.0% (10 additional workloads)
- **Protection Status:** MODERATE — remediation required

---

## Protection Overview

| Metric | Count | Percentage | Target | Status |
|--------|-------|-----------|--------|--------|
| Protected | 287 | 92.0% | > 95% | BELOW |
| Unprotected | 25 | 8.0% | < 5% | ABOVE |
| Total | 312 | 100% | — | — |

---

## Coverage by Cloud Provider

| Cloud | Total | Protected | Unprotected | Coverage | Status |
|-------|-------|-----------|-------------|----------|--------|
| AWS | 160 | 145 | 15 | 90.6% | NEEDS WORK |
| Azure | 95 | 87 | 8 | 91.6% | NEEDS WORK |
| GCP | 40 | 35 | 5 | 87.5% | NEEDS WORK |
| On-Prem | 25 | 20 | 5 | 80.0% | CRITICAL |

---

## Coverage by Resource Type

| Type | Total | Protected | Unprotected | Coverage | Status |
|------|-------|-----------|-------------|----------|--------|
| VM | 180 | 172 | 8 | 95.6% | GOOD |
| Container | 95 | 85 | 10 | 89.5% | NEEDS WORK |
| Bare Metal | 37 | 30 | 7 | 81.1% | CRITICAL |

---

## Resource Groups with Gaps

| Group Name | Type | Members | Protected | Gap | Root Cause |
|------------|------|---------|-----------|-----|------------|
| New API Servers | Managed | 8 | 0 | 8 | No policy rules |
| Legacy Infra | Unmanaged | 5 | 2 | 3 | Stale CIDRs |
| (No group) | — | 14 | 0 | 14 | Not classified |

---

## Unprotected Workloads Detail

| Hostname | Cloud | Type | OS | IP | Gap Reason |
|----------|-------|------|----|----|------------|
| api-new-01 | AWS | VM | Ubuntu | 10.0.5.10 | No group |
| api-new-02 | AWS | VM | Ubuntu | 10.0.5.11 | No group |
| batch-worker-01 | GCP | VM | Debian | 10.2.1.5 | No policy |
| ... | ... | ... | ... | ... | ... |

---

## Remediation Plan

### Priority 1: Immediate (14 workloads — no resource group)
- Create managed resource groups with tag criteria matching these workloads
- OR add workload IPs to existing unmanaged resource groups
- Expected coverage improvement: +4.5%

### Priority 2: High (8 workloads — group exists, no policy)
- Create policy rules for "New API Servers" resource group
- Define allowed communication paths (ports, protocols, directions)
- Expected coverage improvement: +2.6%

### Priority 3: Medium (3 workloads — stale group membership)
- Update CIDR ranges in "Legacy Infra" unmanaged resource group
- Verify IP addresses match current infrastructure
- Expected coverage improvement: +1.0%

### Projected Result After Remediation
- Protected: 312/312 (100%)
- All workloads covered by segmentation policies

---

## Trend Tracking

Recommend running this assessment monthly and tracking:
- Protection percentage over time
- New workload onboarding time-to-protection
- Resource group membership changes
- Policy rule creation rate vs workload growth rate
```

---

## Edge Cases

### 100% Protection Coverage

```
All workloads are protected (100% coverage).

This is excellent! Verify this remains true by:
1. Ensuring new workloads are auto-classified via managed resource
   groups (tag-based membership)
2. Monitoring agent deployment on new infrastructure
3. Reviewing resource group membership after infrastructure changes
4. Checking that decommissioned workloads are cleaned up
```

### No Resources Found

```
No resources (workloads) found in the ZMS deployment.

Possible causes:
- No agents are deployed or connected
- Agents are deployed but haven't reported resource data yet
- ZSCALER_CUSTOMER_ID may be incorrect

Action: Verify agent deployment using
zms_get_agent_connection_status_statistics() and check
ZSCALER_CUSTOMER_ID configuration.
```

### All Unprotected Resources Are in One Cloud

```
All 25 unprotected workloads are in AWS.

This suggests a deployment gap specific to AWS:
- AWS tag integration may not be configured
- New AWS accounts may not have agent deployment automation
- AWS-specific resource groups may be missing

Action: Prioritize AWS tag integration and resource group creation.
```

---

## Quick Reference

**Primary workflow:** Protection Status → Inventory → Group Analysis → Root Causes → Dimensional Breakdown → Remediation

**Protection status tools:**
- `zms_get_resource_protection_status()` — overall protection metrics
- `zms_get_resource_group_protection_status()` — per-group protection

**Resource tools:**
- `zms_list_resources(page_num, page_size)` — workload inventory
- `zms_list_resources(include_deleted=True)` — including decommissioned
- `zms_get_metadata()` — resource event metadata

**Resource group tools:**
- `zms_list_resource_groups()` — all groups with types
- `zms_get_resource_group_members(group_id)` — members of a specific group

**Agent tools (for correlation):**
- `zms_get_agent_connection_status_statistics()` — agent deployment health
- `zms_list_agents()` — individual agent status

**Not yet available via MCP tools:**
- Resource group create/update/delete
- Policy rule create/update/delete
- These must be performed through the Zscaler admin portal or the ZMS API
