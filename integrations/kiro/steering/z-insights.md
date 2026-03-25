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
1. zinsights_get_cyber_incidents           → Get incident overview (total threats, categories)
2. zinsights_get_cyber_incidents_by_location → Identify which locations are affected
3. zinsights_get_cyber_incidents_daily     → Track incident timeline and trends
4. zinsights_get_cyber_incidents_by_threat_and_app → Correlate threats with applications
5. zinsights_get_threat_super_categories   → Understand threat classification breakdown
6. zinsights_get_threat_class              → Get detailed threat classifications
```

### Web Traffic Analysis

Use this for understanding traffic patterns, bandwidth usage, and protocol distribution.

```
1. zinsights_get_web_traffic_no_grouping   → Get aggregate web traffic summary
2. zinsights_get_web_traffic_by_location   → Compare traffic across locations
3. zinsights_get_web_protocols             → Analyze protocol distribution (HTTP/HTTPS/other)
```

### Shadow IT Discovery

Use this for identifying unsanctioned SaaS applications and assessing their risk.

```
1. zinsights_get_shadow_it_summary         → Get shadow IT overview (app count, risk scores)
2. zinsights_get_shadow_it_apps            → List discovered shadow IT applications with details
```

### SaaS Security Posture

```
1. zinsights_get_casb_app_report           → Get CASB report for monitored cloud applications
```

### Firewall Analytics

```
1. zinsights_get_firewall_by_action        → Analyze firewall actions (allow/block/drop)
2. zinsights_get_firewall_by_location      → Compare firewall activity across locations
3. zinsights_get_firewall_network_services → Identify top network services in firewall traffic
```

### IoT Device Inventory

```
1. zinsights_get_iot_device_stats          → Get IoT device statistics and categories
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zinsights_get_web_traffic_no_grouping` | Aggregate web traffic summary |
| `zinsights_get_web_traffic_by_location` | Web traffic broken down by location |
| `zinsights_get_web_protocols` | Protocol distribution analysis |
| `zinsights_get_threat_super_categories` | High-level threat category breakdown |
| `zinsights_get_threat_class` | Detailed threat classifications |
| `zinsights_get_cyber_incidents` | Cyber security incident overview |
| `zinsights_get_cyber_incidents_by_location` | Incidents grouped by location |
| `zinsights_get_cyber_incidents_daily` | Daily incident timeline |
| `zinsights_get_cyber_incidents_by_threat_and_app` | Incidents correlated with threat type and app |
| `zinsights_get_shadow_it_summary` | Shadow IT summary statistics |
| `zinsights_get_shadow_it_apps` | Discovered shadow IT applications |
| `zinsights_get_casb_app_report` | CASB cloud application report |
| `zinsights_get_firewall_by_action` | Firewall activity by action type |
| `zinsights_get_firewall_by_location` | Firewall activity by location |
| `zinsights_get_firewall_network_services` | Top network services in firewall traffic |
| `zinsights_get_iot_device_stats` | IoT device statistics |

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

1. **Start with incidents** — Check `zinsights_get_cyber_incidents` first for immediate threats
2. **Correlate across dimensions** — Cross-reference incidents by location, by app, and by day to identify patterns
3. **Shadow IT is time-sensitive** — New unsanctioned apps appear constantly; review regularly
4. **Use location data** — Location-based breakdowns reveal regional issues (branch offices with weak security, remote sites under attack)
5. **Combine with other services** — Z-Insights findings can guide ZIA policy changes (new firewall rules, URL blocks) and ZDX correlation (is the threat affecting user experience?)
