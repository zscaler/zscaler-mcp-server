---
name: zins-assess-network-security
description: "Assess network security posture using Zscaler Analytics (Z-Insights). Analyzes Zero Trust Firewall effectiveness by action distribution (allow/block ratios), location-based firewall activity, network service usage, and firewall rule hit counts. Use when a security team asks: 'How effective is our firewall?', 'What is being blocked?', 'Show firewall activity by location', 'Which network services are in use?', or 'Generate a firewall report.'"
---

# Z-Insights: Assess Network Security Posture

## Keywords
firewall analytics, zero trust firewall, firewall effectiveness, allow block ratio, firewall by location, network services, firewall rules, policy hits, firewall report, security posture, network security, blocked traffic, firewall monitoring

## Overview

Assess your organization's network security posture by analyzing Zero Trust Firewall data through Zscaler Analytics (Z-Insights). This skill examines firewall action distribution (allow vs block), traffic patterns by location, network service usage, and firewall rule hit counts to evaluate policy effectiveness and identify gaps.

Zscaler's Zero Trust Firewall protects web and non-web traffic for all users, applications, and locations with the industry's most comprehensive cloud-native Security Service Edge (SSE) platform. This analysis covers both inbound and outbound traffic enforcement.

**Use this skill when:** A security or network team needs to evaluate firewall policy effectiveness, investigate blocked traffic patterns, review network service usage, or generate firewall compliance reports.

**Important constraints:**
- Z-Insights only supports **historical data** with a 24-48 hour processing delay
- Time ranges must be exactly **7 or 14 days**
- All firewall queries support time ranges up to **90 days**

---

## Workflow

Follow this 5-step process to assess network security posture.

### Step 1: Understand the Assessment Goal

Gather from the requester:
- What is the goal? (policy effectiveness, compliance audit, incident investigation, baseline review)
- Time period? (7 days for recent, 14 days for trends)
- Specific locations of interest?
- Are there known policy changes to evaluate?
- Compare with a previous period?

---

### Step 2: Analyze Firewall Action Distribution

**Get firewall traffic by action (allow/block):**
```
zins_get_firewall_by_action(
    start_days_ago=9,
    end_days_ago=2,
    limit=10
)
```

This shows how much traffic is being allowed versus blocked. Key metrics:
- **Block ratio**: What percentage of traffic is being blocked?
  - < 1%: Very permissive -- review if policies are too loose
  - 1-5%: Typical for well-tuned policies
  - 5-15%: Active enforcement -- verify legitimate traffic isn't impacted
  - \> 15%: Aggressive blocking -- check for false positives
- **Trend**: Is the block ratio increasing or decreasing?
- **Volume**: Absolute block counts indicate threat exposure

---

### Step 3: Analyze Firewall Activity by Location

**Get firewall traffic by location:**
```
zins_get_firewall_by_location(
    start_days_ago=9,
    end_days_ago=2,
    limit=20
)
```

This identifies which locations generate the most firewall traffic. Look for:
- **Disproportionate traffic**: A small office generating more firewall hits than headquarters
- **Location anomalies**: Sudden spikes at specific locations
- **Geographic patterns**: High firewall activity in regions with known threat activity
- **Remote worker impact**: Firewall activity from remote/roaming users

Cross-reference with web traffic by location to calculate per-location block ratios.

---

### Step 4: Analyze Network Service Usage

**Get firewall traffic by network service:**
```
zins_get_firewall_network_services(
    start_days_ago=9,
    end_days_ago=2,
    limit=30
)
```

Network services represent protocol/port combinations in your traffic. Look for:
- **Expected services**: HTTP (80), HTTPS (443), DNS (53) should dominate
- **Unusual services**: Unexpected ports or protocols may indicate:
  - Malware communication (non-standard ports)
  - Unauthorized applications (VPN tunnels, P2P)
  - Misconfigured applications
  - Shadow IT network activity
- **Deprecated protocols**: Telnet (23), FTP (21) -- should be blocked
- **High-risk ports**: RDP (3389), SMB (445) from external sources

---

### Step 5: Correlate with Cyber Incident Data

**Get cybersecurity incident overview:**
```
zins_get_cyber_incidents(
    start_days_ago=16,
    end_days_ago=2,
    categorize_by=["THREAT_CATEGORY_ID"],
    limit=20
)
```

**Get incidents by location to identify hotspots:**
```
zins_get_cyber_incidents_by_location(
    start_days_ago=16,
    end_days_ago=2,
    categorize_by="LOCATION_ID",
    limit=20
)
```

Correlate firewall blocks with actual security incidents:
- High blocks + high incidents = Active threat targeting
- High blocks + low incidents = Firewall preventing threats effectively
- Low blocks + high incidents = Possible policy gaps
- Low blocks + low incidents = Clean environment or insufficient visibility

---

### Present Assessment

```
Network Security Posture Assessment
=======================================
Date: <current_date>
Period: <start_date> to <end_date>
Assessment Type: <compliance / routine / incident-driven>

## Executive Summary

- **Total Firewall Transactions:** X,XXX,XXX
- **Allowed:** X,XXX,XXX (XX%)
- **Blocked:** XX,XXX (X.X%)
- **Block Ratio Assessment:** Within normal range / Needs review
- **Locations Analyzed:** XX
- **Network Services Detected:** XX
- **Security Incidents:** XXX
- **Overall Posture:** STRONG / ADEQUATE / NEEDS IMPROVEMENT

---

## Firewall Action Summary

| Action   | Count       | Percentage | Assessment           |
|----------|------------|-----------|---------------------|
| ALLOW    | 2,340,000  | 96.2%     | Normal               |
| BLOCK    | 92,500     | 3.8%      | Active enforcement   |

Block ratio of 3.8% is within the typical 1-5% range for
well-tuned policies, indicating effective enforcement without
excessive false positives.

---

## Firewall Activity by Location (Top 10)

| Rank | Location          | Total Traffic | Blocked | Block % | Status    |
|------|------------------|--------------|---------|---------|-----------|
| 1    | New York HQ       | 890,000      | 34,000  | 3.8%    | Normal    |
| 2    | San Francisco     | 456,000      | 22,000  | 4.8%    | Normal    |
| 3    | London            | 234,000      | 18,000  | 7.7%    | ELEVATED  |
| 4    | Singapore         | 189,000      | 4,500   | 2.4%    | Normal    |
| ...  | ...               | ...          | ...     | ...     | ...       |

**London office** shows elevated block ratio (7.7% vs 3.8% average).
Investigate whether this reflects targeted threats or overly
restrictive policies for that location.

---

## Network Services (Top 15)

| Service         | Port  | Traffic Count | % of Total | Risk     |
|----------------|-------|--------------|-----------|----------|
| HTTPS           | 443   | 1,890,000    | 77.6%     | Low      |
| HTTP            | 80    | 290,000      | 11.9%     | Medium   |
| DNS             | 53    | 145,000      | 6.0%      | Low      |
| SMTP            | 25    | 23,000       | 0.9%      | Low      |
| SSH             | 22    | 12,000       | 0.5%      | Medium   |
| RDP             | 3389  | 8,500        | 0.3%      | HIGH     |
| FTP             | 21    | 2,300        | 0.1%      | HIGH     |
| Unknown         | 8443  | 1,800        | 0.1%      | REVIEW   |

**Findings:**
- RDP traffic (3389): 8,500 transactions -- verify these are
  authorized remote desktop sessions only
- FTP traffic (21): 2,300 transactions -- FTP is unencrypted;
  migrate to SFTP (22) or FTPS
- Unknown (8443): 1,800 transactions on non-standard port --
  investigate source applications

---

## Security Incident Correlation

| Category           | Incidents | Firewall Blocks | Effectiveness |
|-------------------|-----------|----------------|--------------|
| Malware            | 234       | 45,000         | 99.5% caught  |
| Phishing           | 189       | 28,000         | 99.3% caught  |
| Command & Control  | 45        | 12,000         | 99.6% caught  |
| Data Exfiltration  | 12        | 3,200          | 99.6% caught  |

Firewall effectiveness is strong across all threat categories.

---

## Recommendations

### Immediate
1. Investigate RDP traffic -- ensure all sessions are authorized
2. Block FTP (port 21) and migrate to SFTP
3. Investigate unknown traffic on port 8443

### Short-Term
4. Review London office elevated block ratio
5. Create firewall rules for newly detected network services
6. Audit SSH access permissions

### Ongoing
7. Schedule monthly firewall effectiveness reviews
8. Track block ratio trends for anomaly detection
9. Review network service inventory quarterly
```

---

## Edge Cases

### Very Low Block Ratio (< 0.5%)

```
Firewall block ratio is unusually low at X.X%.

This could indicate:
- Policies are too permissive
- Traffic inspection is not enabled for all protocols
- Users are bypassing the firewall (split tunnel VPN)
- The environment is genuinely clean

Recommendation: Review firewall rule coverage and ensure all
traffic types are being inspected.
```

### Very High Block Ratio (> 15%)

```
Firewall block ratio is elevated at XX.X%.

This could indicate:
- An active security incident or attack
- Recently deployed restrictive policies
- Misconfigured policies causing false positives
- Legitimate applications being incorrectly blocked

Recommendation: Review recently changed firewall rules and
check if users are reporting access issues.
```

---

## Quick Reference

**Primary workflow:** Scope → Action Distribution → Locations → Network Services → Incidents → Report

**Firewall tools:**
- `zins_get_firewall_by_action()` -- allow/block traffic distribution
- `zins_get_firewall_by_location()` -- firewall activity by location
- `zins_get_firewall_network_services()` -- network service/port usage

**Incident tools (for correlation):**
- `zins_get_cyber_incidents()` -- incident overview by category
- `zins_get_cyber_incidents_by_location()` -- incidents by location
- `zins_get_cyber_incidents_daily()` -- daily incident trends
- `zins_get_cyber_incidents_by_threat_and_app()` -- threat-app correlation

**Key metrics to track:**
- Block ratio: Target 1-5% for well-tuned policies
- Location anomalies: Per-location block ratios that deviate from average
- Network services: Unexpected ports or deprecated protocols
- Incident correlation: High blocks with low incidents = effective policies
