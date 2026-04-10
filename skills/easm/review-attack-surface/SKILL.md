---
name: easm-review-attack-surface
description: "Review the organization's external attack surface using Zscaler EASM. Lists organizations, retrieves findings (exposed services, vulnerabilities, misconfigurations), checks for lookalike domains, and generates a prioritized risk summary. Use when a security team asks: 'What is our external exposure?', 'Are there any critical findings?', or 'Check for lookalike domains.'"
---

# EASM: Review Attack Surface

## Keywords

attack surface, external exposure, easm findings, exposed services, vulnerabilities, lookalike domains, external risk, shadow IT discovery, internet-facing assets, security posture, easm audit

## Overview

Review the organization's external attack surface by retrieving EASM findings, analyzing exposed services and vulnerabilities, checking for lookalike domains (phishing indicators), and generating a prioritized risk report. EASM provides visibility into internet-facing assets that may not be known to the security team.

**Use this skill when:** A security administrator wants to review the organization's external exposure, check for new findings, investigate specific vulnerabilities, or detect lookalike domains used for phishing.

---

## Workflow

Follow this 5-step process to review the external attack surface.

### Step 1: List EASM Organizations

```text
zeasm_list_organizations()
```text

EASM can monitor multiple organizations or business units. Note:

- Organization ID and name
- Monitored domains/assets
- Last scan date

If multiple organizations exist, confirm which one to review.

---

### Step 2: Retrieve Findings

```text
zeasm_list_findings(organization_id="<org_id>")
```text

This returns all findings across the attack surface. Each finding includes:

- Finding type (exposed service, vulnerability, misconfiguration, certificate issue)
- Severity (Critical, High, Medium, Low, Informational)
- Asset affected (domain, IP, subdomain)
- Discovery date
- Current status

**For detailed information on a specific finding:**

```text
zeasm_get_finding_details(organization_id="<org_id>", finding_id="<finding_id>")
```text

**For scan evidence:**

```text
zeasm_get_finding_evidence(organization_id="<org_id>", finding_id="<finding_id>")
```text

**For complete scan output:**

```text
zeasm_get_finding_scan_output(organization_id="<org_id>", finding_id="<finding_id>")
```text

---

### Step 3: Check for Lookalike Domains

```text
zeasm_list_lookalike_domains(organization_id="<org_id>")
```text

Lookalike domains are domains registered by third parties that resemble your organization's domains. They are commonly used for:

- Phishing campaigns
- Brand impersonation
- Credential harvesting

**For details on a specific lookalike domain:**

```text
zeasm_get_lookalike_domain(organization_id="<org_id>", domain_id="<domain_id>")
```text

Check:

- Similarity score to your actual domain
- Registration date (recent registrations are higher risk)
- Whether the domain is actively hosting content
- DNS records (MX records suggest email phishing)

---

### Step 4: Categorize and Prioritize

Group findings by severity and type:

**CRITICAL:**

- Exposed databases (MongoDB, Elasticsearch, Redis without auth)
- Known CVEs with active exploitation (CISA KEV)
- Exposed admin panels (phpMyAdmin, Jenkins, Kubernetes dashboard)
- Default credentials detected

**HIGH:**

- SSL/TLS misconfigurations (expired certs, weak ciphers)
- Exposed development/staging environments
- Open mail relays
- Unpatched services with known CVEs

**MEDIUM:**

- Missing security headers (HSTS, CSP, X-Frame-Options)
- Directory listing enabled
- CORS misconfigurations
- Subdomains pointing to unclaimed resources (subdomain takeover risk)

**LOW/INFORMATIONAL:**

- Technology fingerprinting (web server versions)
- DNS zone transfer possible
- Informational banners exposed

---

### Step 5: Generate Report

```text
External Attack Surface Review
================================
Date: <current_date>
Organization: <org_name>

## Executive Summary

- Total findings: X
- Critical: X | High: X | Medium: X | Low: X
- Lookalike domains detected: X
- New findings (last 7 days): X

---

## Critical Findings (Immediate Action Required)

### 1. Exposed MongoDB Instance
- **Asset:** db-backup.company.com:27017
- **Type:** Exposed Database
- **Discovered:** 3 days ago
- **Risk:** Unauthenticated access to database. Data exfiltration possible.
- **Evidence:** Port 27017 open, MongoDB banner detected, no auth required
- **Remediation:** Restrict access via firewall rules. Enable authentication.

### 2. CVE-2024-XXXXX on api.company.com
- **Asset:** api.company.com
- **Type:** Known Vulnerability
- **CVSS:** 9.8
- **Discovered:** 1 week ago
- **Risk:** Remote code execution. Actively exploited in the wild.
- **Evidence:** Service version detected: Apache/2.4.49 (vulnerable)
- **Remediation:** Patch immediately to version 2.4.54+.

---

## High Findings

### 3. Expired SSL Certificate
- **Asset:** portal.company.com
- **Type:** Certificate Issue
- **Discovered:** 2 days ago
- **Risk:** Users see browser warnings. MITM attack possible.
- **Remediation:** Renew certificate immediately.

---

## Lookalike Domains (X detected)

| Domain              | Similarity | Registered | Active | MX Records | Risk  |
|--------------------|-----------|-----------|--------|-----------|-------|
| companny.com       | 95%       | 2 days ago | Yes    | Yes       | HIGH  |
| company-login.net  | 87%       | 1 week ago | Yes    | No        | HIGH  |
| c0mpany.com        | 82%       | 3 months  | No     | No        | MEDIUM|

**companny.com** is actively hosting content and has MX records configured,
suggesting an active phishing campaign. Recommend:
1. Submit to Zscaler URL category as "Phishing"
2. Report to domain registrar for takedown
3. Alert users via security awareness notification

---

## Recommendations (Priority Order)

1. [CRITICAL] Secure exposed MongoDB instance immediately
2. [CRITICAL] Patch Apache on api.company.com
3. [HIGH] Renew SSL certificate for portal.company.com
4. [HIGH] Investigate and report lookalike domain companny.com
5. [MEDIUM] Add security headers to all web applications
6. [LOW] Remove server version banners
```text

---

## Edge Cases

### No Findings

```text
No findings detected for organization "<org_name>".

This means:
- The external attack surface appears clean as of the last scan
- OR EASM monitoring scope may need to be expanded

Recommendation: Verify all known domains and IP ranges are included
in the EASM monitoring scope.
```text

### High Volume of Findings

If there are hundreds of findings:

```text
Large number of findings detected (X total). Showing top 10 by severity.

For a focused review, I can filter by:
1. Severity level (Critical/High only)
2. Finding type (e.g., only exposed services)
3. Specific asset or subdomain
4. Time range (e.g., last 7 days only)

Which filter would you like to apply?
```text

---

## Quick Reference

**Primary workflow:** List Orgs → Retrieve Findings → Check Lookalikes → Categorize → Report

**Tools used:**

- `zeasm_list_organizations()` -- list monitored organizations
- `zeasm_list_findings(organization_id)` -- all findings
- `zeasm_get_finding_details(organization_id, finding_id)` -- finding details
- `zeasm_get_finding_evidence(organization_id, finding_id)` -- scan evidence
- `zeasm_get_finding_scan_output(organization_id, finding_id)` -- full scan output
- `zeasm_list_lookalike_domains(organization_id)` -- lookalike domains
- `zeasm_get_lookalike_domain(organization_id, domain_id)` -- domain details

**Severity classification:**

- CRITICAL: Exposed databases, active CVEs, admin panels
- HIGH: SSL issues, exposed dev environments, unpatched services
- MEDIUM: Missing headers, CORS issues, subdomain takeover risk
- LOW: Version banners, informational findings
