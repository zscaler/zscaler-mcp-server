---
name: investigate-sandbox
disable-model-invocation: true
argument-hint: "<md5_hash_or_url> [symptom: blocked|allowed|quarantined|not-analyzed]"
description: "Investigate ZIA Sandbox file analysis -- check sandbox reports, quota, SSL prerequisite, and diagnose file block/quarantine issues."
---

# Investigate Sandbox

Investigate sandbox issue: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **MD5 hash** (32-character hex string) or **URL/domain** of the file
- **Symptom**: file blocked, file allowed unexpectedly, stuck in quarantine, not being analyzed

If an MD5 hash is provided, go directly to Step 2. If only a URL is provided, classify it first:

```text
zia_url_lookup(urls=["<url>"])
```text

## Step 2: Check Sandbox Report

If an MD5 hash is available:

```text
zia_get_sandbox_report(md5_hash="<hash>", report_details="full")
```text

Evaluate:

- **MALICIOUS** -- block is expected, sandbox correctly identified threat
- **BENIGN** -- should not be blocked by sandbox; check Malware Protection or ATP
- **Not found** -- file was not analyzed; proceed to Step 4

## Step 3: Check Sandbox Quota & Activity

```text
zia_get_sandbox_quota()
zia_get_sandbox_file_hash_count()
zia_get_sandbox_behavioral_analysis()
```text

Check if quota is exhausted, verify subscription level (Basic vs Advanced), and check if the hash appears in the blocked list.

## Step 4: Check SSL Inspection (Prerequisite)

Sandbox requires SSL inspection to see file content:

```text
zia_list_ssl_inspection_rules()
```text

If a DO_NOT_INSPECT or DO_NOT_DECRYPT rule matches the URL/domain, Sandbox cannot analyze the file.

## Step 5: Diagnose "Not Analyzed" Cases

If the file was not sent to Sandbox, check:

1. SSL not inspecting traffic for this domain (Step 4)
2. File type not supported by subscription (Basic: only .exe/.dll/.scr/.ocx/.sys/.zip)
3. File size exceeds limit (Basic: 2MB, Advanced: 20MB)
4. No active content in Office/PDF files (static analysis found nothing suspicious)
5. File already analyzed and cached as benign

## Step 6: Present Diagnosis

Provide a structured report with: sandbox report findings (or why no report exists), quota status, SSL inspection status, root cause, recommended actions, and any portal-level checks needed for Malware Protection / ATP policies.
