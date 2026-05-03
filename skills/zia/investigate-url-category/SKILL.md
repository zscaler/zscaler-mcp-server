---
name: zia-investigate-url-category
description: "Investigate where a specific URL or URL category is referenced across all ZIA policy rules. Searches URL filtering rules, DLP web rules, SSL inspection rules, and cloud firewall rules to provide a comprehensive view of how a category is used. Use when an administrator asks: 'Where is this URL category used?', 'What rules apply to this URL?', or 'Show me the policy impact of this category.'"
---

# ZIA: Investigate URL Category

## Keywords

url category, where is category used, url filtering, category lookup, url policy, category impact, url rules, which rules use category, url category audit, policy investigation

## Overview

Investigate where a specific URL or URL category is referenced across all ZIA security policies. This skill queries URL filtering rules, DLP web rules, SSL inspection rules, and cloud firewall rules to build a complete picture of how the category affects traffic and users.

**Use this skill when:** An administrator wants to understand the policy impact of a URL category, check which rules reference a specific category, or determine what happens when a user tries to access a URL in that category.

---

## Workflow

Follow this 5-step process to investigate a URL category.

### Step 1: Identify the URL Category

Determine whether the admin is asking about a specific URL or a named category.

**If given a URL**, look it up first:

```text
zia_url_lookup(urls=["example.com"])
```text

This returns the URL's category classification (e.g., "SOCIAL_NETWORKING", "STREAMING_MEDIA").

**If given a category name**, list categories to find the exact ID:

```text
zia_list_url_categories()
```text

Search the results for the category name and note:

- `id` (e.g., "CUSTOM_01", "SOCIAL_NETWORKING")
- `configuredName` (display name)
- `urls` (any URLs explicitly added to the category)
- `superCategory` (parent category)

**If the category is custom**, get full details:

```text
zia_get_url_category(category_id="<category_id>")
```text

#### Present Initial Findings

```text
URL Category Identified:

**Category:** Social Networking
- ID: SOCIAL_NETWORKING
- Super Category: Entertainment & Recreation
- Type: Built-in

Now searching across all policy rule types...
```text

---

### Step 2: Search URL Filtering Rules

```text
zia_list_url_filtering_rules()
```text

Scan every rule's `urlCategories` field for the target category ID or name. For each match, note:

- Rule name and ID
- Action (`ALLOW`, `BLOCK`, `CAUTION`)
- Which users/groups/departments/locations are affected
- Whether the rule is enabled
- Rule order (priority)

---

### Step 3: Search SSL Inspection Rules

```text
zia_list_ssl_inspection_rules()
```text

Scan every rule's `urlCategories` field. For each match, note:

- Rule name and ID
- Action (`INSPECT`, `DO_NOT_INSPECT`, `DO_NOT_DECRYPT`)
- Which users/groups are affected
- Whether the rule is enabled

---

### Step 4: Search DLP Web Rules

```text
zia_list_web_dlp_rules()
```text

Scan every rule's `urlCategories` field. For each match, note:

- Rule name and ID
- Action (`ALLOW`, `BLOCK`)
- DLP engines and dictionaries involved
- Which users/groups are affected

---

### Step 5: Compile and Present Results

Build a comprehensive report showing everywhere the category is referenced.

#### Report Format

```text
URL Category Investigation Report
==================================

**Category:** <name> (<id>)
**Super Category:** <super_category>
**Type:** Built-in / Custom

---

## URL Filtering Rules (X matches)

| # | Rule Name              | Action  | Enabled | Users/Groups          | Order |
|---|------------------------|---------|---------|----------------------|-------|
| 1 | Block Social Media     | BLOCK   | Yes     | All Users             | 3     |
| 2 | Allow Marketing Social | ALLOW   | Yes     | Marketing Department  | 2     |

**Analysis:** Social Networking is BLOCKED for all users by default (Rule #1,
order 3), but ALLOWED for the Marketing department (Rule #2, order 2 --
higher priority).

---

## SSL Inspection Rules (X matches)

| # | Rule Name                  | Action         | Enabled | Users/Groups |
|---|----------------------------|----------------|---------|-------------|
| 1 | Do Not Inspect Social      | DO_NOT_INSPECT | Yes     | All Users   |

**Analysis:** SSL traffic to Social Networking sites is NOT inspected,
meaning DLP policies cannot scan content on these sites.

---

## DLP Web Rules (X matches)

| # | Rule Name               | Action | Enabled | DLP Engine    |
|---|-------------------------|--------|---------|---------------|
| 1 | Block PII Upload Social | BLOCK  | Yes     | PII Detection |

**Analysis:** Even if Social Networking is allowed by URL filtering, DLP
will block uploads containing PII.

NOTE: Since SSL is not inspected for this category (see above), this DLP
rule will NOT be effective for HTTPS traffic. Consider enabling SSL
inspection for this category.

---

## Cloud Firewall Rules (X matches)

No firewall rules reference this URL category directly.

---

## Summary

The URL category "<name>" is referenced in:
- X URL Filtering rules
- X SSL Inspection rules
- X DLP Web rules
- X Cloud Firewall rules

**Effective Policy (for a standard user):**
1. URL Filtering: BLOCKED (rule order 3)
2. SSL Inspection: NOT INSPECTED
3. DLP: Block PII upload (but ineffective without SSL inspection)

**Recommendations:**
- If DLP enforcement is needed, enable SSL inspection for this category
- Review the Marketing department exception to ensure it is still needed
```text

---

## Advanced Investigation

### Check Impact on a Specific User or Group

If the admin asks "Can user X access category Y?":

1. Look up the user's department and groups:

```text
get_zia_users(search="<username>")
get_zia_user_groups(search="<group_name>")
get_zia_user_departments(search="<department_name>")
```text

2. Then cross-reference with the rules found above, evaluating rule order and specificity.

### Check Custom URL Categories

Custom categories may contain specific URLs. Get the full list:

```text
zia_get_url_category(category_id="CUSTOM_01")
```text

Review the `urls`, `dbCategorizedUrls`, `keywords`, and `ipRanges` fields.

### Check If a URL Is in Multiple Categories

```text
zia_url_lookup(urls=["suspicious-site.com"])
```text

A URL can match multiple categories. Repeat the investigation for each returned category.

---

## Edge Cases

### Category Not Found in Any Rules

```text
Investigation complete: The URL category "<name>" is not referenced in any
URL filtering, SSL inspection, DLP, or firewall rules.

This means:
- The DEFAULT rules will apply for this category
- Check the default URL filtering rule for the baseline action
- Check the default SSL inspection rule for inspection behavior
```text

### Category Referenced in Disabled Rules Only

```text
The URL category "<name>" is only referenced in DISABLED rules.
Currently, only the default policy applies.

Disabled rules found:
- [Disabled] "Block Streaming" (URL Filtering, BLOCK)

These rules have no effect until re-enabled.
```text

---

## When NOT to Use This Skill

- Creating or modifying URL categories -- pick the right tool for the flavour. Custom: `zia_create_url_category`, `zia_update_url_category` (full PUT), `zia_delete_url_category`. Predefined (Zscaler-curated, e.g. `FINANCE`, `NEWS_AND_MEDIA`): `zia_get_url_category_predefined`, `zia_update_url_category_predefined` (full PUT). The custom-only tools refuse predefined IDs at the safety-guard layer.
- Adding/removing URLs from a category -- use `zia_add_urls_to_category` or `zia_remove_urls_from_category`. Both work transparently on custom *and* predefined categories (they use the SDK's `?action=ADD_TO_LIST` / `?action=REMOVE_FROM_LIST` endpoints, which preserve Zscaler's curated list on predefined categories).
- Creating new filtering rules -- use `zia_create_url_filtering_rule` directly
- Investigating SSL bypass specifically -- use the "audit-ssl-inspection-bypass" skill

---

## Quick Reference

**Primary workflow:** Identify Category → Search URL Rules → Search SSL Rules → Search DLP Rules → Compile Report

**Tools used:**

- `zia_url_lookup(urls)` -- classify a URL into categories
- `zia_list_url_categories()` -- list all categories
- `zia_get_url_category(category_id)` -- get category details
- `zia_list_url_filtering_rules()` -- search URL filtering rules
- `zia_list_ssl_inspection_rules()` -- search SSL inspection rules
- `zia_list_web_dlp_rules()` -- search DLP rules
- `zia_list_cloud_firewall_rules()` -- search firewall rules
- `get_zia_users(search)` -- look up specific users
- `get_zia_user_groups(search)` -- look up groups
- `get_zia_user_departments(search)` -- look up departments

**Remember:**

- Rule order matters -- lower order number = higher priority
- SSL inspection affects DLP effectiveness
- A URL can belong to multiple categories
- Default rules apply when no explicit rule matches
- Always check for disabled rules that may cause confusion
