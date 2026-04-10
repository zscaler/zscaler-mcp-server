---
name: zms-analyze-policy-rules
description: "Analyze Zscaler Microsegmentation (ZMS) policy rules for optimization opportunities. Reviews custom and default policy rules, identifies stale or unused rules, detects overly permissive rules, maps cross-zone communication patterns, and assesses default security posture. Use when an administrator asks: 'Are there unused policy rules?', 'Which rules are too broad?', 'Optimize our segmentation policies', 'Review our default deny posture', 'Show me policy rule coverage', or 'Analyze our ZMS policies.'"
---

# ZMS: Analyze Policy Rules & Segmentation Optimization

## Keywords

policy rules, segmentation policies, microsegmentation rules, default policy, deny all, allow all, stale rules, unused rules, overly permissive, rule optimization, cross-zone, app zones, lateral movement, zero trust policy, rule priority, policy coverage

## Overview

Perform a focused analysis of Zscaler Microsegmentation policy rules to identify optimization opportunities. This skill examines custom segmentation rules for staleness, breadth, and coverage gaps; evaluates default policy posture (deny vs allow); maps cross-zone communication patterns through app zones; and correlates policy rules with resource group structure to identify unprotected segments.

Policy rules are the enforcement backbone of microsegmentation. They define which resource groups can communicate with each other, over which ports and protocols, and in which direction. Poorly maintained rules lead to either excessive lateral movement risk (too permissive) or application breakage (too restrictive).

**Rule evaluation order matters:** Rules are evaluated by priority — higher priority rules are matched first. A misconfigured priority can cause a restrictive rule to shadow an intended allow rule, or vice versa.

**Use this skill when:** A security architect needs to audit policy rule hygiene, identify stale rules, tighten overly permissive rules, review default posture, or prepare for a compliance audit that requires demonstrating least-privilege segmentation.

**Important:**

- All ZMS tools require `ZSCALER_CUSTOMER_ID` to be set as an environment variable.
- All current MCP tools are **read-only** (Query operations).
- The ZMS API supports full CRUD for policy rules via mutations (`policyRuleCreate`, `policyRuleUpdate`, `policyRuleDelete`, `defaultPolicyRulesCreate/Update/Delete`) but these are not yet exposed through MCP tools.

---

## Workflow

Follow this 5-step process for a comprehensive policy rule analysis.

### Step 1: Inventory All Policy Rules

**Fetch all custom policy rules:**

```text
zms_list_policy_rules(fetch_all=True)
```text

Using `fetch_all=True` bypasses pagination and returns every custom rule. For large tenants with hundreds of rules, use pagination instead:

```text
zms_list_policy_rules(page_num=1, page_size=50)
```text

**For each rule, capture:**

- **Name and description**: Is the rule clearly documented?
- **Action**: Allow or Block
- **Priority**: Higher values are evaluated first
- **Source target**: Which resource group(s) can initiate
- **Destination target**: Which resource group(s) can receive
- **Ports**: Specific port ranges (TCP/UDP) or "any"
- **Protocol**: TCP, UDP, ICMP, or any
- **Last hit (`lastHit`)**: When the rule was last matched — critical for staleness
- **Created/modified timestamps**: When was the rule created and last changed?

**List default (baseline) policy rules:**

```text
zms_list_default_policy_rules(page_num=1, page_size=50)
```text

Default rules establish the baseline security posture:

- **Default deny (recommended)**: All traffic blocked unless explicitly allowed by a custom rule. This is the Zero Trust approach.
- **Default allow**: All traffic allowed unless explicitly blocked. This is permissive and not recommended for production.
- **Direction**: Whether the default applies to inbound, outbound, or both
- **Scope type**: Global vs per-segment default behavior

---

### Step 2: Identify Stale and Unused Rules

**Analyze `lastHit` timestamps across all rules:**

Rules that have never been hit or haven't been hit in a long time are candidates for removal or review.

**Classification criteria:**

- **Never hit**: Rule has no `lastHit` value — may have been created but never matched traffic. Candidate for removal if older than 30 days.
- **Stale (> 90 days)**: Rule hasn't matched traffic in over 90 days. Likely obsolete unless protecting infrequent maintenance windows.
- **Aging (30-90 days)**: Rule hasn't matched recently but may be seasonal or periodic. Flag for review.
- **Active (< 30 days)**: Rule is actively matching traffic. Healthy.

**Also check creation timestamps:**

- Rules created more than 6 months ago with no hits are almost certainly obsolete
- Rules with names suggesting temporary access ("temp", "debug", "migration", "test") should be reviewed regardless of age

**Build a staleness summary:**

```text
Policy Rule Staleness Analysis
================================
Total Custom Rules: 42

Active (hit < 30 days):     32 (76%)  — Healthy
Aging (hit 30-90 days):      5 (12%)  — Review
Stale (hit > 90 days):       3 (7%)   — Likely obsolete
Never hit:                   2 (5%)   — Remove candidates
```text

---

### Step 3: Detect Overly Permissive Rules

**Identify rules that are too broad:**

A rule is overly permissive if it:

- **Allows "any" port**: No port restriction means all network services are accessible
- **Allows "any" protocol**: No protocol restriction
- **Has wildcard source or destination**: Applies to all resource groups rather than specific ones
- **Allows both directions**: No directionality constraint
- **Combines multiple of the above**: The more wildcards, the broader the rule

**Risk levels:**

- **Critical**: Any-to-any allow rule (completely defeats segmentation)
- **High**: Specific source, any destination, any port (source can reach anything)
- **Medium**: Specific source and destination, but any port (all services exposed between groups)
- **Low**: Specific source, destination, and ports but broad port ranges (e.g., 1-65535)

**Assess each permissive rule:**

- Is the breadth intentional and documented?
- Can it be narrowed to specific ports/protocols?
- Is there a business justification?
- Would tightening the rule break existing traffic? (check `lastHit` to see if it's active)

---

### Step 4: Map Cross-Zone Communication Patterns

**List all app zones:**

```text
zms_list_app_zones(page_num=1, page_size=50)
```text

**List resource groups for correlation:**

```text
zms_list_resource_groups(page_num=1, page_size=50)
```text

**Build a communication matrix:**

Cross-reference policy rules with app zones and resource groups to build a matrix showing which zones can communicate with which:

```text
Cross-Zone Communication Matrix
==================================

                Web Tier    App Tier    DB Tier     Shared
Web Tier        ALLOW(*)    ALLOW(443)  BLOCK       ALLOW(53,123)
App Tier        BLOCK       ALLOW(*)    ALLOW(5432) ALLOW(53,123)
DB Tier         BLOCK       BLOCK       ALLOW(*)    ALLOW(53,123)
Shared          ALLOW(*)    ALLOW(*)    ALLOW(*)    ALLOW(*)

(*) = intra-zone, any port
Ports shown = allowed cross-zone ports
BLOCK = default deny, no explicit allow rule
```text

**Analysis points:**

- **Intra-zone**: Are there rules controlling traffic within a zone? Often missed.
- **Cross-zone paths**: Does each cross-zone path have a corresponding allow rule with specific ports?
- **Shared services access**: Do all zones have appropriate access to DNS, NTP, logging?
- **Database tier isolation**: Is the database tier only accessible from the app tier? Direct web-to-DB is a red flag.
- **Missing zones**: Are there resource groups not assigned to any app zone?

---

### Step 5: Assess Overall Policy Health

**Compile the full picture:**

1. **Default posture**: Is the baseline deny-all? If not, flag as critical.
2. **Rule count**: Appropriate for environment size? Too few may mean gaps; too many may mean complexity.
3. **Staleness ratio**: What percentage of rules are active vs stale?
4. **Permissiveness score**: How many rules use wildcards for ports/protocols?
5. **Coverage**: Are all resource groups referenced in at least one policy rule?
6. **Priority conflicts**: Are there rules with the same priority that could cause unpredictable behavior?

**Check resource group protection for correlation:**

```text
zms_get_resource_group_protection_status()
```text

Groups with members but no policy coverage represent segmentation gaps.

---

### Present Policy Analysis Report

```text
Policy Rule Analysis & Optimization Report
=============================================
Date: <current_date>
Auditor: AI Assistant

## Executive Summary

- **Custom Rules:** 42
- **Default Rules:** 3
- **Default Posture:** Deny All — BEST PRACTICE
- **Active Rules (< 30 days):** 32 (76%)
- **Stale/Unused Rules:** 5 (12%) — NEEDS CLEANUP
- **Overly Permissive Rules:** 3 (7%) — NEEDS TIGHTENING
- **Resource Groups Without Coverage:** 2 — NEEDS POLICY
- **Overall Policy Health:** FAIR — optimization needed

---

## Default Posture Assessment

| Direction | Default Action | Assessment |
|-----------|---------------|------------|
| Inbound | DENY | Best practice |
| Outbound | DENY | Best practice |
| Cross-zone | DENY | Best practice |

✅ Default deny is correctly configured. All traffic requires explicit allow rules.

---

## Rule Hygiene

| Category | Count | % | Action |
|----------|-------|---|--------|
| Active (hit < 30 days) | 32 | 76% | No action |
| Aging (30-90 days) | 5 | 12% | Review |
| Stale (> 90 days) | 3 | 7% | Consider removal |
| Never hit | 2 | 5% | Remove |

**Stale rules (candidates for removal):**

| Rule Name | Created | Last Hit | Action |
|-----------|---------|----------|--------|
| Legacy App Migration | 6 months ago | Never | Remove |
| Temp Debug Access | 3 months ago | 92 days ago | Remove |
| Old Staging Bridge | 4 months ago | 95 days ago | Review |

---

## Permissiveness Analysis

| Rule Name | Source | Destination | Ports | Risk |
|-----------|--------|-------------|-------|------|
| Shared Services Any | Shared Svc | Any | Any | HIGH |
| Dev Full Access | Dev Group | Staging Group | Any | MEDIUM |
| Monitoring Sweep | Monitoring | Any | 161,9100 | LOW |

**Recommendations:**
1. "Shared Services Any" — Restrict to specific ports (53, 123, 514, 9200)
2. "Dev Full Access" — Restrict to specific application ports
3. "Monitoring Sweep" — Acceptable for monitoring, document justification

---

## Coverage Gaps

| Resource Group | Members | Has Policy | Issue |
|----------------|---------|------------|-------|
| New API Servers | 8 | No | NO COVERAGE |
| Decom Staging | 0 | Yes | Empty group |
| Test Env | 3 | No | NO COVERAGE |

---

## Recommendations

### Critical
1. Create policy rules for 2 resource groups with no coverage (11 workloads exposed)
2. Review default posture if set to "allow" — switch to "deny all"

### High
3. Remove 2 rules that have never been hit (created > 30 days ago)
4. Tighten "Shared Services Any" rule to specific ports
5. Review 3 stale rules (> 90 days without a hit)

### Medium
6. Narrow "Dev Full Access" to specific application ports
7. Remove empty resource group "Decom Staging" and its associated rule
8. Document business justification for all "any port" rules

### Low
9. Establish rule naming convention if not already in place
10. Schedule quarterly policy rule reviews
11. Add descriptions to rules that lack documentation
```text

---

## Edge Cases

### No Custom Policy Rules

```text
No custom policy rules found.

The deployment relies entirely on default rules, which means:
- If default is DENY: all cross-group traffic is blocked (no applications can communicate)
- If default is ALLOW: no segmentation is in effect (all traffic allowed)

Action: Create policy rules that match your application communication
requirements. Start with the most critical communication paths and
use default deny for everything else.
```text

### All Rules Are Active

```text
All 42 custom rules have been hit within the last 30 days.

This is a healthy state. Continue monitoring for:
- New rules that may need to be added for new applications
- Rules that become stale as applications are decommissioned
- Port ranges that can be further narrowed
```text

### Default Posture Is Allow

```text
WARNING: Default policy posture is set to ALLOW.

This means all traffic between resource groups is allowed unless
explicitly blocked by a policy rule. This defeats the purpose of
microsegmentation and does NOT follow Zero Trust principles.

Action: Switch to default DENY via the Zscaler admin portal or
defaultPolicyRulesUpdate mutation (not available via MCP tools).
Plan this change carefully — it will block all traffic that isn't
covered by an explicit allow rule.
```text

---

## Quick Reference

**Primary workflow:** Inventory Rules → Staleness → Permissiveness → Communication Matrix → Health Assessment → Report

**Policy rule tools:**

- `zms_list_policy_rules(fetch_all=True)` — all custom rules
- `zms_list_policy_rules(page_num, page_size)` — paginated custom rules
- `zms_list_default_policy_rules()` — baseline policies

**Supporting tools:**

- `zms_list_app_zones()` — application zone boundaries
- `zms_list_resource_groups()` — resource groups referenced by rules
- `zms_get_resource_group_protection_status()` — groups with/without policy coverage
- `zms_get_resource_group_members(group_id)` — members of a specific group

**Not yet available via MCP tools:**

- Policy rule create/update/delete (`policyRuleCreate`, `policyRuleUpdate`, `policyRuleDelete`)
- Default policy rule management (`defaultPolicyRulesCreate/Update/Delete`)
- These must be performed through the Zscaler admin portal or the ZMS API directly
