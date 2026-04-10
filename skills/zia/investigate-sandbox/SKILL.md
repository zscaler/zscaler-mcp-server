---
name: zia-investigate-sandbox
description: "Investigate ZIA Sandbox file analysis results, quarantine issues, and security policy enforcement. Uses sandbox report, quota, behavioral analysis, and file hash tools combined with SSL inspection checks to diagnose why files are blocked, allowed, or stuck in quarantine. Incorporates runbook knowledge for Malware Protection, ATP, and Sandbox policy troubleshooting. Use when an administrator asks 'why is this file blocked?', 'check sandbox report for this hash', 'file stuck in quarantine', or 'sandbox is not analyzing files.'"
---

# ZIA: Investigate Sandbox

## Keywords

sandbox, file blocked, quarantine, md5 hash, sandbox report, malware, atp, advanced threat protection, malware protection, file analysis, patient zero, patient 0, sandbox quota, file not scanning, quarantine stuck, sandbox verdict, behavioral analysis, unscannable file

## Overview

Investigate ZIA Sandbox file analysis results and security policy enforcement issues. This skill combines API-driven sandbox inspection (reports, quota, behavioral analysis) with runbook-guided troubleshooting for Malware Protection, Advanced Threat Protection (ATP), and Sandbox policies.

**Use this skill when:** An administrator reports files being unexpectedly blocked or allowed, files stuck in quarantine, sandbox not analyzing files, missing Patient 0 alerts, or needs to verify a sandbox verdict for a specific file hash.

---

## Workflow

### Step 1: Gather Issue Details

Collect from the administrator:

**Required:**

- Symptom: file blocked, file allowed unexpectedly, file stuck in quarantine, sandbox not analyzing
- File MD5 hash (if available from Web Insights logs)
- URL or domain where the file was downloaded from

**Helpful:**

- Policy Action from Web Insights logs (e.g., "Sandbox Block", "Quarantined", "Allowed")
- Threat Super Category from Web Insights logs (e.g., "Sandbox", "Virus", "Malware Protection")
- Blocked Policy Type (e.g., "Sandbox", "Malware Protection", "Advanced Threat Protection")
- File type and size
- Sandbox subscription level (Basic vs Advanced)

---

### Step 2: Determine the Security Control Involved

The Blocked Policy Type in Web Insights logs identifies which security control is responsible:

| Blocked Policy Type | Security Control | API Tools Available? |
|---------------------|-----------------|---------------------|
| **Sandbox** | ZIA Sandbox | Yes -- full API investigation |
| **Malware Protection** | ZIA Malware Protection | No API -- advisory guidance only |
| **Advanced Threat Protection** | ZIA ATP | No API -- advisory guidance only |

If the administrator knows the Blocked Policy Type, skip to the relevant section below.

---

### Step 3: Sandbox Investigation (API-driven)

#### 3A: Check Sandbox Report for a File

If an MD5 hash is available:

```text
zia_get_sandbox_report(md5_hash="<md5_hash>", report_details="full")
```text

**Evaluate the report:**

- **Class Type**: `MALICIOUS`, `SUSPICIOUS`, `BENIGN`
- If `MALICIOUS` -- the block is expected behavior; the sandbox correctly identified the threat
- If `BENIGN` -- the file should not be blocked by Sandbox; look for other policies (Malware Protection, ATP, File Type Control)
- If `SUSPICIOUS` -- review the behavioral indicators in the full report

**If no report is found:**
The file was not analyzed by Sandbox. Proceed to Step 3D to diagnose why.

#### 3B: Check Sandbox Quota

```text
zia_get_sandbox_quota()
```text

Verify:

- Quota is not exhausted (if exhausted, files won't be sent for analysis)
- Subscription level (Basic vs Advanced affects file type and size limits)

**Basic vs Advanced Sandbox:**

| Capability | Basic | Advanced |
|-----------|-------|----------|
| File types | .exe, .dll, .scr, .ocx, .sys, .zip only | All common types including Office, PDF, APK, scripts |
| File size | 2 MB max | Up to 20 MB (50 MB for .exe and archives) |
| Quarantine | Not available | Yes |
| Patient 0 alerts | Not available | Yes |
| URL category filtering | Limited categories only | All URL categories |
| Sandbox report API | Not available | Yes |

If a file type or size doesn't match the subscription level, Sandbox won't analyze it.

#### 3C: Check Behavioral Analysis and Hash Counts

```text
zia_get_sandbox_behavioral_analysis()
```text

Returns the list of MD5 hashes currently blocked by Sandbox. Check if the file's hash appears in this list.

```text
zia_get_sandbox_file_hash_count()
```text

Returns blocked-hash usage statistics to understand overall sandbox activity volume.

#### 3D: File Not Sent to Sandbox -- Diagnostic Checklist

If the file was not analyzed by Sandbox, walk through these causes:

1. **SSL Inspection not enabled** -- Sandbox requires SSL inspection as a prerequisite

```text
zia_list_ssl_inspection_rules()
```text

Check if the traffic for this URL/domain is being SSL-inspected. If a `DO_NOT_INSPECT` or `DO_NOT_DECRYPT` rule matches, Sandbox cannot see the file.

2. **File type not supported by subscription** -- Basic Sandbox only supports .exe, .dll, .scr, .ocx, .sys, .zip. Check the file extension against the subscription level.

3. **File size exceeds limit** -- Basic: 2 MB max. Advanced: 20 MB max (50 MB for .exe/archives). Files exceeding the limit are handled by File Type Control policy instead.

4. **No active content (Office/PDF files)** -- For Office documents and PDFs, ZIA performs static analysis first. If no macros, embedded scripts, or suspicious objects are found, the file is classified as benign without Sandbox analysis. Web Insights logs show "Allowed - No Active Content".

5. **File already analyzed** -- If the same MD5 was previously analyzed and classified as benign, it may be fast-pathed without re-analysis.

---

### Step 4: SSL Inspection Prerequisite Check

SSL Inspection is required for both Sandbox and Malware Protection to function:

```text
zia_list_ssl_inspection_rules()
```text

**Check for the URL/domain in question:**

- Is there a rule with `DO_NOT_INSPECT` or `DO_NOT_DECRYPT` that matches the domain or URL category?
- If traffic is not SSL-inspected, Sandbox, Malware Protection, and ATP cannot scan the file content

Also check the URL category for the domain:

```text
zia_url_lookup(urls=["<url_or_domain>"])
```text

This helps correlate SSL inspection rules (which often use URL categories as conditions).

---

### Step 5: Malware Protection & ATP Troubleshooting (Advisory)

These security controls do not have API tools, but the following guidance helps administrators troubleshoot via the ZIA Admin Portal.

#### Access Blocked Unexpectedly

If the Blocked Policy Type is "Malware Protection" or "Advanced Threat Protection":

1. **Verify SSL Inspection is enabled** (Step 4 above -- this IS API-checkable)
2. **Check Malware Protection Policy** (Portal: Web > Malware Protection)
   - Verify Traffic Inspection and Protocol Inspection are enabled
   - Check if the file matches Unscannable Files or Password-Protected Files settings
   - Unscannable: archive files >400 MB or extracted files >200 MB are not scanned
3. **Check ATP Policy** (Portal: Web > Advanced Threat Protection)
   - Check for matching entries in Blocked Malicious URLs
   - Review the ATP policy action for the relevant threat categories
4. **Check Security Exceptions** (Portal: Web > Security Exceptions)
   - Look for "Do Not Scan Content from these URLs" entries
5. **Verify the URL classification hasn't changed:**

```text
zia_url_lookup(urls=["<url>"])
```text

Compare the current category to what it was when access previously worked.

#### Access Allowed Unexpectedly (Block Policy Configured but Not Enforced)

1. **Verify SSL Inspection is enabled** (without SSL inspection, Malware Protection and ATP cannot scan)
2. **Check if URL is in Security Exceptions** (Portal: Web > Security Exceptions > "Do Not Scan Content from these URLs")
3. **Check Malware Protection policy action** -- if set to "Allow" for this file type, it won't block
4. **Check ATP policy action** -- if set to "Allow" for this threat category, it won't block

---

### Step 6: Quarantine Issues (Advisory + API)

#### File Stuck in Quarantine

Possible causes:

1. **One-time download links** -- After the initial request, the URL no longer serves the file. Subsequent download attempts return 404/403 from the origin server. Web Insights logs show "Sent for Analysis" for the first transaction, then "Allowed" for subsequent attempts (but with server-side 404).

2. **Dynamic file generation (changing hashes)** -- Some websites generate a unique file per request (different MD5 each time). Each new hash triggers a new quarantine. Web Insights logs show multiple "Sent for Analysis" entries for the same URL but with different MD5 hashes.

   **Resolution:** Create a Sandbox rule for the affected domain to "Allow and scan" instead of quarantine. This delivers the file immediately while Sandbox analyzes in the background. If malicious, a Patient 0 alert fires.

3. **ZIA PSE cache timing** -- After analysis completes on one ZIA Public Service Edge, the result may not yet be cached on another PSE. Users accessing from a different location may briefly see the quarantine page again. This resolves itself after the cache propagates.

#### Verify with Sandbox Report

```text
zia_get_sandbox_report(md5_hash="<md5_hash>", report_details="summary")
```text

If the report shows "Benign" but the file is still quarantined, the PSE cache hasn't updated yet. The user should retry shortly.

---

### Step 7: Present Diagnosis

#### Report Format

```text
ZIA Security Policy Investigation Report
==========================================

**File/URL:** <url_or_file>
**MD5 Hash:** <md5>
**Symptom:** <blocked / allowed unexpectedly / stuck in quarantine / not analyzed>

---

## Security Control Identification

Blocked Policy Type: <Sandbox / Malware Protection / ATP>
Policy Action: <specific action from Web Insights>
Threat Super Category: <Sandbox / Virus / etc.>

---

## Sandbox Analysis

### Report Status: <Found / Not Found>
- Class Type: MALICIOUS / BENIGN / SUSPICIOUS
- Threat Name: <name>
- Analysis Date: <date>
- Verdict: <summary>

### Quota Status
- Files submitted: <count>
- Quota remaining: <count>
- Subscription: Basic / Advanced

### Behavioral Analysis
- MD5 in blocked list: Yes / No

---

## SSL Inspection Check

- SSL inspection active for this domain: Yes / No
- Matching rule: "<rule_name>" (action: <INSPECT / DO_NOT_INSPECT>)
- Impact: <if not inspected, Sandbox/Malware/ATP cannot scan>

---

## Root Cause

<Explanation based on findings>

---

## Recommended Actions

1. <Immediate action>
2. <Configuration change if needed>
3. <Portal checks for Malware Protection / ATP if applicable>

---

## Portal Checks Required (not available via API)

If the issue involves Malware Protection or ATP policy:
- [ ] Check Web > Malware Protection policy and exceptions
- [ ] Check Web > Advanced Threat Protection policy and exceptions
- [ ] Check Web > Security Exceptions > "Do Not Scan Content from these URLs"
- [ ] Review Web Insights logs with all fields selected
```text

---

## Quick Reference

**Sandbox Tools:**

- `zia_get_sandbox_report(md5_hash, report_details)` -- get sandbox analysis report (summary or full)
- `zia_get_sandbox_quota()` -- check quota usage and subscription limits
- `zia_get_sandbox_behavioral_analysis()` -- list of MD5 hashes blocked by sandbox
- `zia_get_sandbox_file_hash_count()` -- blocked hash usage statistics

**Supporting Tools:**

- `zia_list_ssl_inspection_rules()` -- verify SSL inspection (prerequisite for sandbox)
- `zia_url_lookup(urls)` -- classify the URL to correlate with policy rules
- `zia_list_url_filtering_rules()` -- check URL filtering (may block before sandbox)
- `zia_list_cloud_firewall_rules()` -- check firewall rules

**External Resources (for administrator):**

- Zulu (zulu.zscaler.com) -- URL analysis
- VirusTotal (virustotal.com) -- file/URL multi-vendor analysis
- Zscaler Threat Library -- threat name lookup
- Zscaler Sandbox Portal -- manual file submission (max 20 MB)
