---
name: zia-check-user-url-access
description: "Determine whether a specific user or group is allowed to access a given URL by evaluating all applicable ZIA policies in order. Performs URL category lookup, then evaluates URL filtering rules, SSL inspection rules, DLP rules, and cloud firewall rules in priority order to produce a definitive access verdict. Use when an administrator asks: 'Can user X access site Y?', 'Why is a URL blocked?', or 'What policies apply to this user and URL?'"
---

# ZIA: Check User URL Access

## Keywords
can user access, is url blocked, why blocked, url access check, user access, policy evaluation, url allowed, access denied, troubleshoot access, blocked site, user policy

## Overview

Determine whether a specific user (or group/department) can access a given URL by evaluating all applicable ZIA policies in priority order. This skill simulates the policy evaluation engine by checking URL category classification, then walking through URL filtering, SSL inspection, DLP, and firewall rules to produce a definitive access verdict with full reasoning.

**Use this skill when:** An administrator asks whether a user can access a specific URL, why a URL is being blocked, or needs to understand which policy rules affect access for a specific user.

---

## Workflow

Follow this 6-step process to evaluate user URL access.

### Step 1: Identify the User and URL

Collect from the administrator:
- **URL** to check (e.g., "chat.openai.com", "github.com")
- **User identifier** -- username, email, group name, or department

**Look up the user:**
```
get_zia_users(search="<username_or_email>")
```

Note the user's:
- User ID
- Department (ID and name)
- Groups (IDs and names)

If the admin specified a group or department instead:
```
get_zia_user_groups(search="<group_name>")
get_zia_user_departments(search="<department_name>")
```

---

### Step 2: Classify the URL

```
zia_url_lookup(urls=["<url>"])
```

This returns:
- `urlClassifications` -- the category(ies) the URL belongs to
- `urlClassificationsWithSecurityAlert` -- whether there are security alerts

Note all categories returned. A URL can belong to multiple categories.

#### Example:

```
URL: chat.openai.com
Categories: AI/ML Applications, Technology
Security Alert: None
```

---

### Step 3: Evaluate URL Filtering Rules

```
zia_list_url_filtering_rules()
```

Walk through rules in **order** (lowest order number = highest priority). For each rule, check if it matches:

1. **Is the rule enabled?** Skip disabled rules.
2. **Does the URL category match?** Check if any of the URL's categories appear in the rule's `urlCategories`.
3. **Does the user match?** Check if the user, their groups, their department, or their location appears in the rule's `users`, `groups`, `departments`, `locations`. If none are specified, the rule applies to all users.
4. **First matching rule wins.** Stop evaluating once a match is found.

Record:
- Matching rule name, ID, and order
- Action: `ALLOW`, `BLOCK`, `CAUTION`
- Why it matched (category + user scope)

---

### Step 4: Evaluate SSL Inspection Rules

```
zia_list_ssl_inspection_rules()
```

Walk through rules in order. Check if the URL's categories or cloud application match any SSL rule. Record:
- Action: `INSPECT`, `DO_NOT_INSPECT`, `DO_NOT_DECRYPT`
- Impact on downstream policies (DLP effectiveness)

---

### Step 5: Evaluate DLP Rules (if SSL inspected)

Only applicable if SSL inspection action is `INSPECT`:

```
zia_list_web_dlp_rules()
```

Check if any DLP rules target the URL's categories. If yes, note:
- Rule name and action
- DLP engines involved
- Whether uploads, downloads, or both are scanned

If SSL is `DO_NOT_INSPECT`, DLP rules for HTTPS traffic are ineffective. Note this.

---

### Step 6: Present Access Verdict

#### Report Format:

```
URL Access Check Results
=========================

**User:** John Smith (john.smith@company.com)
- Department: Engineering
- Groups: Developers, All Employees
- Location: San Jose Office

**URL:** chat.openai.com
- Categories: AI/ML Applications, Technology
- Security Alerts: None

---

## Access Verdict: ALLOWED

---

## Policy Evaluation (in priority order)

### 1. URL Filtering
**Matching Rule:** "Allow AI Tools for Engineering" (ID: 12345, Order: 5)
- Action: ALLOW
- Matched because:
  - URL category "AI/ML Applications" is in the rule's category list
  - User's department "Engineering" is in the rule's department list
- Rules evaluated before match: 4 (none matched this user + category)

**Note:** A higher-priority rule "Block AI Tools" (Order: 8) exists that
BLOCKS "AI/ML Applications" for All Users, but the Engineering-specific
ALLOW rule at Order 5 takes precedence.

### 2. SSL Inspection
**Matching Rule:** "Inspect AI Applications" (ID: 23456, Order: 3)
- Action: INSPECT
- SSL traffic to AI/ML applications IS decrypted and inspected

### 3. DLP Web Rules
**Matching Rule:** "Monitor AI Data Uploads" (ID: 34567, Order: 2)
- Action: ALLOW (with logging)
- DLP Engine: Sensitive Data Detection
- Effect: Uploads are scanned for sensitive data. If detected, the
  upload is logged but not blocked (ALLOW action).

### 4. Cloud Firewall
No matching firewall rules for this URL/category.

---

## Effective Policy Summary

| Policy Layer      | Rule                          | Action       | Effective? |
|------------------|-------------------------------|--------------|------------|
| URL Filtering    | Allow AI for Engineering       | ALLOW        | Yes        |
| SSL Inspection   | Inspect AI Applications        | INSPECT      | Yes        |
| DLP              | Monitor AI Data Uploads        | ALLOW + LOG  | Yes        |
| Firewall         | (default)                     | ALLOW        | Yes        |

**Result:** User CAN access chat.openai.com. Uploads will be scanned
by DLP and logged if sensitive data is detected.
```

---

### Verdict: BLOCKED Example

```
## Access Verdict: BLOCKED

### 1. URL Filtering
**Matching Rule:** "Block Social Media" (ID: 12345, Order: 3)
- Action: BLOCK
- Matched because:
  - URL category "Social Networking" matches
  - User is in "All Users" scope (no exceptions for this user's groups)

**Other rules checked:**
- "Allow Social for Marketing" (Order: 2): ALLOW -- but user is NOT
  in the Marketing department, so this rule did not match.

**Why blocked:** The user is not in any group or department that has
an explicit ALLOW exception for Social Networking.

**To fix:** Either:
1. Add the user's group to an existing ALLOW rule
2. Create a new URL filtering rule to allow this user/group
3. Move the user to a department with an existing exception
```

---

## Edge Cases

### URL in Multiple Categories

```
URL: dropbox.com
Categories: File Sharing, Cloud Storage, Business Applications

Multiple categories means multiple potential rule matches. I'll evaluate
against ALL categories and report which category triggered the match.
```

### No Matching Rules (Default Policy)

```
No explicit rules matched for this user and URL category.
The DEFAULT URL filtering rule applies.

Default Rule: "<name>" (ID: <id>)
- Action: <ALLOW/BLOCK/CAUTION>

This is the catch-all rule at the bottom of the policy.
```

### User in Multiple Groups with Conflicting Rules

```
Conflict detected: User is in both "Developers" and "Contractors" groups.

- Rule "Allow GitHub" (Order: 3): ALLOW for Developers
- Rule "Block Code Repos" (Order: 5): BLOCK for Contractors

Resolution: Rule at Order 3 is evaluated first. Since the user IS a
member of the Developers group, the ALLOW rule matches first.

Verdict: ALLOWED (Developer rule takes precedence by order)
```

### Caution Action

```
Action: CAUTION

The user will see a warning page but CAN proceed to the site after
acknowledging the caution. This is neither a full block nor a full allow.
```

---

## When NOT to Use This Skill

- Investigating all rules for a category (not user-specific) -- use "investigate-url-category" skill
- Auditing SSL bypass rules -- use "audit-ssl-inspection-bypass" skill
- Creating or modifying URL filtering rules -- use `zia_create_url_filtering_rule` directly
- Looking up URL categories without policy evaluation -- use `zia_url_lookup` directly

---

## Quick Reference

**Primary workflow:** Identify User → Classify URL → Evaluate URL Filtering → Evaluate SSL → Evaluate DLP → Present Verdict

**Tools used:**
- `get_zia_users(search)` -- look up user details
- `get_zia_user_groups(search)` -- look up group membership
- `get_zia_user_departments(search)` -- look up department
- `zia_url_lookup(urls)` -- classify URL into categories
- `zia_list_url_filtering_rules()` -- evaluate URL filtering rules
- `zia_list_ssl_inspection_rules()` -- evaluate SSL inspection rules
- `zia_list_web_dlp_rules()` -- evaluate DLP rules
- `zia_list_cloud_firewall_rules()` -- evaluate firewall rules

**Evaluation order:**
1. URL Filtering Rules (by order number, first match wins)
2. SSL Inspection Rules (determines DLP effectiveness)
3. DLP Web Rules (only effective if SSL is inspected)
4. Cloud Firewall Rules (network-level controls)

**Remember:**
- Lowest rule order number = highest priority
- First matching rule wins (no further evaluation)
- SSL bypass makes DLP ineffective for HTTPS
- A URL can belong to multiple categories
- "All Users" scope means everyone unless a higher-priority rule excludes them
