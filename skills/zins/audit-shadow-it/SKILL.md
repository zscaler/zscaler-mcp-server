---
name: zins-audit-shadow-it
description: "Audit shadow IT and SaaS application usage using Zscaler Analytics (Z-Insights). Discovers unsanctioned applications, assesses risk scores, monitors CASB-protected SaaS usage, tracks data transfers to shadow apps, and reviews IoT device inventory. Use when a security team asks: 'What shadow IT apps are being used?', 'Show me unsanctioned SaaS usage', 'What is our SaaS risk exposure?', 'How many IoT devices are on our network?', or 'Generate a shadow IT report.'"
---

# Z-Insights: Audit Shadow IT and SaaS Usage

## Overview

Audits shadow IT exposure and SaaS application usage using Z-Insights. Discovers unsanctioned applications, assesses risk, monitors CASB-protected services, tracks data transfers, and inventories IoT devices.

**Use this skill when:** A security or compliance team needs to discover unauthorized SaaS usage, generate shadow IT risk reports, review CASB findings, assess IoT device sprawl, or support compliance audits (SOC2, ISO 27001, HIPAA).

**Constraints:**

- Z-Insights supports **historical data** only (24-48 hour processing delay)
- Shadow IT summary: **1, 7, 15, or 30 days**
- Shadow IT apps: up to **30 days**
- CASB: up to **90 days**
- IoT device stats: **current state** (no time range)

---

## Workflow

### Step 1: Understand the Audit Scope

Gather from the requester:

- Audit goal (compliance, risk assessment, incident investigation, routine review)
- Time period (7 days for recent, 14 days for broader view)
- Application categories of concern (file sharing, messaging, AI/ML, storage)
- Compliance framework if applicable (SOC2, ISO 27001, HIPAA, PCI-DSS, GDPR)
- Whether IoT device inventory is needed

---

### Step 2: Get Shadow IT Summary

```text
zins_get_shadow_it_summary(
    start_days_ago=16,
    end_days_ago=2
)
```

**Validate:** Confirm the response contains `total_apps` and `group_by_risk_index_for_app`. If the response is empty or returns an error, verify the time range uses supported values (1, 7, 15, or 30 days) and that Z-Insights is licensed.

Highlight: total unsanctioned apps, total data volume (especially uploads as a data exfiltration vector), high-risk application count, and category breakdown.

---

### Step 3: Discover Shadow IT Applications

```text
zins_get_shadow_it_apps(
    start_days_ago=9,
    end_days_ago=2,
    limit=50
)
```

**Validate:** Confirm the response returns application entries with `risk_index` and `sanctioned_state` fields. If empty, widen the time range or reduce filters before concluding no shadow IT exists.

**Prioritize by risk:**

| Risk + Sanctioned State | Data Volume | Action |
|------------------------|-------------|--------|
| High risk + unsanctioned | High | Immediate attention |
| High risk + unsanctioned | Low | Monitor closely |
| Low risk + unsanctioned | High | Review data transfers |
| Sanctioned | Any | Verify compliance |

---

### Step 4: Review CASB SaaS Application Usage

```text
zins_get_casb_app_report(
    start_days_ago=9,
    end_days_ago=2,
    limit=30
)
```

**Validate:** Confirm the response contains application usage entries. If empty, verify CASB is enabled and the time range is within the 90-day limit.

Cross-reference with shadow IT findings to identify sanctioned apps with unexpected usage, candidates for the sanctioned list, and apps with declining usage (decommissioning candidates).

---

### Step 5: Inventory IoT Devices

```text
zins_get_iot_device_stats(limit=50)
```

**Validate:** Confirm the response contains `devices_count` and `entries`. If empty or unavailable, IoT Device Visibility may not be licensed -- note this in the report rather than treating it as an error.

Flag unclassified devices (`un_classified_devices_count`) and unmanaged user devices as areas requiring investigation and network segmentation.

---

### Present Audit Report

Structure the report with these sections:

1. **Executive Summary** -- total shadow IT apps, data volume (upload vs download), high-risk app count, user count, IoT device count, overall risk level
2. **Critical Findings** -- each high-risk unsanctioned app with: risk score, user count, data uploaded, category, risk assessment, recommended action
3. **Shadow IT by Category** -- table of category, app count, user count, data volume, top risk level
4. **Shadow IT by Risk Level** -- table of risk level, app count, percentage, required action
5. **CASB Usage** -- table of sanctioned app usage and status
6. **IoT Inventory** -- table of device types, counts, and risk assessment (if IoT data was collected)
7. **Recommendations** -- prioritized as immediate (block critical apps, investigate large uploads), short-term (DLP policies, sanctioned alternatives, IoT segmentation), and ongoing (monthly audits, automated alerts)

---

## Edge Cases

- **No shadow IT detected:** Report as a positive finding. Suggest widening to a 14-day window to confirm, and note whether app governance policies or URL filtering may explain the result.
- **IoT Visibility not available:** Note in the report that IoT Device Visibility may not be licensed or sensors may not be deployed. Do not treat as a workflow failure.
- **Partial data:** If some API calls succeed but others fail, present available data and clearly note which sections are incomplete.

---

## Quick Reference

| Tool | Purpose | Time Range |
|------|---------|------------|
| `zins_get_shadow_it_summary()` | Dashboard overview (totals, categories, risk groups) | 1, 7, 15, 30 days |
| `zins_get_shadow_it_apps()` | Detailed app list with risk scores and data volumes | Up to 30 days |
| `zins_get_casb_app_report()` | SaaS application usage report | Up to 90 days |
| `zins_get_iot_device_stats()` | IoT device inventory and classifications | Current state |

**Workflow:** Scope → Shadow IT Summary → App Details → CASB → IoT → Report
