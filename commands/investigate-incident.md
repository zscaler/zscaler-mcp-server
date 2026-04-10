---
disable-model-invocation: true
argument-hint: "[threat_type_or_keyword] [since_hours]"
description: "Investigate security incidents using Z-Insights analytics -- threats, firewall actions, shadow IT, and web traffic."
---

# Investigate Security Incident

Investigate: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Threat type or keyword** (e.g., "malware", "phishing", "ransomware", a specific IP or domain)
- **Time window** in hours (default: 24)

## Step 2: Check Threat Categories

```text
zins_get_threat_categories()
```text

Identify the most active threat categories in the environment.

## Step 3: Get Cyber Incident Data

```text
zins_get_cyber_incidents()
```text

Look for incidents matching the threat type or keyword.

## Step 4: Analyze Firewall Actions

```text
zins_get_firewall_actions()
zins_get_firewall_insights()
```text

Check for blocks, allows, and suspicious connection patterns.

## Step 5: Review Web Traffic Patterns

```text
zins_get_web_traffic_overview()
zins_get_web_application_usage()
```text

Look for unusual traffic spikes or suspicious application usage.

## Step 6: Check Shadow IT

```text
zins_get_shadow_it_summary()
zins_get_saas_security_posture()
```text

Identify unsanctioned applications that may have been used in the incident.

## Step 7: Present Investigation Report

```text
Security Incident Investigation
==================================

Timeframe: <start> to <end>
Focus: <threat_type>

THREAT SUMMARY:
  Active threat categories: <list>
  Incidents detected: X
  Firewall blocks: Y

INCIDENT TIMELINE:
  <chronological list of events>

AFFECTED ASSETS:
  Users: <list>
  Devices: <list>
  Applications: <list>

FIREWALL ANALYSIS:
  Blocked connections: X
  Allowed suspicious: Y (review needed)

SHADOW IT FINDINGS:
  Unsanctioned apps detected: <list>

ROOT CAUSE ASSESSMENT:
  <analysis>

RECOMMENDED ACTIONS:
  1. <immediate action>
  2. <containment action>
  3. <follow-up investigation>
```text
