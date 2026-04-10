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

**ALWAYS present ZDX data using HTML tables** in the chat for clear, structured output. Use `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling for readability.

After each table, provide:

1. **Detailed analysis** explaining the compliance posture, version distribution, and risk areas
2. **Security assessment** highlighting EOL, outdated, or vulnerable software
3. **Next steps / resolution** with specific remediation actions (patching, MDM push, upgrade plans) prioritized by risk

Use color-coded status indicators in tables:

- Green: Current version, no known vulnerabilities
- Yellow: One version behind or approaching EOL
- Red: EOL, known vulnerabilities, or significantly outdated

## Output Artifacts — MANDATORY

**You MUST generate BOTH files below. Do NOT skip the HTML page. Do NOT consider this optional. Both files are REQUIRED output for every software inventory audit.**

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `software_inventory_audit_<date>.docx` containing:

- Executive summary with compliance posture percentages
- Full software inventory table (software name, version, vendor, device count, user count, status, risk)
- Security findings section with EOL/vulnerable software details
- Recommendations section with prioritized remediation actions
- Scope and filters used for the audit

### 2. Interactive HTML Web Page (.html) — REQUIRED

Write a **fully functional, self-contained HTML file** to disk named `software_inventory_audit_<date>.html`. This file MUST contain working CSS and JavaScript — not placeholders or comments. Copy the template below and populate `<tbody>` with one `<tr>` per software entry from the collected data. Replace `{{TOTAL_SOFTWARE}}`, `{{TOTAL_DEVICES}}`, `{{COMPLIANCE_PCT}}`, and `{{CRITICAL_COUNT}}` with actual values.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Software Inventory Audit</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f6fa;color:#2d3436;padding:20px}
h1{text-align:center;margin-bottom:20px;color:#1a1a2e}
.summary{display:flex;gap:15px;justify-content:center;flex-wrap:wrap;margin-bottom:20px}
.card{background:#fff;border-radius:10px;padding:18px 28px;box-shadow:0 2px 8px rgba(0,0,0,.1);text-align:center;min-width:160px}
.card .num{font-size:2em;font-weight:700;color:#1a1a2e}
.card .label{font-size:.85em;color:#636e72;margin-top:4px}
.filters{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:18px}
.filters input,.filters select{padding:8px 14px;border:1px solid #ddd;border-radius:6px;font-size:.95em}
.filters input{min-width:260px}
.filters button{padding:8px 18px;background:#0984e3;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.95em}
.filters button:hover{background:#0767b2}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}
th{background:#1a1a2e;color:#fff;padding:10px 12px;cursor:pointer;position:sticky;top:0;user-select:none;white-space:nowrap}
th:hover{background:#2d3460}
td{padding:9px 12px;border-bottom:1px solid #eee}
tr.current{background:#d4edda}
tr.outdated{background:#fff3cd}
tr.eol{background:#f8d7da}
tr:hover{filter:brightness(.97)}
.status-current{color:#27ae60;font-weight:700}
.status-outdated{color:#e67e22;font-weight:700}
.status-eol{color:#e74c3c;font-weight:700}
@media(max-width:800px){.summary{flex-direction:column;align-items:center}table{font-size:.85em}}
</style>
</head>
<body>
<h1>Software Inventory Audit Report</h1>
<div class="summary">
  <div class="card"><div class="num" id="totalSw">{{TOTAL_SOFTWARE}}</div><div class="label">Total Software</div></div>
  <div class="card"><div class="num" id="totalDev">{{TOTAL_DEVICES}}</div><div class="label">Total Devices</div></div>
  <div class="card"><div class="num" id="compPct">{{COMPLIANCE_PCT}}%</div><div class="label">Compliance</div></div>
  <div class="card"><div class="num" id="critCnt" style="color:#e74c3c">{{CRITICAL_COUNT}}</div><div class="label">Critical / EOL</div></div>
</div>
<div class="filters">
  <input type="text" id="search" placeholder="Search software, vendor, version..." oninput="applyFilters()">
  <select id="statusFilter" onchange="applyFilters()"><option value="">All Status</option><option value="Current">Current</option><option value="Outdated">Outdated</option><option value="EOL">EOL</option></select>
  <select id="riskFilter" onchange="applyFilters()"><option value="">All Risk</option><option value="None">None</option><option value="Low">Low</option><option value="Medium">Medium</option><option value="High">High</option><option value="Critical">Critical</option></select>
  <button onclick="exportCSV()">Export CSV</button>
</div>
<table id="inventoryTable">
<thead><tr>
  <th onclick="sortTable(0)">Software &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(1)">Version &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(2)">Vendor &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(3)">Group &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(4)">Devices &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(5)">Users &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(6)">Status &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(7)">Risk &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="current|outdated|eol"> per software entry.
     Example row:
  <tr class="current">
    <td>Microsoft Teams</td><td>24.1.414</td><td>Microsoft</td><td>Collaboration</td>
    <td>290</td><td>280</td><td class="status-current">Current</td><td>None</td>
  </tr>
-->
</tbody>
</table>
<script>
let sortDir=[1,1,1,1,1,1,1,1];
function sortTable(c){const t=document.getElementById('inventoryTable'),b=t.tBodies[0],rows=Array.from(b.rows);sortDir[c]*=-1;rows.sort((a,b_)=>{let x=a.cells[c].textContent.trim(),y=b_.cells[c].textContent.trim();const xn=parseFloat(x),yn=parseFloat(y);if(!isNaN(xn)&&!isNaN(yn))return(xn-yn)*sortDir[c];return x.localeCompare(y)*sortDir[c]});rows.forEach(r=>b.appendChild(r))}
function applyFilters(){const q=document.getElementById('search').value.toLowerCase(),s=document.getElementById('statusFilter').value,r=document.getElementById('riskFilter').value;const rows=document.querySelectorAll('#inventoryTable tbody tr');rows.forEach(row=>{const txt=row.textContent.toLowerCase(),st=row.cells[6]?.textContent.trim()||'',ri=row.cells[7]?.textContent.trim()||'';let show=true;if(q&&!txt.includes(q))show=false;if(s&&st!==s)show=false;if(r&&ri!==r)show=false;row.style.display=show?'':'none'})}
function exportCSV(){const t=document.getElementById('inventoryTable'),rows=Array.from(t.rows).filter(r=>r.style.display!=='none');let csv=rows.map(r=>Array.from(r.cells).map(c=>'"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='software_inventory.csv';a.click()}
</script>
</body>
</html>
```text

**MANDATORY STEPS:**

1. Copy this template exactly
2. Replace the `{{...}}` placeholders in the summary cards with real values
3. Add one `<tr>` row inside `<tbody>` for every software entry collected from the API
4. Set the row class to `current`, `outdated`, or `eol` based on status
5. Write the file to disk and provide the file path to the user

**Both files must be saved to the user's working directory** and the file paths provided in the response.

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

Present all data in **HTML table format** with detailed analysis.

**Software Inventory Overview (HTML table):**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Software</th>
  <th style="padding:8px;border:1px solid #ddd">Version(s)</th>
  <th style="padding:8px;border:1px solid #ddd">Devices</th>
  <th style="padding:8px;border:1px solid #ddd">Status</th>
  <th style="padding:8px;border:1px solid #ddd">Risk</th>
</tr></thead>
<tbody>
  <tr style="background:#d4edda"><td style="padding:8px;border:1px solid #ddd">Microsoft Teams</td><td style="padding:8px">24.1.x (290)</td><td style="padding:8px">290</td><td style="padding:8px;color:green;font-weight:bold">Current</td><td style="padding:8px">None</td></tr>
  <tr style="background:#fff3cd"><td style="padding:8px;border:1px solid #ddd">Google Chrome</td><td style="padding:8px">120.x (312), 119.x (45)</td><td style="padding:8px">357</td><td style="padding:8px;color:orange;font-weight:bold">45 Outdated</td><td style="padding:8px">Medium</td></tr>
  <tr style="background:#f8d7da"><td style="padding:8px;border:1px solid #ddd">Java Runtime</td><td style="padding:8px">21.x (180), 17.x (95), 8.x (12)</td><td style="padding:8px">287</td><td style="padding:8px;color:red;font-weight:bold">12 EOL</td><td style="padding:8px">Critical</td></tr>
</tbody></table>
```text

**Compliance Summary (HTML table):**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Category</th>
  <th style="padding:8px;border:1px solid #ddd">Count</th>
  <th style="padding:8px;border:1px solid #ddd">Percentage</th>
</tr></thead>
<tbody>
  <tr style="background:#d4edda"><td style="padding:8px">Up to Date</td><td style="padding:8px">792</td><td style="padding:8px">93.5%</td></tr>
  <tr style="background:#fff3cd"><td style="padding:8px">One Version Behind</td><td style="padding:8px">43</td><td style="padding:8px">5.1%</td></tr>
  <tr style="background:#f8d7da"><td style="padding:8px">EOL / Unsupported</td><td style="padding:8px">12</td><td style="padding:8px">1.4%</td></tr>
</tbody></table>
```text

**After the tables, ALWAYS provide:**

1. **Analysis:** Summarize the fleet's compliance posture. Highlight the ratio of up-to-date vs outdated software. Identify patterns (e.g., "Outdated Chrome is concentrated in APAC offices, suggesting MDM policy gaps in that region").

2. **Security Assessment:** For each EOL or vulnerable software, explain the risk (e.g., "Java 8 is end-of-life with 200+ known CVEs. The 12 devices running it are exposed to remote code execution vulnerabilities").

3. **Next Steps / Resolution:**
   - **Critical (EOL):** Immediate upgrade plan. Identify device owners, schedule maintenance windows, and push updates via MDM.
   - **High (vulnerable versions):** Cross-reference with known CVEs. Prioritize devices in sensitive departments (Finance, Engineering).
   - **Medium (one version behind):** Schedule automated updates via MDM or software distribution tools.
   - **Low (current):** No action needed. Verify auto-update policies are in place.

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
