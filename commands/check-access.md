---
disable-model-invocation: true
argument-hint: "<user_or_group> <url>"
description: "Check whether a user or group can access a specific URL via ZIA policies."
---

# Check User URL Access

Check access for: **$ARGUMENTS**

## Step 1: Parse Input

Extract:
- **User or group name**
- **URL to check** (e.g., youtube.com, drive.google.com/upload)

## Step 2: Classify the URL

```
zia_url_lookup(urls=["<url>"])
```

Note the URL category classification.

## Step 3: Evaluate URL Filtering Rules

```
zia_list_url_filtering_rules()
```

Walk through rules in order. For each rule, check if:
- The user/group matches the rule's scope
- The URL category matches the rule's categories
- The rule's action (ALLOW, BLOCK, CAUTION, ISOLATE)

The first matching rule determines the verdict.

## Step 4: Check SSL Inspection

```
zia_list_ssl_inspection_rules()
```

Determine if the traffic would be inspected, which affects DLP and threat detection.

## Step 5: Check DLP Rules

```
zia_list_dlp_web_rules()
```

Check if any DLP rules apply to this URL category for this user.

## Step 6: Check Cloud Firewall

```
zia_list_cloud_firewall_rules()
```

Look for port/protocol-based rules that might affect access.

## Step 7: Present Verdict

```
Access Verdict: ALLOWED / BLOCKED / CAUTIONED
URL: <url>
Category: <category>
User/Group: <user_or_group>

Matching Rule: "<rule_name>" (order: <N>)
Action: <action>
Reason: <explanation>

Additional Findings:
- SSL Inspection: Yes/No (rule: "<rule_name>")
- DLP: No matching rules / Matched rule "<name>"
- Firewall: No blocks / Blocked by "<rule_name>"
```
