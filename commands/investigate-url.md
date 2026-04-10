---
disable-model-invocation: true
argument-hint: "<url_or_category_name>"
description: "Investigate where a URL or URL category is referenced across ZIA policy rules."
---

# Investigate URL Category

Investigate: **$ARGUMENTS**

## Step 1: Classify the URL

If a URL was provided (not a category name):

```text
zia_url_lookup(urls=["<url>"])
```text

Note the category name and ID.

## Step 2: Search Across All Policy Types

Check every policy type for references to this category:

**URL Filtering:**

```text
zia_list_url_filtering_rules()
```text

**SSL Inspection:**

```text
zia_list_ssl_inspection_rules()
```text

**DLP Web Rules:**

```text
zia_list_dlp_web_rules()
```text

**Cloud Firewall:**

```text
zia_list_cloud_firewall_rules()
```text

## Step 3: Map Policy Impact

For each rule that references the category, document:

- Rule name and order
- Action (ALLOW, BLOCK, CAUTION, INSPECT, DO_NOT_INSPECT, etc.)
- Scope (which users/groups/departments)
- Whether the rule is enabled

## Step 4: Present Report

```text
URL Category Policy Impact Report
===================================

URL: <url>
Category: <category_name>

Referenced in X rules across Y policy types:

URL FILTERING (Z rules):
  1. "<rule>" (order N): BLOCK for All Users
  2. "<rule>" (order N): ALLOW for <group> (override)

SSL INSPECTION (Z rules):
  1. "<rule>" (order N): DO_NOT_INSPECT for All Users

DLP (Z rules):
  (none)

CLOUD FIREWALL (Z rules):
  1. "<rule>" (order N): ALLOW ports 80,443

Net effect for a typical user:
  URL Filtering: BLOCKED
  SSL Inspection: NOT INSPECTED
  DLP: Not applicable (bypassed by SSL)
```text
