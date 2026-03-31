# Z-Insights (Zscaler Business Insights) Steering

## Overview

Z-Insights provides analytics and reporting across Zscaler services — web traffic patterns, cyber security incidents, shadow IT usage, SaaS security posture, firewall activity, and IoT device statistics.

## Key Concepts

- **Web Traffic**: Traffic volume, protocols, and threat categories by location
- **Cyber Security Incidents**: Threat detections including malware, phishing, C2 callbacks
- **Shadow IT**: Unsanctioned SaaS applications discovered in network traffic
- **SaaS Security (CASB)**: Cloud application risk and compliance posture
- **Firewall Analytics**: Firewall actions and network service usage by location
- **IoT Devices**: Connected IoT device inventory and statistics

## Common Workflows

### Security Incident Investigation

Use this when investigating active threats, malware detections, or suspicious activity.

```
1. zins_get_cyber_incidents           → Get incident overview (total threats, categories)
2. zins_get_cyber_incidents_by_location → Identify which locations are affected
3. zins_get_cyber_incidents_daily     → Track incident timeline and trends
4. zins_get_cyber_incidents_by_threat_and_app → Correlate threats with applications
5. zins_get_threat_super_categories   → Understand threat classification breakdown
6. zins_get_threat_class              → Get detailed threat classifications
```

### Web Traffic Analysis

Use this for understanding traffic patterns, bandwidth usage, and protocol distribution.

```
1. zins_get_web_traffic_no_grouping   → Get aggregate web traffic summary
2. zins_get_web_traffic_by_location   → Compare traffic across locations
3. zins_get_web_protocols             → Analyze protocol distribution (HTTP/HTTPS/other)
```

### Shadow IT Discovery

Use this for identifying unsanctioned SaaS applications and assessing their risk.

```
1. zins_get_shadow_it_summary         → Get shadow IT overview (app count, risk scores)
2. zins_get_shadow_it_apps            → List discovered shadow IT applications with details
```

### SaaS Security Posture

```
1. zins_get_casb_app_report           → Get CASB report for monitored cloud applications
```

### Firewall Analytics

```
1. zins_get_firewall_by_action        → Analyze firewall actions (allow/block/drop)
2. zins_get_firewall_by_location      → Compare firewall activity across locations
3. zins_get_firewall_network_services → Identify top network services in firewall traffic
```

### IoT Device Inventory

```
1. zins_get_iot_device_stats          → Get IoT device statistics and categories
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zins_get_web_traffic_no_grouping` | Aggregate web traffic summary |
| `zins_get_web_traffic_by_location` | Web traffic broken down by location |
| `zins_get_web_protocols` | Protocol distribution analysis |
| `zins_get_threat_super_categories` | High-level threat category breakdown |
| `zins_get_threat_class` | Detailed threat classifications |
| `zins_get_cyber_incidents` | Cyber security incident overview |
| `zins_get_cyber_incidents_by_location` | Incidents grouped by location |
| `zins_get_cyber_incidents_daily` | Daily incident timeline |
| `zins_get_cyber_incidents_by_threat_and_app` | Incidents correlated with threat type and app |
| `zins_get_shadow_it_summary` | Shadow IT summary statistics |
| `zins_get_shadow_it_apps` | Discovered shadow IT applications |
| `zins_get_casb_app_report` | CASB cloud application report |
| `zins_get_firewall_by_action` | Firewall activity by action type |
| `zins_get_firewall_by_location` | Firewall activity by location |
| `zins_get_firewall_network_services` | Top network services in firewall traffic |
| `zins_get_iot_device_stats` | IoT device statistics |

All Z-Insights tools are **read-only**.

## Investigation Report Template

When presenting Z-Insights findings, structure the report as:

1. **Executive Summary** — One-paragraph overview of findings
2. **Threat Landscape** — Incident counts, top threat categories, affected locations
3. **Traffic Analysis** — Volume trends, protocol breakdown, anomalies
4. **Shadow IT Risk** — Unsanctioned apps discovered, risk levels
5. **Firewall Activity** — Block/allow ratios, top services, location hotspots
6. **Recommendations** — Prioritized actions based on findings

## Best Practices

1. **Start with incidents** — Check `zins_get_cyber_incidents` first for immediate threats
2. **Correlate across dimensions** — Cross-reference incidents by location, by app, and by day to identify patterns
3. **Shadow IT is time-sensitive** — New unsanctioned apps appear constantly; review regularly
4. **Use location data** — Location-based breakdowns reveal regional issues (branch offices with weak security, remote sites under attack)
5. **Combine with other services** — Z-Insights findings can guide ZIA policy changes (new firewall rules, URL blocks) and ZDX correlation (is the threat affecting user experience?)
