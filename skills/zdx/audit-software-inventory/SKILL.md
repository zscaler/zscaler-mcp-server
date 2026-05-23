---
name: zdx-audit-software-inventory
description: "Audit the software inventory across devices in the organization using ZDX data. Lists installed software, filters by location, department, or user, and drills into specific software version details. Use for compliance audits, security vulnerability assessments, or identifying outdated software. Use when an administrator asks: 'What software is installed on our devices?', 'Find all devices running Chrome version X', 'Audit software versions across the organization', or 'Which departments have outdated Java?'"
---

# ZDX: Audit Software Inventory

## Keywords

software inventory, installed software, software audit, compliance, outdated software, software versions, device software, security audit, vulnerability assessment, software deployment, patch management

## Overview

Audit the software installed across devices in the organization using ZDX's software inventory data. This skill retrieves installed software with filtering by location, department, geolocation, user, or device, then drills into specific software packages to understand version distribution and deployment scope.

**Use this skill when:** An administrator needs to audit software compliance, identify devices with outdated or vulnerable software versions, assess patch rollout progress, or inventory software across the fleet.

---

## Data Presentation Requirements

**All tables are rendered by the HTML template, not by hand.** Do not author `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, or `<td>` markup in your reply or in the report. You produce a JSON payload (see *Data Payload Contract*) and the template at `./templates/report.html.template` turns it into the styled, sortable, exportable tables shown in `./example/report.example.html`.

After each table, provide:

1. **Detailed analysis** explaining the compliance posture, version distribution, and risk areas
2. **Security assessment** highlighting EOL, outdated, or vulnerable software
3. **Next steps / resolution** with specific remediation actions (patching, MDM push, upgrade plans) prioritized by risk

Use color-coded status indicators in tables:

- Green: Current version, no known vulnerabilities
- Yellow: One version behind or approaching EOL
- Red: EOL, known vulnerabilities, or significantly outdated

## ⚠ HTML OUTPUT — READ THIS BEFORE PRODUCING ANY HTML

There is exactly one acceptable way to produce the HTML output:

1. **Read the template from disk** — do NOT inline a copy in your response. The template lives next to this SKILL.md inside the skill's package, at:

   ```text
   ./templates/report.html.template
   ```

   The `./` prefix is intentional: this path is **relative to the skill folder** (the directory containing this SKILL.md), **never** an absolute path. Most agents that load skills from an uploaded `.zip` extract the package into a working directory and expose its contents via that relative path — read the file by joining the skill's own root directory with `./templates/report.html.template`. Do not rewrite this to an absolute path that points at the author's machine.

2. **Build a single JSON object** (`__ZDX_DATA__` payload) shaped exactly as documented in the *Data Payload Contract* section below. Aggregate the responses from the ZDX MCP tool calls (Steps 1–3 of the *Workflow*) into that object.

3. **Replace** the literal token `__ZDX_DATA__` (which appears once, inside `<script type="application/json" id="zdx-data">__ZDX_DATA__</script>`) with the JSON object. Do not edit any other part of the template.

4. **Write** the result to disk as `software_inventory_audit_<YYYYMMDD-HHMMSS>.html` next to the .docx, and give the user a `computer://` link to it.

This template already provides: Zscaler header with logo · sticky top bar · scope summary bar · KPI cards with severity-coded top borders · per-table search + filter chips · sortable color-coded tables · per-table CSV export · light/dark theme toggle · top-right language dropdown (EN / ES / PT / FR / JA) · printable PDF view · localStorage prefs · Analysis / Root Cause / Remediation block.

**If you find yourself writing `<html>`, `<style>`, or `<table>` in a code-block destined for the user, stop. Read the template instead.**

A populated reference rendering ships with this skill at `./example/report.example.html` (relative to the skill folder). Open it in a browser to preview the exact layout and depth expected.

### Data Payload Contract

The full `__ZDX_DATA__` payload is one JSON object. Every field below is **required** unless marked optional.

```json
{
  "generated_at": "<ISO 8601 timestamp>",
  "scope_en": "Free-form description in English",
  "scope_es": "...in Spanish (optional, falls back to scope_en)",
  "scope_pt": "...in Portuguese (optional)",
  "scope_fr": "...in French (optional)",
  "scope_ja": "...in Japanese (optional)",
  "kpis": {
    "totalSoftware": "<int>",
    "totalDevices": "<int>",
    "compliancePct": "<float, 0-100>",
    "criticalCount": "<int>"
  },
  "tables": {
    "software": [
      {
        "severity": "critical | warning | good",
        "name": "<software name>",
        "version": "<version string or summary>",
        "vendor": "<vendor>",
        "group": "<category, e.g. 'Collaboration'>",
        "devices": "<int>",
        "users": "<int>",
        "status": "Current | Outdated | EOL",
        "risk": "None | Low | Medium | High | Critical"
      }
    ]
  },
  "analysis": {
    "summary": "...",
    "rootCause": "...",
    "remediation": [
      { "priority": "Immediate | Investigate | Monitor | Communicate", "action": "..." }
    ]
  }
}
```

Map each row's `severity` from `status`: `Current` → `good`, `Outdated` → `warning`, `EOL` → `critical`.

## Output Artifacts — MANDATORY

You MUST generate BOTH files below. Both are REQUIRED output for every software inventory audit.

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `software_inventory_audit_<YYYYMMDD-HHMMSS>.docx` containing:

- Executive summary with compliance posture percentages
- Full software inventory table (software name, version, vendor, device count, user count, status, risk)
- Security findings section with EOL/vulnerable software details
- Recommendations section with prioritized remediation actions
- Scope and filters used for the audit

### 2. Interactive HTML Web Page (.html) — REQUIRED

Generated by the template-substitution flow described in the **HTML OUTPUT** section above. Filename: `software_inventory_audit_<YYYYMMDD-HHMMSS>.html`. Do not hand-author HTML or CSS — the template ships everything the report needs.

---

## Workflow

### Step 1: List Software Inventory

Retrieve the organization-wide software inventory.

```text
zdx_list_software()
```text

**Filter by location:**

```text
zdx_list_software(location_id=["<location_id>"])
```text

**Filter by department:**

```text
zdx_list_software(department_id=["<department_id>"])
```text

**Filter by geolocation:**

```text
zdx_list_software(geo_id=["<geo_id>"])
```text

**Filter by specific users:**

```text
zdx_list_software(user_ids=["<user_id_1>", "<user_id_2>"])
```text

**Filter by specific devices:**

```text
zdx_list_software(device_ids=["<device_id_1>", "<device_id_2>"])
```text

**Combine filters for targeted audits:**

```text
zdx_list_software(
  location_id=["<location_id>"],
  department_id=["<department_id>"]
)
```text

---

### Step 2: Get Software Version Details

For a specific software package, get detailed version distribution and device breakdown.

```text
zdx_get_software_details(software_key="<software_name_and_version>")
```text

**Filter by scope:**

```text
zdx_get_software_details(
  software_key="Google Chrome 120.0.6099.130",
  location_id=["<location_id>"]
)
```text

```text
zdx_get_software_details(
  software_key="Microsoft Teams",
  department_id=["<department_id>"]
)
```text

---

### Step 3: Cross-Reference with Device Data

For specific devices of interest, get full device details.

```text
zdx_get_device(device_id="<device_id>")
```text

To find devices owned by a specific user:

```text
zdx_list_devices(emails=["user@company.com"])
```text

To find devices in a specific location:

```text
zdx_list_devices(location_id=["<location_id>"])
```text

---

### Step 4: Present Audit Report

Assemble the `__ZDX_DATA__` payload defined in the *Data Payload Contract* and render it through `./templates/report.html.template` (see the **HTML OUTPUT** section). The template already produces the inventory table, KPI cards, compliance percentages, color coding, search/sort, and CSV export — do **not** hand-author any HTML or markdown table here.

What you DO write is the `analysis` block inside the payload. **Do not skip it.** This is what makes the audit useful:

- **`analysis.summary`** (3–5 sentences): the fleet's compliance posture. Cite the ratio of up-to-date vs. outdated software. Call out patterns (e.g., "Outdated Chrome is concentrated in APAC offices, suggesting MDM policy gaps in that region"). Quote actual counts from the `kpis` block.
- **`analysis.rootCause`** (1–3 sentences per EOL / vulnerable group): explain the risk concretely (e.g., "Java 8 is end-of-life with 200+ known CVEs. The 12 devices running it are exposed to remote code execution vulnerabilities").
- **`analysis.remediation`** (4–6 items): label each with a priority bucket and a concrete action.

| Priority | Apply to | Action |
|---|---|---|
| `Immediate` | EOL software | Immediate upgrade plan. Identify device owners, schedule maintenance windows, push updates via MDM. |
| `Investigate` | Vulnerable versions | Cross-reference with known CVEs. Prioritize devices in sensitive departments (Finance, Engineering). |
| `Monitor` | One version behind | Schedule automated updates via MDM or software distribution tools. |
| `Communicate` | Borderline current versions | Confirm auto-update policies are in place; report status to security/compliance. |

---

## Common Audit Scenarios

### Security Vulnerability Assessment

When a CVE is announced for a specific software version:

1. List software inventory filtered by the affected software name
2. Get details to identify exact versions installed
3. Cross-reference affected versions with CVE data
4. List impacted devices by location and department

```text
Example: CVE-2024-XXXXX affects Chrome < 120.0.6099.130

zdx_list_software()
→ Find "Google Chrome" entries

zdx_get_software_details(software_key="Google Chrome 119.0.6045.199")
→ Identify all devices running the vulnerable version

Report:
  Vulnerable Devices: 45
  Locations: Tokyo (25), Singapore (20)
  Priority: HIGH - Immediate patch required
```text

### Patch Rollout Progress

Track how a software update is rolling out across the organization:

1. List software and find the old and new versions
2. Compare device counts between versions
3. Filter by location to identify offices lagging behind

```text
Patch Rollout: Chrome 120.0.6099.130
  Deployed: 312 devices (87.4%)
  Pending: 45 devices (12.6%)
  
  By Location:
    San Jose: 100% deployed
    New York: 100% deployed
    London: 95% deployed
    Tokyo: 72% deployed ← lagging
    Singapore: 68% deployed ← lagging
```text

### Department-Specific Audit

For compliance requirements specific to a department:

```text
zdx_list_software(department_id=["<finance_dept_id>"])
```text

Useful for auditing regulated departments (Finance, Healthcare, Legal) that may have specific software requirements.

### License Compliance

Count software installations to verify license compliance:

```text
zdx_list_software()
→ Count installations of licensed software

Example:
  Adobe Acrobat Pro: 142 devices installed
  Licensed seats: 150
  Remaining: 8 seats available
```text

---

## Edge Cases

### No Software Data Available

```text
No software inventory data available for the specified filters.

Possible causes:
- ZDX agent version doesn't support software inventory
- Software inventory collection is not enabled
- The filtered scope (location/department) has no active devices

Action: Verify ZDX software inventory is enabled in the admin portal.
```text

### Large Inventory

If the software list is very long:

- Focus on key categories: browsers, security tools, collaboration apps, runtimes
- Filter by location or department to narrow scope
- Prioritize EOL or outdated versions

---

## Quick Reference

**Primary workflow:** List Software → Filter by Scope → Get Version Details → Cross-Reference Devices → Report

**Tools used:**

- `zdx_list_software()` -- organization-wide inventory
- `zdx_list_software(location_id, department_id, ...)` -- filtered inventory
- `zdx_get_software_details(software_key)` -- version details for a package
- `zdx_list_devices(emails, location_id, ...)` -- find specific devices
- `zdx_get_device(device_id)` -- device details

**Filter options (available on both list and details):**

- `location_id` -- ZDX location IDs
- `department_id` -- department IDs
- `geo_id` -- geolocation IDs
- `user_ids` -- specific user IDs
- `device_ids` -- specific device IDs

**Related skills:**

- [Troubleshoot User Experience](../troubleshoot-user-experience/) -- if software issues affect user experience
- [Analyze Application Health](../analyze-application-health/) -- if outdated software correlates with poor app scores
