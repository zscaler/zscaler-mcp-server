---
name: zms-review-tag-classification
description: "Review Zscaler Microsegmentation (ZMS) tag classification, application discovery, and tag-to-resource-group mapping. Investigates tag namespaces (CUSTOM, EXTERNAL, ML), tag keys and values, application catalog entries, and how tags drive managed resource group membership. Use when an administrator asks: 'Show me our tag structure', 'What cloud tags are imported?', 'How are resource groups using tags?', 'What applications were discovered?', 'Review tag classification', or 'Are ML tags being used?'"
---

# ZMS: Review Tag Classification & Application Discovery

## Keywords
tags, tag namespaces, tag keys, tag values, application catalog, app catalog, resource groups, managed groups, workload classification, cloud tags, ML tags, custom tags, EXTERNAL, CUSTOM, ML, application discovery, tag hierarchy, resource grouping

## Overview

Review the tag classification hierarchy, application catalog discoveries, and how tags drive dynamic resource group membership in Zscaler Microsegmentation. Tags are the foundation of automated workload classification — they determine which workloads belong to which managed resource groups, which in turn are referenced by segmentation policy rules.

The tag system has three levels: **namespace → key → value**. Tag namespaces indicate the origin of the tags:
- **EXTERNAL**: Imported from cloud providers (AWS, Azure, GCP) — e.g., instance tags, labels, resource metadata
- **CUSTOM**: Created by administrators in the ZMS console for organization-specific classification
- **ML**: Machine-learning discovered tags based on observed traffic patterns and workload behavior
- **UNKNOWN**: Tags that don't fit the other categories

The **Application Catalog** tracks applications discovered by microsegmentation agents on workloads — identified by process name, protocol, port, and category. These discoveries inform tag recommendations and help administrators understand what's running in their environment.

**Use this skill when:** An administrator needs to review how workloads are classified, verify cloud tag imports, assess ML tag adoption, audit tag naming conventions, understand application discovery state, or troubleshoot resource group membership driven by tags.

**Important:**
- All ZMS tools require `ZSCALER_CUSTOMER_ID` to be set as an environment variable.
- All current MCP tools are **read-only** (Query operations).
- The ZMS API supports **ML Tag Recommendations** (accept/ignore/delete ML-suggested tags) but this is not yet exposed through MCP tools.

---

## Workflow

Follow this 5-step process for a complete tag classification review.

### Step 1: Map the Tag Namespace Landscape

**List all tag namespaces:**
```
zms_list_tag_namespaces(page_num=1, page_size=50)
```

This returns the top-level organizational categories for all tags. For each namespace, note:
- **Name**: The namespace identifier
- **Origin**: CUSTOM, EXTERNAL, ML, or UNKNOWN
- **Key count**: How many tag keys exist under this namespace
- **ID**: Required for drilling into keys (Step 2)

**Key questions to answer:**
- Are cloud provider tags (EXTERNAL) being imported? If not, cloud tag integration may not be configured.
- Are there CUSTOM namespaces? These indicate intentional organizational tagging.
- Are ML namespaces present? These indicate the ML recommendation engine is active.
- How many namespaces exist? Too many may indicate inconsistent tagging strategy.

**Expected healthy state:**
- At least one EXTERNAL namespace per cloud provider in use (AWS, Azure, GCP)
- One or more CUSTOM namespaces for organizational tags
- ML namespace(s) present if ML recommendations are enabled

---

### Step 2: Explore Tag Keys Within Each Namespace

**For each namespace identified in Step 1, list the tag keys:**
```
zms_list_tag_keys(
    namespace_id="<namespace_id>",
    page_num=1,
    page_size=50
)
```

Tag keys are the categories within a namespace. For example:
- EXTERNAL namespace might have keys like: `aws:environment`, `aws:team`, `aws:application`, `azure:resourceGroup`
- CUSTOM namespace might have keys like: `tier`, `compliance-level`, `data-classification`
- ML namespace might have keys like: `ml-app-group`, `ml-traffic-pattern`

**For each key, evaluate:**
- **Naming convention**: Are keys consistently named? (kebab-case, camelCase, etc.)
- **Relevance**: Do keys map to meaningful workload attributes?
- **Coverage**: Are the expected organizational dimensions represented (environment, team, application, tier)?
- **Staleness**: Are there keys that no longer apply?

**Document the key hierarchy:**
```
Namespace: aws-tags (EXTERNAL)
├── environment → [prod, staging, dev, test]
├── team → [platform, backend, data, security]
├── application → [api-gateway, user-service, payment-service, ...]
└── cost-center → [eng-001, eng-002, ops-001, ...]

Namespace: org-classification (CUSTOM)
├── data-sensitivity → [public, internal, confidential, restricted]
├── compliance → [pci, hipaa, sox, none]
└── tier → [web, app, database, shared-services]
```

---

### Step 3: Inspect Tag Values for Critical Keys

**For each important tag key, list the values:**
```
zms_list_tag_values(
    tag_id="<tag_id>",
    namespace_origin="EXTERNAL",
    page_num=1,
    page_size=50
)
```

The `namespace_origin` parameter must be one of: `CUSTOM`, `EXTERNAL`, `ML`, `UNKNOWN`.

**Evaluate values for:**
- **Consistency**: Are values standardized? (e.g., "prod" vs "production" vs "Production")
- **Completeness**: Are all expected values present?
- **Cardinality**: High cardinality (many unique values) may make tag-based grouping impractical
- **Meaningful grouping**: Do values map to logical resource group boundaries?

**Flag issues:**
- Duplicate values with different casing or spelling
- Values that are too specific (e.g., individual instance IDs) for grouping
- Missing expected values (e.g., "production" environment exists but "staging" doesn't)

---

### Step 4: Review Application Catalog Discoveries

**List discovered applications:**
```
zms_list_app_catalog(page_num=1, page_size=50)
```

The application catalog shows what the microsegmentation agents have discovered running on workloads:
- **Application name**: Identified application
- **Application category**: Classification of the application
- **Process name**: The process executing the application
- **Protocol**: Network protocol (TCP, UDP, etc.)
- **Port range**: Port start and end

**Analysis points:**
- **Expected applications**: Verify that known business applications appear in the catalog
- **Unknown applications**: Identify unrecognized applications that may need investigation
- **Port usage**: Understand what ports are actively in use for policy creation
- **Category coverage**: Ensure applications are properly categorized
- **Discovery gaps**: If expected applications are missing, agents may not be deployed on those workloads

**Correlate with tags:**
- Applications in the catalog should have corresponding tags for classification
- ML tag recommendations are generated based on application catalog discoveries
- If an application appears in the catalog but has no corresponding tags, tagging coverage needs improvement

---

### Step 5: Correlate Tags with Resource Group Membership

**List resource groups to understand tag-driven membership:**
```
zms_list_resource_groups(page_num=1, page_size=50)
```

Resource groups come in two types:
- **Managed groups**: Membership determined dynamically by tag-based rules. When workload tags change, group membership updates automatically.
- **Unmanaged groups**: Membership defined statically by CIDR blocks and/or FQDNs.

**For managed groups, evaluate:**
- What tag keys/values determine membership?
- Are the tag rules using the keys identified in Steps 2-3?
- Is the member count expected for the tag criteria?
- Are there managed groups with 0 members? (tag criteria may be wrong)

**Inspect members of key groups:**
```
zms_get_resource_group_members(
    group_id="<group_id>",
    page_num=1,
    page_size=50
)
```

Verify:
- Members match the expected workloads for the tag criteria
- Cloud provider and region distribution is correct
- No unexpected workloads have been included
- No expected workloads are missing

**Check protection status by group:**
```
zms_get_resource_group_protection_status()
```

Identify groups that have members but no policy coverage — these represent classification without enforcement.

---

### Present Tag Classification Report

```
Tag Classification & Application Discovery Report
====================================================
Date: <current_date>
Auditor: AI Assistant

## Executive Summary

- **Tag Namespaces:** 5 (2 EXTERNAL, 2 CUSTOM, 1 ML)
- **Total Tag Keys:** 23
- **Total Tag Values:** 187
- **Discovered Applications:** 34
- **Managed Resource Groups:** 12 (tag-driven)
- **Classification Health:** GOOD with improvements needed

---

## Tag Namespace Overview

| Namespace | Origin | Keys | Values | Status |
|-----------|--------|------|--------|--------|
| aws-tags | EXTERNAL | 8 | 67 | Active |
| azure-labels | EXTERNAL | 6 | 45 | Active |
| org-classification | CUSTOM | 5 | 32 | Active |
| security-zones | CUSTOM | 2 | 8 | Active |
| ml-discovery | ML | 2 | 35 | Review |

---

## Tag Key Analysis

| Key | Namespace | Values | Used by Groups | Issues |
|-----|-----------|--------|----------------|--------|
| environment | aws-tags | 4 | 4 groups | None |
| team | aws-tags | 8 | 6 groups | 2 unused values |
| application | aws-tags | 24 | 12 groups | None |
| tier | org-classification | 4 | 4 groups | None |
| data-sensitivity | org-classification | 4 | 0 groups | NOT USED |

---

## Application Catalog Summary

| Category | Count | Top Applications |
|----------|-------|-----------------|
| Database | 8 | PostgreSQL, MySQL, Redis, MongoDB |
| Web Server | 6 | nginx, Apache, Tomcat, IIS |
| Messaging | 4 | RabbitMQ, Kafka, SQS |
| Custom | 16 | Various business applications |

---

## Recommendations

### Critical
1. Tag key "data-sensitivity" exists but is not used by any resource groups
   → Create managed groups based on data sensitivity for compliance

### High
2. 3 inconsistent tag values found (prod vs production vs Production)
   → Standardize to a single value
3. ML namespace has 35 unreviewed tag suggestions
   → Review and accept/ignore via the ZMS console

### Medium
4. 2 managed resource groups have 0 members
   → Verify tag criteria match actual workload tags
5. 5 discovered applications have no corresponding tags
   → Add custom tags or verify cloud provider tagging

### Low
6. Document tag naming conventions
7. Schedule quarterly tag hygiene reviews
```

---

## Edge Cases

### No Tag Namespaces Found

```
No tag namespaces found in the ZMS deployment.

This means:
- Cloud tag integration is not configured (no EXTERNAL tags)
- No custom tags have been created
- ML tag discovery is not enabled

Action: Configure cloud provider tag integration in the ZMS console
and create custom namespaces for organizational classification.
```

### No Applications in Catalog

```
The application catalog is empty.

Possible causes:
- No agents are deployed or connected
- Agents have not been running long enough to discover applications
- Application discovery may be disabled in agent group settings

Action: Verify agent deployment status using
zms_get_agent_connection_status_statistics() and ensure agents
are connected and running.
```

### ML Tags Present but No Recommendations Reviewed

```
ML tag namespace exists with unreviewed tag suggestions.

The ML recommendation engine has identified patterns but no
recommendations have been accepted, edited, or ignored.

Action: Review ML tag recommendations in the ZMS console under
Microsegmentation > Tag Management > ML Tag Recommendations.
(ML recommendation management is not available via MCP tools.)
```

---

## Quick Reference

**Primary workflow:** Namespaces → Keys → Values → App Catalog → Resource Groups → Report

**Tag tools:**
- `zms_list_tag_namespaces()` — top-level tag organization
- `zms_list_tag_keys(namespace_id)` — keys within a namespace
- `zms_list_tag_values(tag_id, namespace_origin)` — values for a key

**Application catalog tools:**
- `zms_list_app_catalog()` — discovered applications

**Resource group tools (for correlation):**
- `zms_list_resource_groups()` — managed and unmanaged groups
- `zms_get_resource_group_members(group_id)` — members of a group
- `zms_get_resource_group_protection_status()` — group protection coverage

**Not yet available via MCP tools:**
- ML Tag Recommendations (accept/ignore/delete suggestions)
- Tag create/update/delete operations
- Application catalog management
