---
name: zinsights-investigate-security-incident
description: "Investigate security incidents using Zscaler Z-Insights analytics. Correlates threat categories, cyber incident trends, firewall actions, web traffic patterns, and shadow IT data to build a comprehensive incident timeline. Use when a security analyst asks: 'What threats were detected?', 'Show me incident trends', 'Investigate this security event', or 'What shadow IT is being used?'"
---

# Z-Insights: Investigate Security Incident

## Keywords
security incident, threat investigation, cyber incident, malware detected, phishing, threat analytics, incident response, shadow IT, threat trends, firewall blocks, web traffic anomaly, security analytics

## Overview

Investigate security incidents by correlating multiple Z-Insights data sources: threat categories, cyber incident logs, firewall actions, web traffic patterns, and shadow IT discovery. This skill builds a timeline and context around security events to support incident response and threat hunting.

**Use this skill when:** A security analyst needs to investigate detected threats, analyze incident trends, understand the scope of a security event, or review shadow IT and CASB findings.

---

## Workflow

Follow this 6-step process to investigate a security incident.

### Step 1: Understand the Incident Scope

Gather from the analyst:
- What type of event? (malware, phishing, data exfiltration, policy violation, anomalous traffic)
- When did it occur or when was it detected?
- Specific user, location, or application involved?
- Alert or ticket reference number?

---

### Step 2: Check Threat Analytics

**Get threat super categories:**
```
zinsights_get_threat_super_categories()
```

This returns high-level threat categories (malware, phishing, spyware, command & control, etc.) with counts. Identify which category the incident falls under.

**Get detailed threat classifications:**
```
zinsights_get_threat_class()
```

This breaks down threats into specific types (virus, trojan, ransomware, exploit kit, cryptominer, etc.). Look for spikes or anomalies in the relevant class.

---

### Step 3: Analyze Cyber Incidents

**Get incident overview:**
```
zinsights_get_cyber_incidents()
```

**Get incidents by location to identify the source:**
```
zinsights_get_cyber_incidents_by_location()
```

**Get daily trends to identify when the incident started:**
```
zinsights_get_cyber_incidents_daily()
```

Look for:
- Sudden spikes in specific incident categories
- Geographic concentration (specific offices or regions)
- Correlation between incident start time and reported symptoms

**Get incidents correlated by threat and application:**
```
zinsights_get_cyber_incidents_by_threat_and_app()
```

This shows which applications are associated with which threats -- critical for understanding the attack vector.

---

### Step 4: Review Firewall and Traffic Data

**Check firewall actions:**
```
zinsights_get_firewall_by_action()
```

Look for:
- Spike in BLOCK actions (indicates active threat mitigation)
- Changes in ALLOW vs BLOCK ratios
- New blocked categories

**Check firewall by location:**
```
zinsights_get_firewall_by_location()
```

**Check web traffic patterns:**
```
zinsights_get_web_traffic_by_location()
zinsights_get_web_traffic_no_grouping()
```

Look for anomalous traffic volumes that might indicate:
- Data exfiltration (unusual outbound volume)
- Command & control beaconing (regular small requests)
- DDoS participation (high outbound traffic to specific destinations)

**Check protocol distribution:**
```
zinsights_get_web_protocols()
```

Unusual protocol distribution (e.g., spike in non-HTTPS traffic) may indicate malware communicating over unencrypted channels.

---

### Step 5: Check Shadow IT and CASB

**Review CASB app usage:**
```
zinsights_get_casb_app_report()
```

**Discover shadow IT applications:**
```
zinsights_get_shadow_it_apps()
zinsights_get_shadow_it_summary()
```

Shadow IT applications are unsanctioned SaaS tools that may be:
- Data exfiltration vectors
- Sources of credential compromise
- Compliance violations

Check if the incident involves any unsanctioned applications.

---

### Step 6: Generate Incident Report

```
Security Incident Investigation Report
========================================
Date: <current_date>
Investigator: AI Assistant
Reference: <ticket_number>

## Incident Summary

- **Type:** <Malware / Phishing / Data Exfiltration / Policy Violation>
- **Severity:** <Critical / High / Medium / Low>
- **Detection Time:** <timestamp>
- **Status:** <Active / Contained / Resolved>

---

## Timeline

| Time          | Event                                          | Source     |
|---------------|------------------------------------------------|-----------|
| 09:15 UTC     | First malware detection (Trojan.GenericKD)     | Threats    |
| 09:15-09:45   | 47 additional detections from same location    | Threats    |
| 09:30 UTC     | Firewall block spike: 340% above baseline      | Firewall   |
| 09:45 UTC     | Anomalous outbound traffic to unknown IPs       | Traffic    |
| 10:00 UTC     | Security team alerted                           | Manual     |

---

## Threat Analysis

**Threat Category:** Malware → Trojan
- Super Category: Malware (↑ 280% from baseline)
- Classification: Trojan.GenericKD
- Variant: Known payload, first seen in wild 2 weeks ago

**Affected Applications:**
- browser-plugin-update.com (uncategorized domain)
- file-share-temp.net (file sharing application)

**Geographic Distribution:**
- 85% of detections from New York office
- 10% from San Francisco office
- 5% from remote workers

---

## Firewall Response

- Block actions: 523 (↑ 340% from daily average)
- Blocked destinations: 12 unique IPs
- Blocked protocols: HTTP (port 80), custom (port 8443)
- Firewall rules triggered:
  - "Block Known C2 Domains" (287 blocks)
  - "Block Uncategorized Outbound" (236 blocks)

---

## Traffic Anomalies

- Outbound traffic spike: 4.2 GB above normal for this time window
- 67% of anomalous traffic targeted 3 external IP addresses
- Protocol: HTTPS (port 443) — may indicate encrypted C2 channel

---

## Shadow IT Involvement

- **file-share-temp.net** is an unsanctioned file sharing service
  - Risk score: High
  - 12 users accessed this application in the past 24 hours
  - Not in the sanctioned application list
  - Likely initial infection vector

---

## Recommendations

### Immediate (Containment)
1. Block all identified C2 IP addresses at the firewall
2. Isolate affected devices in the New York office
3. Force password reset for users who accessed file-share-temp.net

### Short-Term (Eradication)
4. Run endpoint scans on all devices in the New York office
5. Add file-share-temp.net to the URL blocklist
6. Review and block similar uncategorized file sharing domains

### Long-Term (Prevention)
7. Create a URL filtering rule to block uncategorized file sharing sites
8. Enable SSL inspection for uncategorized domains
9. Implement DLP rules to detect and block sensitive data uploads to
   unsanctioned applications
10. Add shadow IT discovery findings to monthly security review
```

---

## Quick Reference

**Primary workflow:** Scope → Threats → Incidents → Firewall/Traffic → Shadow IT → Report

**Threat tools:**
- `zinsights_get_threat_super_categories()` -- high-level threat categories
- `zinsights_get_threat_class()` -- detailed threat classifications

**Incident tools:**
- `zinsights_get_cyber_incidents()` -- incident overview
- `zinsights_get_cyber_incidents_by_location()` -- incidents by location
- `zinsights_get_cyber_incidents_daily()` -- daily trends
- `zinsights_get_cyber_incidents_by_threat_and_app()` -- threat-app correlation

**Firewall tools:**
- `zinsights_get_firewall_by_action()` -- allow/block distribution
- `zinsights_get_firewall_by_location()` -- firewall events by location
- `zinsights_get_firewall_network_services()` -- network service usage

**Traffic tools:**
- `zinsights_get_web_traffic_by_location()` -- traffic by location
- `zinsights_get_web_traffic_no_grouping()` -- total traffic volume
- `zinsights_get_web_protocols()` -- protocol distribution

**Shadow IT tools:**
- `zinsights_get_casb_app_report()` -- CASB application report
- `zinsights_get_shadow_it_apps()` -- discovered shadow IT apps
- `zinsights_get_shadow_it_summary()` -- shadow IT summary
