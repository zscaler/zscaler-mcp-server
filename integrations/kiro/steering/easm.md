# EASM (External Attack Surface Management) Steering

## Overview

EASM provides continuous discovery and monitoring of your organization's external attack surface, identifying vulnerabilities and risks in internet-facing assets.

## Key Concepts

- **Organizations**: EASM tenant organizations
- **Findings**: Security issues discovered on external assets
- **Lookalike Domains**: Domains that impersonate your organization
- **Scan Evidence**: Proof and context for findings

## Common Workflows

### Security Posture Review
```
1. zeasm_list_organizations - Get configured organizations
2. zeasm_list_findings - Review all findings
3. zeasm_get_finding_details - Investigate specific finding
4. zeasm_get_finding_evidence - View scan evidence
```

### Brand Protection
```
1. zeasm_list_lookalike_domains - Find impersonating domains
2. zeasm_get_lookalike_domain - Get domain details
```

### Finding Investigation
```
1. zeasm_list_findings - Filter by severity/type
2. zeasm_get_finding_details - Get full finding context
3. zeasm_get_finding_evidence - Review technical evidence
4. zeasm_get_finding_scan_output - Get raw scan data
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zeasm_list_organizations` | List EASM organizations |
| `zeasm_list_findings` | List all findings |
| `zeasm_get_finding_details` | Get finding details |
| `zeasm_get_finding_evidence` | Get scan evidence for finding |
| `zeasm_get_finding_scan_output` | Get complete scan output |
| `zeasm_list_lookalike_domains` | List lookalike domains |
| `zeasm_get_lookalike_domain` | Get lookalike domain details |

## Finding Severity Levels

- **Critical**: Immediate action required
- **High**: Address within 24-48 hours
- **Medium**: Address within 1 week
- **Low**: Address during regular maintenance
- **Informational**: No immediate action needed

## Best Practices

1. **Prioritize by severity** - Address critical findings first
2. **Review lookalike domains regularly** - Brand impersonation is time-sensitive
3. **Document remediation** - Track finding resolution progress
4. **Use evidence for context** - Understand the full scope of findings

