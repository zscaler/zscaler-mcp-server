---
name: zia-audit-ssl-inspection-bypass
description: "Audit ZIA SSL inspection rules to identify which applications, URL categories, users, or groups are subject to INSPECT, DO_NOT_INSPECT, or DO_NOT_DECRYPT actions. This skill focuses exclusively on SSL inspection rules and their configuration. Use when a security administrator asks: 'What SSL rules are in decryption mode?', 'What is bypassing SSL inspection?', 'Are there SSL bypass exceptions?', or 'Audit our SSL inspection policy.'"
---

# ZIA: Audit SSL Inspection Bypass

## Keywords

ssl inspection, ssl bypass, do not inspect, do not decrypt, ssl exceptions, ssl audit, ssl security gap, bypass ssl, inspection exclusion, ssl policy review, certificate pinning, decryption mode

## Overview

Audit ZIA SSL inspection rules to understand what traffic is being inspected, bypassed, or blocked at the SSL layer. This skill works **exclusively with SSL inspection tools**. It does NOT call URL filtering, DLP, or other unrelated tools unless the user explicitly asks for cross-referencing.

**Use this skill when:** A security administrator wants to review SSL inspection rules, understand what traffic is or is not being decrypted, or audit SSL inspection policy configuration.

## Scope Boundaries

**ONLY use these tools in this skill:**

- `zia_list_ssl_inspection_rules()` -- primary tool
- `zia_get_ssl_inspection_rule(rule_id)` -- detail for a specific rule
- `get_zia_user_groups(search)` -- resolve group IDs referenced in SSL rules
- `get_zia_user_departments(search)` -- resolve department IDs referenced in SSL rules
- `zia_list_locations()` -- resolve location IDs referenced in SSL rules

**DO NOT call these tools unless the user explicitly asks:**

- `zia_list_url_filtering_rules()` -- not part of SSL inspection audit
- `zia_list_web_dlp_rules()` / `zia_list_web_dlp_rules_lite()` -- not part of SSL inspection audit
- `zia_list_firewall_rules()` -- not part of SSL inspection audit
- Any other non-SSL tool

---

## Workflow

Follow this 4-step process.

### Step 1: Retrieve All SSL Inspection Rules

```text
zia_list_ssl_inspection_rules()
```text

Categorize each rule by its action:

- **INSPECT** (also called DECRYPT) -- traffic is fully decrypted and inspected
- **DO_NOT_INSPECT** -- traffic is not decrypted or inspected (full bypass)
- **DO_NOT_DECRYPT** -- traffic is not decrypted but metadata is still visible
- **BLOCK** -- traffic is blocked at the SSL layer

If the user asks about a specific action (e.g., "which rules are in decryption mode"), filter the results to show only rules matching that action.

---

### Step 2: Analyze Rule Details

For each relevant rule, extract and present:

**What it covers:**

- `url_categories` -- URL categories affected
- `cloud_applications` -- specific cloud apps affected
- `zpa_app_segments` -- ZPA application segments affected

**Who it applies to:**

- `users` -- specific user IDs
- `groups` -- user group IDs
- `departments` -- department IDs
- `locations` -- location IDs
- `device_trust_levels` -- device trust level requirements

**Scope:**

- `platforms` -- OS platforms (iOS, Android, macOS, Windows, Linux)
- `user_agent_types` -- browser types
- `enabled` -- whether the rule is active
- `order` -- rule evaluation order

Resolve IDs to human-readable names only when needed:

```text
get_zia_user_groups(search="<group_name>")
get_zia_user_departments(search="<department_name>")
zia_list_locations()
```text

---

### Step 3: Risk Assessment (for bypass audits)

If the user is auditing bypasses (DO_NOT_INSPECT / DO_NOT_DECRYPT), classify each by risk level:

**CRITICAL Risk:**

- Broad categories bypassed (e.g., "Uncategorized", "Miscellaneous")
- AI/ML applications bypassed
- Bypass applies to ALL users (no scoping)
- Categories with known data exfiltration risk (file sharing, webmail, social media)

**HIGH Risk:**

- Bypass for cloud applications that handle sensitive data
- Large user groups or entire departments bypassed

**MEDIUM Risk:**

- Specific applications bypassed due to certificate pinning (legitimate technical reason)
- Narrow scope -- specific users or small groups
- Categories with low data sensitivity (e.g., government sites, health portals)

**LOW Risk:**

- Platform-specific bypasses (e.g., iOS system services)
- Well-known applications with strong native encryption and no data loss risk
- Bypasses scoped to high-trust devices only

---

### Step 4: Generate Report

Present findings organized by the user's question. Adapt the format:

**If the user asks "which rules are in decryption mode":**

```text
SSL Inspection Rules -- DECRYPT (Active Inspection)
=====================================================

Total SSL rules: X
DECRYPT (active inspection): Y rules
DO_NOT_DECRYPT (bypass): Z rules
BLOCK: W rules

DECRYPT Rules:
1. "<rule_name>" (order: N, enabled: yes/no)
   - URL Categories: ...
   - Cloud Apps: ...
   - Applies To: <users/groups/departments>
   - Platforms: ...

2. "<rule_name>" ...
```text

**If the user asks "audit SSL bypass exceptions":**

```text
SSL Inspection Bypass Audit
============================

Total SSL rules: X
Bypass rules (DO_NOT_INSPECT/DO_NOT_DECRYPT): Y

CRITICAL RISK:
- "<rule>": Bypasses <N> categories for All Users

HIGH RISK:
- "<rule>": Bypasses <apps> for <department>

MEDIUM RISK:
- "<rule>": Certificate-pinned app bypass for specific users

LOW RISK:
- "<rule>": OS update bypass (expected)

Recommendations:
1. Review and narrow critical/high-risk bypasses
2. Consider per-user scoping instead of All Users
```text

---

## Optional: Cross-Reference with DLP / URL Filtering

**Only perform this step if the user explicitly asks** for DLP impact, URL filtering overlap, or a comprehensive security gap analysis.

```text
zia_list_web_dlp_rules()
zia_list_url_filtering_rules()
```text

Check if bypassed URL categories overlap with categories targeted by DLP or URL filtering rules. Flag any DLP rules that are rendered ineffective because their target categories are SSL-bypassed.

---

## Edge Cases

### No Bypass Rules Found

```text
Audit Complete: No SSL inspection bypass rules found.

All SSL inspection rules use the INSPECT action. This means all HTTPS
traffic is being decrypted and inspected.

Note: Verify this is intentional -- some applications with certificate
pinning may break without DO_NOT_INSPECT exceptions.
```text

### All Rules Disabled

```text
Warning: All X bypass rules are currently DISABLED.

This means full SSL inspection is effectively enabled for all traffic.
However, these disabled rules exist and could be re-enabled.

Recommendation: If no longer needed, delete them to prevent accidental
re-enablement.
```text

### Predefined/Default Rules

```text
Note: Rule "<name>" is a predefined/default rule (predefined=True).
This rule cannot be modified or deleted. Factor it into the audit but
flag that changes require a Zscaler support request.
```text

---

## When NOT to Use This Skill

- Creating or modifying SSL rules -- use `zia_create_ssl_inspection_rule` or `zia_update_ssl_inspection_rule` directly
- Investigating a specific URL category's full policy -- use the "investigate-url-category" skill
- Checking user access -- use the "check-user-url-access" skill
- Auditing DLP rules -- query DLP tools directly, not through this skill

---

## Quick Reference

**Primary workflow:** List SSL Rules → Analyze Details → Risk Assessment → Report

**Core tools (always use):**

- `zia_list_ssl_inspection_rules()` -- list all SSL inspection rules
- `zia_get_ssl_inspection_rule(rule_id)` -- get details of a specific rule

**Supporting tools (use only to resolve IDs in SSL rules):**

- `get_zia_user_groups(search)` -- resolve group IDs to names
- `get_zia_user_departments(search)` -- resolve department IDs to names
- `zia_list_locations()` -- resolve location IDs to names

**DO NOT call unless explicitly asked:**

- `zia_list_web_dlp_rules()` -- only if user asks for DLP impact analysis
- `zia_list_url_filtering_rules()` -- only if user asks for URL filtering overlap

**Risk classification:**

- CRITICAL: Broad categories, all users, high-risk apps
- HIGH: Sensitive apps/categories, large user scope
- MEDIUM: Certificate-pinning exceptions, narrow scope
- LOW: OS updates, system services, no data sensitivity
