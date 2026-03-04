# ZDX (Zscaler Digital Experience) Steering

## Overview

ZDX provides end-to-end visibility into user digital experience — application health, device performance, network path analysis, and alerting. It helps IT teams proactively detect and troubleshoot issues before users report them.

## Critical: ZDX Is Read-Only

All ZDX tools are **read-only query operations**. There are no create/update/delete operations. The only exception is deep traces, which can be started to capture detailed network path data.

## Key Concepts

- **Applications**: Monitored SaaS and internal applications (each has a ZDX score)
- **Devices**: End-user devices running Zscaler Client Connector
- **ZDX Scores**: Health indicator from 0-100. Higher is better.
- **Alerts**: Automated notifications triggered when performance degrades
- **Deep Traces**: Detailed hop-by-hop network path analysis for a specific device
- **Departments**: Organizational departments for filtering
- **Locations**: Office/site locations for filtering

## ZDX Score Ranges

| Score | Status | Meaning |
|-------|--------|---------|
| 66–100 | Good | No significant issues |
| 34–65 | Okay | Some degradation, investigate further |
| 0–33 | Poor | Major issues affecting users |

## Critical: Filtering Parameters

ZDX query tools accept optional filters that **significantly improve result quality** and prevent overwhelming responses on large tenants:

- `location_id` — Filter by office/site location (list of strings)
- `department_id` — Filter by department (list of strings)
- `geo_id` — Filter by geolocation (list of strings)
- `since` — Number of **hours** to look back (integer, default: 2). Example: `since=24` means "last 24 hours"

**Always ask the user for scope** (which location? which department? what timeframe?) before running broad ZDX queries.

Use `zdx_list_locations` and `zdx_list_departments` to discover valid filter IDs.

## Common Workflows

### Single User Troubleshooting

Use when a specific user reports issues with an application.

```
1. zdx_list_devices               → Find the user's device by name/email
2. zdx_get_device                 → Get device health details
3. zdx_list_applications          → List monitored apps
4. zdx_get_application            → Get app score for the user's location (since=2)
5. zdx_get_application_score_trend → Check if scores dropped recently (since=24)
6. zdx_get_application_metric     → Drill into specific metrics:
   - metric_name="dns"           → DNS resolution time
   - metric_name="availability"  → App availability percentage
   - metric_name="pft"           → Page fetch time (web apps)
7. zdx_list_alerts                → Check if there's an active alert for this app/device
8. zdx_list_device_deep_traces    → Check for existing deep traces
9. zdx_get_device_deep_trace      → Analyze network path if trace exists
```

### Organization-Wide Application Health Analysis

Use for understanding application health across the organization.

```
1. zdx_list_applications              → Get all monitored apps with scores
2. Sort by score to identify degraded apps (score < 66)
3. For each degraded app:
   a. zdx_get_application             → Get overall score and impacted locations
   b. zdx_get_application_score_trend → Check trend over 24h (since=24)
   c. zdx_get_application_metric      → Check DNS, availability, PFT
   d. zdx_list_application_users      → See how many users are impacted
4. zdx_list_alerts                    → Cross-reference with active alerts
5. Present report: ranked apps, scores, trends, impacted user counts
```

### Alert Investigation

Use when investigating active or historical alerts.

```
1. zdx_list_alerts                 → List active alerts
2. zdx_get_alert                   → Get alert details (severity, trigger, affected app)
3. zdx_list_alert_affected_devices → See which devices/users are impacted
4. zdx_get_application_score_trend → Correlate with score timeline (did score drop when alert fired?)
5. zdx_get_application_metric      → Identify which metric degraded (DNS? availability? PFT?)
6. zdx_list_historical_alerts      → Check if this is a recurring issue
7. Present: alert scope, root cause hypothesis, affected user count, historical pattern
```

### Software Inventory Audit

Use for patch compliance, license audits, or security assessments.

```
1. zdx_list_software      → List all software across the fleet
   - Filter by location_id, department_id, or specific device
2. zdx_get_software_details → Get version details, device count per version
3. Cross-reference with zdx_list_devices → Identify devices running outdated versions
4. Present: software name, version distribution, devices needing updates
```

### Location/Department Experience Comparison

Use for comparing digital experience across sites or teams.

```
1. zdx_list_locations    → Get all location IDs
2. zdx_list_departments  → Get all department IDs
3. For each location/department:
   a. zdx_get_application (with location_id or department_id filter)
   b. zdx_get_application_score_trend (filtered)
4. Compare scores across locations/departments
5. zdx_list_alerts (filtered by location)
6. Present: ranked locations/departments by experience quality
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zdx_list_applications` | List all monitored applications with scores |
| `zdx_get_application` | Get application score and impacted locations |
| `zdx_get_application_score_trend` | Get application score history over time |
| `zdx_get_application_metric` | Get specific metrics (dns, pft, availability) |
| `zdx_list_application_users` | List users for a specific application |
| `zdx_get_application_user` | Get specific user's application experience |
| `zdx_list_devices` | List monitored devices |
| `zdx_get_device` | Get device health details |
| `zdx_list_alerts` | List active alerts |
| `zdx_get_alert` | Get alert details |
| `zdx_list_alert_affected_devices` | List devices affected by a specific alert |
| `zdx_list_historical_alerts` | List past/resolved alerts |
| `zdx_list_software` | List software inventory across devices |
| `zdx_get_software_details` | Get software version details |
| `zdx_list_departments` | List departments (for filtering) |
| `zdx_list_locations` | List locations (for filtering) |
| `zdx_list_device_deep_traces` | List deep traces for a device |
| `zdx_get_device_deep_trace` | Get specific deep trace results |

All tools are **read-only**.

## Application Metric Types

| Metric Name | What It Measures | Use Case |
|-------------|-----------------|----------|
| `dns` | DNS resolution time | Slow DNS = name resolution issues |
| `availability` | Application availability % | Low = app or server is down/unreachable |
| `pft` | Page fetch time (web apps) | High PFT = slow page load |

## Output Artifacts — MANDATORY

**For ALL ZDX workflows above, you MUST generate BOTH of the following files after collecting data. Do NOT skip the HTML page.**

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk with a name matching the workflow:
- `user_experience_diagnosis_<date>.docx`
- `application_health_report_<date>.docx`
- `alert_investigation_report_<date>.docx`
- `software_inventory_audit_<date>.docx`
- `location_comparison_report_<date>.docx`

Contents: Executive summary, full data tables, root cause analysis, and prioritized remediation actions.

### 2. Interactive HTML Web Page (.html) — REQUIRED

Write a **fully functional, self-contained HTML file** to disk with a matching name (e.g., `application_health_report_<date>.html`). The file MUST contain:

- **Working CSS and JavaScript** (not placeholders or comments)
- **Search bar** at the top for real-time text filtering across all columns
- **Column sorting** (click column headers to sort ascending/descending)
- **Filter dropdowns** appropriate to the data (Status, Priority, Risk, etc.)
- **Summary dashboard** at the top with key metrics (totals, counts, percentages)
- **Color-coded rows** (green/yellow/red) based on status/score/priority
- **Export CSV button** to download the filtered view
- All CSS and JavaScript **inline** (single self-contained file, no external dependencies)

Use this base template and adapt columns/filters to the specific workflow:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ZDX Report</title>
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
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}
th{background:#1a1a2e;color:#fff;padding:10px 12px;cursor:pointer;position:sticky;top:0;user-select:none;white-space:nowrap}
th:hover{background:#2d3460}
td{padding:9px 12px;border-bottom:1px solid #eee}
tr.good,tr.ok,tr.current,tr.top,tr.low{background:#d4edda}
tr.okay,tr.degraded,tr.outdated,tr.borderline,tr.medium{background:#fff3cd}
tr.poor,tr.critical,tr.eol,tr.high{background:#f8d7da}
tr:hover{filter:brightness(.97)}
</style>
</head>
<body>
<h1><!-- Report Title --></h1>
<div class="summary"><!-- Summary cards with actual values --></div>
<div class="filters">
  <input type="text" id="search" placeholder="Search..." oninput="applyFilters()">
  <!-- Add appropriate <select> dropdowns -->
  <button onclick="exportCSV()">Export CSV</button>
</div>
<table id="dataTable">
<thead><tr><!-- Column headers with onclick="sortTable(N)" --></tr></thead>
<tbody><!-- One <tr> per data row with appropriate class --></tbody>
</table>
<script>
let sortDir=[];
function sortTable(c){const t=document.getElementById('dataTable'),b=t.tBodies[0],rows=Array.from(b.rows);if(!sortDir[c])sortDir[c]=1;sortDir[c]*=-1;rows.sort((a,b_)=>{let x=a.cells[c].textContent.trim(),y=b_.cells[c].textContent.trim();const xn=parseFloat(x),yn=parseFloat(y);if(!isNaN(xn)&&!isNaN(yn))return(xn-yn)*sortDir[c];return x.localeCompare(y)*sortDir[c]});rows.forEach(r=>b.appendChild(r))}
function applyFilters(){const q=document.getElementById('search').value.toLowerCase();const selects=document.querySelectorAll('.filters select');const rows=document.querySelectorAll('#dataTable tbody tr');rows.forEach(row=>{const txt=row.textContent.toLowerCase();let show=txt.includes(q);selects.forEach(sel=>{if(sel.value){const ci=parseInt(sel.dataset.col);if(ci>=0&&row.cells[ci]&&row.cells[ci].textContent.trim()!==sel.value)show=false}});row.style.display=show?'':'none'})}
function exportCSV(){const t=document.getElementById('dataTable'),rows=Array.from(t.rows).filter(r=>r.style.display!=='none');let csv=rows.map(r=>Array.from(r.cells).map(c=>'"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='zdx_report.csv';a.click()}
</script>
</body>
</html>
```

**MANDATORY STEPS:** Copy this template, replace placeholders with real data, add `<tr>` rows for every data entry, set row classes for color coding, write the file to disk, and provide the file path to the user.

**Both files must be saved to the user's working directory.**

## Best Practices

1. **Start with the score, then drill down** — Check app scores first, then investigate metrics for degraded apps only
2. **Always use time context** — Use `since` parameter. Default 2h is narrow; use `since=24` or `since=72` for trend analysis
3. **Filter by location/department** — Prevents overwhelming responses and helps isolate regional issues
4. **Correlate alerts with metrics** — An alert tells you something is wrong; metrics tell you what's wrong
5. **Check historical alerts** — Recurring alerts suggest a systemic issue, not a one-time incident
6. **Use deep traces for network path issues** — When metrics point to network problems (high DNS, TCP errors), deep traces show the exact hop where latency or drops occur
7. **Combine with other services** — ZDX tells you what's degraded; ZPA/ZIA steering files help you check if policy or connectivity is the cause
