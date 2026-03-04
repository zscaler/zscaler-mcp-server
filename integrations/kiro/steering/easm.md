# EASM (External Attack Surface Management) Steering

## Overview

EASM provides continuous discovery and monitoring of your organization's external attack surface — internet-facing assets, exposed services, vulnerabilities, misconfigurations, and lookalike domains used for brand impersonation.

## Key Concepts

- **Organizations**: EASM tenant organizations (multi-org support for enterprises)
- **Findings**: Security issues discovered on external assets (exposed services, vulnerabilities, misconfigurations, certificate issues)
- **Lookalike Domains**: Domains registered to impersonate your organization (phishing, brand abuse)
- **Scan Evidence**: Technical proof and raw scan output for each finding
- **Finding Severity**: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL

## Common Workflows

### Full Attack Surface Review

Use for periodic security posture assessments or executive reporting.

```
1. zeasm_list_organizations    → Identify configured organizations
2. zeasm_list_findings         → Get all findings (filter by severity if needed)
3. Group findings by severity:
   - CRITICAL: Immediate action required (exposed admin panels, known CVEs, default credentials)
   - HIGH: Address within 24-48 hours
   - MEDIUM: Address within 1 week
   - LOW: Address during regular maintenance
   - INFORMATIONAL: No immediate action
4. zeasm_list_lookalike_domains → Check for brand impersonation domains
5. Present report: finding counts by severity, top risks, lookalike domain threats
```

### Finding Investigation

Use when drilling into a specific finding for remediation.

```
1. zeasm_list_findings          → Find the relevant finding(s)
2. zeasm_get_finding_details    → Get full context: affected asset, vulnerability details, CVE references
3. zeasm_get_finding_evidence   → Get scan evidence (what the scanner found)
4. zeasm_get_finding_scan_output → Get raw scan data for technical analysis
5. Present: what was found, where it is, how critical it is, suggested remediation
```

### Brand Protection / Lookalike Domain Review

Use for monitoring domain impersonation and phishing threats.

```
1. zeasm_list_lookalike_domains → Get all discovered lookalike domains
2. zeasm_get_lookalike_domain   → Get details for specific domain (registration date, similarity score, hosting info)
3. Assess risk: Is the domain hosting content? Does it mimic login pages? Is it actively used in phishing?
4. Present: domain list, risk assessment, recommended takedown actions
```

### Remediation Tracking

Use for tracking progress on addressing findings.

```
1. zeasm_list_findings     → Get current findings with their status
2. Compare with previous review:
   - New findings since last review
   - Resolved findings
   - Findings that remain open
3. zeasm_get_finding_details → Get updated details for unresolved findings
4. Present: progress summary, remaining risk, newly discovered issues
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zeasm_list_organizations` | List EASM organizations |
| `zeasm_list_findings` | List all security findings |
| `zeasm_get_finding_details` | Get detailed finding information |
| `zeasm_get_finding_evidence` | Get scan evidence for a finding |
| `zeasm_get_finding_scan_output` | Get raw scan output data |
| `zeasm_list_lookalike_domains` | List detected lookalike domains |
| `zeasm_get_lookalike_domain` | Get specific lookalike domain details |

All EASM tools are **read-only**.

## Investigation Report Template

When presenting EASM findings, structure the report as:

1. **Executive Summary** — Total findings, critical count, new since last review
2. **Critical & High Findings** — Detailed list with affected assets and recommended remediation
3. **Exposed Services** — Publicly accessible services that shouldn't be exposed
4. **Certificate Issues** — Expired, self-signed, or misconfigured certificates
5. **Brand Protection** — Lookalike domains, impersonation risk level
6. **Recommendations** — Prioritized remediation actions

## Best Practices

1. **Prioritize by severity** — Always address CRITICAL findings first; they represent active, exploitable risks
2. **Review lookalike domains regularly** — Brand impersonation is time-sensitive; new phishing domains appear constantly
3. **Use evidence for verification** — Before taking remediation action, verify findings using `zeasm_get_finding_evidence` and `zeasm_get_finding_scan_output`
4. **Track remediation progress** — Compare findings across reviews to track which issues have been resolved
5. **Cross-reference with ZIA** — Lookalike domains can be added to ZIA URL blocklists using `zia_add_urls_to_category` for immediate protection
