---
name: review-attack-surface
disable-model-invocation: true
argument-hint: "[organization_name] [focus: findings|lookalikes|all]"
description: "Review external attack surface using Zscaler EASM findings, exposed services, and lookalike domains."
---

# Review Attack Surface

Review attack surface: **$ARGUMENTS**

## Step 1: List Organizations

```text
easm_list_organizations()
```text

If an organization was specified, find its ID. Otherwise, use the primary organization.

## Step 2: Retrieve Findings

```text
easm_list_findings(organization_id="<id>")
```text

## Step 3: Analyze Findings by Severity

Categorize findings:

- **Critical**: Exploitable vulnerabilities, exposed admin panels, default credentials
- **High**: Exposed services (RDP, SSH, databases), expired certificates
- **Medium**: Misconfigurations, information disclosure
- **Low**: Best-practice improvements

## Step 4: Check Lookalike Domains

```text
easm_list_lookalike_domains(organization_id="<id>")
```text

Flag domains that could be used for phishing or brand impersonation.

## Step 5: Get Detailed Finding Info

For critical/high findings:

```text
easm_get_finding(finding_id="<id>")
```text

## Step 6: Present Report

```text
External Attack Surface Report
================================

Organization: <name>
Scan date: <date>

FINDINGS SUMMARY:
  Critical: X
  High: Y
  Medium: Z
  Low: W

CRITICAL FINDINGS:
  1. <finding_type>: <asset>
     Risk: <description>
     Remediation: <steps>

HIGH FINDINGS:
  1. ...

LOOKALIKE DOMAINS:
  - <domain> (similarity: X%) -- potential phishing
  - <domain> (similarity: Y%) -- registered <date>

PRIORITY REMEDIATION:
  1. <most urgent action>
  2. <next action>
```text
