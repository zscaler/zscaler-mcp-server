---
name: zins-audit-shadow-it
description: "Audit shadow IT and SaaS application usage using Zscaler Analytics (Z-Insights). Discovers unsanctioned applications, assesses risk scores, monitors CASB-protected SaaS usage, tracks data transfers to shadow apps, and reviews IoT device inventory. Use when a security team asks: 'What shadow IT apps are being used?', 'Show me unsanctioned SaaS usage', 'What is our SaaS risk exposure?', 'How many IoT devices are on our network?', or 'Generate a shadow IT report.'"
---

# Z-Insights: Audit Shadow IT and SaaS Usage

## Keywords
shadow IT, unsanctioned apps, SaaS security, CASB, cloud access, risk score, data exfiltration, SaaS compliance, unauthorized applications, cloud apps, IoT devices, device visibility, shadow IT report, app governance

## Overview

Audit your organization's shadow IT exposure and SaaS application usage using Zscaler Analytics (Z-Insights). This skill discovers unsanctioned applications, assesses their risk, monitors CASB-protected cloud services, tracks data transfers, and inventories IoT devices on the network. Shadow IT represents a significant security and compliance risk -- users adopting cloud applications without IT approval can lead to data leaks, compliance violations, and expanded attack surface.

**Use this skill when:** A security or compliance team needs to discover unauthorized SaaS usage, generate shadow IT risk reports, review CASB findings, assess IoT device sprawl, or support compliance audits (SOC2, ISO 27001, HIPAA).

**Important constraints:**
- Z-Insights only supports **historical data** with a 24-48 hour processing delay
- Shadow IT summary supports time ranges of **1, 7, 15, or 30 days**
- Shadow IT apps supports time ranges up to **30 days**
- CASB supports time ranges up to **90 days**
- IoT device stats show **current state** (no time range needed)

---

## Workflow

Follow this 5-step process to audit shadow IT and SaaS usage.

### Step 1: Understand the Audit Scope

Gather from the requester:
- What is the audit goal? (compliance, risk assessment, incident investigation, routine review)
- Time period to review? (7 days for recent, 14 days for broader view)
- Specific application categories of concern? (file sharing, messaging, AI/ML, storage)
- Compliance framework? (SOC2, ISO 27001, HIPAA, PCI-DSS, GDPR)
- Need IoT device inventory?

---

### Step 2: Get Shadow IT Summary

**Get the overall shadow IT dashboard:**
```
zins_get_shadow_it_summary(
    start_days_ago=16,
    end_days_ago=2
)
```

This returns a comprehensive summary including:
- **total_apps**: Total number of shadow IT applications discovered
- **total_bytes**: Total data transferred to/from shadow apps
- **total_upload_bytes**: Data uploaded (potential data exfiltration)
- **total_download_bytes**: Data downloaded
- **group_by_app_cat_for_app**: Applications grouped by category
- **group_by_risk_index_for_app**: Applications grouped by risk level

Key metrics to highlight:
- Total unsanctioned apps vs sanctioned
- Total data volume (especially uploads -- data exfiltration vector)
- High-risk application count
- Category breakdown (file sharing, messaging, etc.)

---

### Step 3: Discover Shadow IT Applications

**Get detailed shadow IT application list:**
```
zins_get_shadow_it_apps(
    start_days_ago=9,
    end_days_ago=2,
    limit=50
)
```

Each application entry includes:
- **application**: Application name
- **application_category**: Category (file sharing, messaging, social media, etc.)
- **risk_index**: Risk score (higher = more risk)
- **sanctioned_state**: Whether the app is sanctioned by IT
- **data_consumed**: Total data transferred
- **authenticated_users**: Number of users accessing the app

**Prioritize by risk:**
1. **High risk + unsanctioned + high data volume** = Immediate attention
2. **High risk + unsanctioned + low data volume** = Monitor closely
3. **Low risk + unsanctioned + high data volume** = Review data transfers
4. **Sanctioned apps** = Verify compliance and proper configuration

---

### Step 4: Review CASB SaaS Application Usage

**Get CASB application report:**
```
zins_get_casb_app_report(
    start_days_ago=9,
    end_days_ago=2,
    limit=30
)
```

CASB (Cloud Access Security Broker) provides data and threat protection for data at rest in cloud services. This report shows:
- Which SaaS applications are being accessed
- Usage volume per application
- Application adoption trends

Cross-reference CASB data with shadow IT findings to identify:
- Sanctioned apps with unexpected usage patterns
- SaaS applications that should be added to the sanctioned list
- Applications with declining usage (candidates for decommissioning)

---

### Step 5: Inventory IoT Devices

**Get IoT device statistics:**
```
zins_get_iot_device_stats(limit=50)
```

IoT Device Visibility uses AI/ML to automatically detect, identify, and classify IoT devices. Returns:
- **devices_count**: Total devices on the network
- **iot_devices_count**: IoT devices (cameras, printers, sensors, etc.)
- **user_devices_count**: Unmanaged user devices (BYOD)
- **server_devices_count**: Server devices
- **un_classified_devices_count**: Devices not yet classified
- **entries**: Detailed breakdown by device classification

IoT devices represent shadow IT at the hardware level -- unmanaged devices connecting to the corporate network without IT oversight.

---

### Present Audit Report

```
Shadow IT & SaaS Usage Audit Report
=======================================
Date: <current_date>
Period: <start_date> to <end_date>
Requested by: <requester>

## Executive Summary

- **Shadow IT Apps Discovered:** 47 unsanctioned applications
- **Total Data to Shadow Apps:** 12.4 GB (8.1 GB uploaded, 4.3 GB downloaded)
- **High-Risk Applications:** 8 apps with elevated risk scores
- **Users Accessing Shadow IT:** 234 unique users
- **IoT Devices on Network:** 1,847 devices (312 unclassified)
- **Risk Level:** ELEVATED -- 3 critical findings require immediate action

---

## Critical Findings (Immediate Action)

### 1. Unauthorized File Sharing -- file-share-temp.net
- **Risk Score:** 9/10
- **Users:** 45
- **Data Uploaded:** 3.2 GB
- **Category:** File Sharing (unsanctioned)
- **Risk:** Potential data exfiltration -- large uploads to unauthorized service
- **Action:** Block immediately, investigate uploaded content, notify users

### 2. Unmanaged AI/ML Tool -- ai-assistant-free.com
- **Risk Score:** 8/10
- **Users:** 67
- **Data Uploaded:** 1.8 GB
- **Category:** AI/ML (unsanctioned)
- **Risk:** Sensitive data being sent to unvetted AI services
- **Action:** Block, evaluate sanctioned AI alternatives, add to DLP policies

### 3. Unsanctioned Messaging -- secretchat-app.io
- **Risk Score:** 8/10
- **Users:** 23
- **Data Uploaded:** 890 MB
- **Category:** Messaging (unsanctioned)
- **Risk:** Communications outside corporate retention policies
- **Action:** Block, review compliance impact

---

## Shadow IT by Category

| Category         | Apps | Users | Data Volume | Top Risk |
|-----------------|------|-------|------------|----------|
| File Sharing     | 12   | 156   | 5.2 GB     | High     |
| AI/ML Tools      | 8    | 89    | 2.1 GB     | High     |
| Messaging        | 6    | 45    | 1.3 GB     | Medium   |
| Social Media     | 5    | 178   | 890 MB     | Low      |
| Cloud Storage    | 4    | 67    | 1.5 GB     | Medium   |
| Productivity     | 7    | 123   | 980 MB     | Low      |
| Other            | 5    | 34    | 420 MB     | Low      |

---

## Shadow IT by Risk Level

| Risk Level | Apps | % of Total | Action Required        |
|-----------|------|-----------|------------------------|
| Critical   | 3    | 6%        | Block immediately      |
| High       | 5    | 11%       | Review and restrict    |
| Medium     | 14   | 30%       | Monitor and evaluate   |
| Low        | 25   | 53%       | Awareness only         |

---

## CASB SaaS Application Usage

| Application      | Usage Count | Status      | Notes                    |
|-----------------|-------------|-------------|--------------------------|
| Microsoft 365    | 890,000     | Sanctioned  | Primary productivity     |
| Google Workspace | 234,000     | Sanctioned  | Secondary productivity   |
| Salesforce       | 156,000     | Sanctioned  | CRM platform             |
| Slack            | 123,000     | Sanctioned  | Corporate messaging      |
| Dropbox          | 45,000      | Unsanctioned| Migrate to OneDrive      |

---

## IoT Device Inventory

| Device Type         | Count | % of Total | Risk Assessment        |
|--------------------|-------|-----------|------------------------|
| Printers/Scanners   | 450   | 24%       | Low -- managed devices  |
| Security Cameras    | 280   | 15%       | Medium -- verify config |
| Smart TVs/Displays  | 120   | 6%        | Low -- limited access   |
| HVAC/Building       | 95    | 5%        | Medium -- OT network    |
| Unmanaged User      | 590   | 32%       | High -- BYOD devices    |
| Unclassified        | 312   | 17%       | HIGH -- unknown devices |

**312 unclassified devices** require investigation to determine
device type and appropriate network segmentation.

---

## Recommendations

### Immediate (This Week)
1. Block 3 critical-risk shadow IT applications
2. Investigate 3.2 GB of uploads to file-share-temp.net
3. Start classification of 312 unknown IoT devices

### Short-Term (This Month)
4. Create DLP policies for AI/ML tool categories
5. Evaluate sanctioned alternatives for top shadow IT apps
6. Segment IoT devices into dedicated network zones
7. Develop shadow IT acceptable use policy

### Ongoing
8. Schedule monthly shadow IT audits
9. Implement automated alerts for new high-risk app discovery
10. Review IoT device classifications quarterly
```

---

## Edge Cases

### No Shadow IT Detected

```
No shadow IT applications were detected for the specified period.

This could mean:
- Your organization has excellent app governance policies
- URL filtering rules are effectively blocking unsanctioned apps
- The time period may be too narrow -- try a 14-day window

This is a positive finding if app governance policies are in place.
```

### IoT Visibility Not Enabled

```
No IoT device data available.

Possible causes:
- IoT Device Visibility is not licensed or enabled
- No IoT-capable sensors are deployed
- Device classification is still in progress

Action: Verify IoT Device Visibility licensing and sensor deployment.
```

---

## Quick Reference

**Primary workflow:** Scope → Shadow IT Summary → App Details → CASB → IoT → Report

**Shadow IT tools:**
- `zins_get_shadow_it_summary()` -- dashboard overview (totals, categories, risk groups)
- `zins_get_shadow_it_apps()` -- detailed app list with risk scores and data volumes

**CASB tools:**
- `zins_get_casb_app_report()` -- SaaS application usage report

**IoT tools:**
- `zins_get_iot_device_stats()` -- IoT device inventory and classifications

**Time range notes:**
- Shadow IT summary: supports 1, 7, 15, and 30-day ranges
- Shadow IT apps: up to 30 days
- CASB: up to 90 days
- IoT: current state (no time range needed)
