---
name: audit-ssl
disable-model-invocation: true
argument-hint: "<question about SSL rules> [e.g., 'which rules are in decryption mode', 'show bypass exceptions', 'audit all SSL rules']"
description: "Audit ZIA SSL inspection rules -- list rules by action (INSPECT, DO_NOT_INSPECT, DO_NOT_DECRYPT, BLOCK), identify bypasses, and assess risk."
---

# Audit SSL Inspection Rules

Audit SSL inspection: **$ARGUMENTS**

## Scope

This command works EXCLUSIVELY with SSL inspection rules. Do NOT call URL filtering, DLP, firewall, or any other non-SSL tools unless the user explicitly asks for cross-referencing.

## Step 1: Retrieve SSL Inspection Rules

```text
zia_list_ssl_inspection_rules()
```text

## Step 2: Filter and Categorize

Categorize each rule by its action:

- **INSPECT / DECRYPT** -- traffic is fully decrypted and inspected
- **DO_NOT_INSPECT** -- traffic is not decrypted or inspected (full bypass)
- **DO_NOT_DECRYPT** -- traffic is not decrypted but metadata is visible
- **BLOCK** -- traffic is blocked at the SSL layer

Filter results based on the user's question. If they ask about "decryption mode," show only INSPECT/DECRYPT rules. If they ask about "bypasses," show DO_NOT_INSPECT and DO_NOT_DECRYPT rules.

## Step 3: Analyze Rule Details

For each relevant rule, present:

- Rule name, order, enabled status
- URL categories and cloud applications affected
- Users, groups, departments, locations scoped
- Platforms and device trust levels

Resolve IDs to names only when needed:

```text
get_zia_user_groups(search="<name>")
get_zia_user_departments(search="<name>")
zia_list_locations()
```text

## Step 4: Risk Assessment (bypass audits only)

If auditing bypasses, classify by risk:

- **Critical**: Broad categories (Uncategorized, Miscellaneous), all users, AI/ML apps bypassed
- **High**: Sensitive cloud apps, large departments bypassed
- **Medium**: Certificate-pinning exceptions, narrow user scope
- **Low**: OS updates, system services, high-trust device scoping

## Step 5: Present Report

Organize findings to directly answer the user's question. Include:

- Summary counts by action type
- Detailed rule list (filtered to what the user asked about)
- Risk assessment and recommendations (for bypass audits)

## Important: Do NOT Call These Tools

Unless the user explicitly asks for DLP or URL filtering cross-reference:

- Do NOT call `zia_list_url_filtering_rules()`
- Do NOT call `zia_list_web_dlp_rules()` or `zia_list_web_dlp_rules_lite()`
- Do NOT call `zia_list_firewall_rules()`
- Do NOT call any tool unrelated to SSL inspection
