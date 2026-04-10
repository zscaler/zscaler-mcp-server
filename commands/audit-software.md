---
disable-model-invocation: true
argument-hint: "[software_name] [location_or_department]"
description: "Audit software inventory across devices using ZDX data for compliance and vulnerability assessment."
---

# Audit Software Inventory

Audit software: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Software name** (optional -- list all if not provided)
- **Filter**: location, department, or user (optional)

## Step 2: List Software Inventory

```text
zdx_list_software()
```text

If a specific software was requested, filter the results.

## Step 3: Drill Into Specific Software

For targeted investigation:

```text
zdx_get_software_details(software_key="<software_name_and_version>")
```text

Check version distribution across devices.

## Step 4: Check Device Details

For devices with outdated or concerning software:

```text
zdx_list_devices(search="<filter>")
zdx_get_device(device_id="<id>")
```text

## Step 5: Present Report

**ALWAYS present data in HTML tables** in the chat response using `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling. Use color-coded rows: green (current), yellow (one version behind), red (EOL/vulnerable).

Include:

1. **Software inventory table** (software name, version(s), device count, status, risk level)
2. **Compliance summary table** (up to date count/%, one version behind count/%, EOL count/%)
3. **Detailed analysis** explaining the compliance posture, version distribution patterns, and geographic concentration of outdated software
4. **Security assessment** for each EOL/vulnerable entry with risk explanation
5. **Next steps / resolution** prioritized by risk:
   - Critical (EOL): immediate upgrade plan, MDM push, maintenance windows
   - High (known CVEs): cross-reference with CVE data, prioritize sensitive departments
   - Medium (one version behind): schedule automated updates
   - Low (current): verify auto-update policies

## Step 6: Generate Downloadable Artifacts — MANDATORY

**You MUST create BOTH files. Do NOT skip the HTML page.**

1. **Word document** (`software_inventory_audit_<date>.docx`): Executive summary, full inventory table, security findings, prioritized recommendations.

2. **Interactive HTML page** (`software_inventory_audit_<date>.html`): Use the complete HTML template from the `zdx-audit-software-inventory` skill. The file must be fully functional with working search bar, sortable columns, filter dropdowns, color-coded rows, summary dashboard, and CSV export button. All CSS and JavaScript inline — no external dependencies. Populate the `<tbody>` with one `<tr>` per software entry from the collected data.

**Write both files to disk and provide the file paths to the user.**
