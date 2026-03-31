---
name: zins-analyze-web-traffic
description: "Analyze web traffic patterns using Zscaler Analytics (Z-Insights). Examines traffic distribution by location, protocol breakdown (HTTP vs HTTPS), threat categories, DLP violations, and volume trends over time. Use when an administrator asks: 'Show me web traffic by location', 'What protocols are in use?', 'Are there any DLP violations?', 'What does our traffic look like?', or 'Show traffic trends.'"
---

# Z-Insights: Analyze Web Traffic Patterns

## Keywords
web traffic, traffic analytics, traffic by location, protocol distribution, HTTP HTTPS, DLP violations, traffic volume, traffic trends, bandwidth, capacity planning, web analytics, traffic report, data loss prevention

## Overview

Analyze web traffic across your organization using the Zscaler Analytics (Z-Insights) GraphQL API. This skill retrieves traffic data by location, protocol distribution, threat categories, and overall volume. It supports DLP filtering, trend analysis, and allows measurement in transactions or bytes.

**Use this skill when:** An administrator or security analyst needs to understand web traffic patterns, plan capacity, monitor protocol adoption (e.g., HTTPS migration), investigate DLP policy violations, or generate traffic reports for specific time periods.

**Important constraints:**
- Z-Insights only supports **historical data** with a 24-48 hour processing delay
- Time ranges must be exactly **7 or 14 days** (the API enforces this)
- Use `start_days_ago` / `end_days_ago` (recommended) or epoch milliseconds
- Set `end_days_ago` to at least **2** to ensure data availability

---

## Workflow

Follow this 5-step process to analyze web traffic.

### Step 1: Understand the Analysis Request

Gather from the analyst:
- What aspect of traffic? (volume, locations, protocols, threats, DLP)
- What time period? (past week = 7 days, past two weeks = 14 days)
- Measurement unit? (TRANSACTIONS for request counts, BYTES for bandwidth)
- Any specific filters? (DLP engine, allow/block actions)
- Need trend data? (daily or hourly granularity)

---

### Step 2: Analyze Traffic by Location

**Get web traffic distribution across locations:**
```
zins_get_web_traffic_by_location(
    start_days_ago=9,
    end_days_ago=2,
    traffic_unit="TRANSACTIONS",
    limit=20
)
```

This identifies which offices, branches, or regions generate the most web traffic. Look for:
- Top traffic-generating locations (potential bandwidth bottlenecks)
- Unusual traffic spikes at specific locations
- Remote vs office traffic distribution

**With trend data for capacity planning:**
```
zins_get_web_traffic_by_location(
    start_days_ago=9,
    end_days_ago=2,
    traffic_unit="BYTES",
    include_trend=True,
    trend_interval="DAY",
    limit=10
)
```

---

### Step 3: Analyze Protocol Distribution

**Get protocol breakdown:**
```
zins_get_web_protocols(
    start_days_ago=9,
    end_days_ago=2,
    traffic_unit="TRANSACTIONS",
    limit=20
)
```

Evaluate:
- **HTTPS adoption**: What percentage of traffic is encrypted?
- **HTTP traffic**: Remaining unencrypted traffic may indicate legacy applications or misconfigured services
- **Other protocols**: SSL, FTP over HTTP, WebSocket, etc.
- **Anomalies**: Unexpected protocol usage may indicate malware or policy bypass

---

### Step 4: Analyze Overall Traffic Volume and DLP

**Get total traffic volume (no grouping):**
```
zins_get_web_traffic_no_grouping(
    start_days_ago=9,
    end_days_ago=2,
    traffic_unit="TRANSACTIONS"
)
```

**Filter by DLP violations:**
```
zins_get_web_traffic_no_grouping(
    start_days_ago=9,
    end_days_ago=2,
    dlp_engine_filter="PCI",
    traffic_unit="TRANSACTIONS"
)
```

Available DLP engine filters:
- `ANY` -- any DLP engine triggered
- `NONE` -- no DLP engine triggered
- `HIPAA` -- healthcare data violations
- `PCI` -- payment card data violations
- `GLBA` -- financial data violations
- `CYBER_BULLY_ENG` -- cyberbullying content
- `OFFENSIVE_LANGUAGE` -- offensive content
- `EXTERNAL` -- external DLP engine

**Filter by action:**
```
zins_get_web_traffic_no_grouping(
    start_days_ago=9,
    end_days_ago=2,
    action_filter="BLOCK",
    traffic_unit="TRANSACTIONS"
)
```

**Get volume trends over time:**
```
zins_get_web_traffic_no_grouping(
    start_days_ago=9,
    end_days_ago=2,
    include_trend=True,
    trend_interval="DAY",
    traffic_unit="BYTES"
)
```

---

### Step 5: Check Threat Activity in Web Traffic

**Get threat super categories:**
```
zins_get_threat_super_categories(
    start_days_ago=9,
    end_days_ago=2,
    traffic_unit="TRANSACTIONS",
    limit=20
)
```

This shows high-level threat categories (malware, phishing, spyware, C2, etc.) detected in web traffic.

**Get detailed threat classifications:**
```
zins_get_threat_class(
    start_days_ago=9,
    end_days_ago=2,
    traffic_unit="TRANSACTIONS",
    limit=20
)
```

This breaks threats into specific types (virus, trojan, ransomware, exploit kit, cryptominer, etc.).

---

### Present Analysis

```
Web Traffic Analysis Report
=============================
Date: <current_date>
Period: <start_date> to <end_date> (7-day / 14-day interval)

## Traffic Summary

- **Total Transactions:** X,XXX,XXX
- **Total Data Volume:** XX.X GB
- **Blocked Transactions:** X,XXX (X.X% of total)
- **DLP Violations:** X,XXX

---

## Traffic by Location (Top 10)

| Rank | Location             | Transactions | % of Total | Trend      |
|------|---------------------|-------------|-----------|------------|
| 1    | New York HQ          | 450,000     | 32%       | Stable     |
| 2    | San Francisco        | 280,000     | 20%       | ↑ 15%      |
| 3    | London               | 195,000     | 14%       | Stable     |
| ...  | ...                  | ...         | ...       | ...        |

---

## Protocol Distribution

| Protocol | Transactions | % of Total | Assessment        |
|----------|-------------|-----------|-------------------|
| HTTPS    | 1,200,000   | 87%       | Good adoption     |
| HTTP     | 140,000     | 10%       | Review needed     |
| SSL      | 35,000      | 2.5%      | Normal            |
| Other    | 7,000       | 0.5%      | Monitor           |

HTTPS adoption at 87% -- target is 95%+. HTTP traffic sources
should be investigated for possible migration to HTTPS.

---

## Threat Detections

| Category         | Count  | Trend vs Previous |
|-----------------|--------|-------------------|
| Malware          | 2,340  | ↑ 12%             |
| Phishing         | 1,890  | ↓ 5%              |
| Spyware          | 890    | Stable            |
| Adware           | 567    | ↓ 20%             |

---

## DLP Summary

| DLP Engine | Violations | Action  |
|-----------|-----------|---------|
| PCI        | 145       | Blocked |
| HIPAA      | 89        | Blocked |
| GLBA       | 23        | Blocked |

---

## Recommendations

1. Investigate HTTP traffic sources for HTTPS migration
2. Review the 12% increase in malware detections
3. <location> shows unusual traffic spike -- verify with local IT
4. PCI violations trending up -- review DLP policy exceptions
```

---

## Edge Cases

### No Data Returned

```
Z-Insights returned no data for the specified time range.

Possible causes:
- Z-Insights/Business Insights may not be licensed for this tenant
- The time range may be outside the supported window
- Data has a 24-48 hour processing delay

Action: Verify Z-Insights licensing and try a time range ending
at least 2 days ago.
```

### Time Range Errors

```
The Z-Insights API requires time intervals of exactly 7 or 14 days.

Use these parameter combinations:
- 7-day: start_days_ago=9, end_days_ago=2
- 14-day: start_days_ago=16, end_days_ago=2

The tool auto-adjusts intervals when using days_ago parameters.
```

---

## Quick Reference

**Primary workflow:** Scope → Locations → Protocols → Volume/DLP → Threats → Report

**Traffic tools:**
- `zins_get_web_traffic_by_location()` -- traffic distribution by location
- `zins_get_web_traffic_no_grouping()` -- overall traffic volume with DLP and action filters
- `zins_get_web_protocols()` -- protocol distribution (HTTP, HTTPS, SSL, etc.)

**Threat tools:**
- `zins_get_threat_super_categories()` -- high-level threat categories
- `zins_get_threat_class()` -- detailed threat classifications

**Common parameters:**
- `start_days_ago` / `end_days_ago` -- recommended time range specification
- `traffic_unit` -- TRANSACTIONS (request counts) or BYTES (data volume)
- `include_trend` / `trend_interval` -- enable time series data (DAY or HOUR)
- `dlp_engine_filter` -- filter by DLP engine (PCI, HIPAA, GLBA, etc.)
- `action_filter` -- filter by action (ALLOW, BLOCK)
- `limit` -- max results (1-1000)
