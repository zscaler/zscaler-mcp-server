---
name: zdx-compare-location-experience
description: "Compare digital experience across locations, departments, and geolocations using ZDX data. Identifies which offices or regions have the best and worst experience for specific applications, detects location-specific issues, and provides optimization recommendations. Aligned with ZDX Copilot analytics and optimization use cases. Use when an administrator asks: 'Which office has the worst experience?', 'Compare application performance between locations', 'Is the Dallas office having network issues?', or 'Show me ZDX scores by department.'"
---

# ZDX: Compare Location Experience

## Keywords
compare locations, location experience, office comparison, department comparison, regional performance, site health, location score, office performance, worst office, best practices, optimization, geographic analysis, location ranking

## Overview

Compare digital experience across different locations, departments, and geolocations to identify which sites perform best and worst. This skill uses ZDX filtering capabilities to break down application scores, metrics, alerts, and device health by organizational dimensions, enabling proactive optimization and targeted remediation.

**Use this skill when:** An administrator wants to compare application experience across offices, identify the worst-performing locations, investigate whether an issue is location-specific, or optimize network configuration for underperforming sites.

**ZDX Copilot alignment:** This skill covers the Analytics and Optimization categories -- comparing performance across organizational dimensions and recommending improvements.

---

## Data Presentation Requirements

**ALWAYS present ZDX data using HTML tables** for clear, structured output. Use `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling for readability.

After each table, provide:
1. **Detailed analysis** explaining the performance differences between locations and what they indicate
2. **Root cause identification** for underperforming locations (DNS, ISP, WiFi, device fleet age, etc.)
3. **Next steps / resolution** with site-specific remediation actions prioritized by impact and feasibility

Use color-coded rows based on location ranking:
- Green: Top-performing locations (score 66-100)
- Yellow: Borderline locations (score 34-65)
- Red: Worst-performing locations (score 0-33)

## Output Artifacts — MANDATORY

**You MUST generate BOTH files below. Do NOT skip the HTML page. Do NOT consider this optional. Both files are REQUIRED output for every location comparison.**

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `location_comparison_report_<date>.docx` containing:
- Executive summary with best/worst performing locations
- Location ranking table (rank, location, score, PFT, DNS, availability, poor users, alerts)
- Per-location analysis for underperforming sites with metric breakdowns
- Root cause analysis for worst performers (DNS, ISP, WiFi, device fleet)
- Cross-location metric comparison for each application
- Site-specific remediation actions prioritized by impact

### 2. Interactive HTML Web Page (.html) — REQUIRED

Write a **fully functional, self-contained HTML file** to disk named `location_comparison_report_<date>.html`. This file MUST contain working CSS and JavaScript — not placeholders or comments. Copy the template below and populate `<tbody>` with one `<tr>` per location. Replace `{{TOTAL_LOCATIONS}}`, `{{BEST_LOCATION}}`, `{{WORST_LOCATION}}`, `{{AVG_SCORE}}`, and `{{ALERT_COUNT}}` with actual values.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Location Comparison Report</title>
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
tr.top{background:#d4edda}
tr.borderline{background:#fff3cd}
tr.poor{background:#f8d7da}
tr:hover{filter:brightness(.97)}
.status-top{color:#27ae60;font-weight:700}
.status-borderline{color:#e67e22;font-weight:700}
.status-poor{color:#e74c3c;font-weight:700}
@media(max-width:800px){.summary{flex-direction:column;align-items:center}table{font-size:.85em}}
</style>
</head>
<body>
<h1>Location Experience Comparison Report</h1>
<div class="summary">
  <div class="card"><div class="num">{{TOTAL_LOCATIONS}}</div><div class="label">Total Locations</div></div>
  <div class="card"><div class="num" style="color:#27ae60">{{BEST_LOCATION}}</div><div class="label">Best Location</div></div>
  <div class="card"><div class="num" style="color:#e74c3c">{{WORST_LOCATION}}</div><div class="label">Worst Location</div></div>
  <div class="card"><div class="num">{{AVG_SCORE}}</div><div class="label">Avg Score</div></div>
  <div class="card"><div class="num">{{ALERT_COUNT}}</div><div class="label">Active Alerts</div></div>
</div>
<div class="filters">
  <input type="text" id="search" placeholder="Search location, application..." oninput="applyFilters()">
  <select id="tierFilter" onchange="applyFilters()"><option value="">All Tiers</option><option value="Top">Top</option><option value="Borderline">Borderline</option><option value="Poor">Poor</option></select>
  <button onclick="exportCSV()">Export CSV</button>
</div>
<table id="locationTable">
<thead><tr>
  <th onclick="sortTable(0)">Rank &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(1)">Location &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(2)">Score &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(3)">Page Fetch Time &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(4)">DNS &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(5)">Availability &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(6)">Poor Users &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(7)">Active Alerts &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="top|borderline|poor"> per location.
     Example row:
  <tr class="top">
    <td>1</td><td>San Jose</td><td class="status-top">92</td><td>1.8s</td>
    <td>18ms</td><td>100%</td><td>0/120</td><td>0</td>
  </tr>
-->
</tbody>
</table>
<script>
let sortDir=[1,1,1,1,1,1,1,1];
function sortTable(c){const t=document.getElementById('locationTable'),b=t.tBodies[0],rows=Array.from(b.rows);sortDir[c]*=-1;rows.sort((a,b_)=>{let x=a.cells[c].textContent.trim(),y=b_.cells[c].textContent.trim();const xn=parseFloat(x),yn=parseFloat(y);if(!isNaN(xn)&&!isNaN(yn))return(xn-yn)*sortDir[c];return x.localeCompare(y)*sortDir[c]});rows.forEach(r=>b.appendChild(r))}
function applyFilters(){const q=document.getElementById('search').value.toLowerCase(),tier=document.getElementById('tierFilter').value;const rows=document.querySelectorAll('#locationTable tbody tr');rows.forEach(row=>{const txt=row.textContent.toLowerCase();let show=true;if(q&&!txt.includes(q))show=false;if(tier){const cls=row.className;if(tier==='Top'&&cls!=='top')show=false;if(tier==='Borderline'&&cls!=='borderline')show=false;if(tier==='Poor'&&cls!=='poor')show=false}row.style.display=show?'':'none'})}
function exportCSV(){const t=document.getElementById('locationTable'),rows=Array.from(t.rows).filter(r=>r.style.display!=='none');let csv=rows.map(r=>Array.from(r.cells).map(c=>'"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='location_comparison.csv';a.click()}
</script>
</body>
</html>
```

**MANDATORY STEPS:**
1. Copy this template exactly
2. Replace the `{{...}}` placeholders in the summary cards with real values
3. Add one `<tr>` row inside `<tbody>` for every location
4. Set the row class to `top`, `borderline`, or `poor` based on score tier
5. Write the file to disk and provide the file path to the user

**Both files must be saved to the user's working directory** and the file paths provided in the response.

---

## Workflow

### Step 1: List Available Locations and Departments

First, enumerate the organizational dimensions available for comparison.

**List locations:**
```
zdx_list_locations()
```

**List departments:**
```
zdx_list_departments()
```

Note the IDs returned -- these are used as filters in subsequent calls.

---

### Step 2: Compare Application Scores Across Locations

For each application of interest, retrieve scores filtered by different locations.

**Location A:**
```
zdx_list_applications(location_id=["<location_a_id>"], since=24)
```

**Location B:**
```
zdx_list_applications(location_id=["<location_b_id>"], since=24)
```

**Location C:**
```
zdx_list_applications(location_id=["<location_c_id>"], since=24)
```

Compile the scores side by side to identify which locations are underperforming.

---

### Step 3: Drill Into Score Trends for Underperforming Locations

For the worst-performing location, check the score trend.

```
zdx_get_application_score_trend(
  app_id="<app_id>",
  location_id=["<worst_location_id>"],
  since=24
)
```

Compare with a healthy location:
```
zdx_get_application_score_trend(
  app_id="<app_id>",
  location_id=["<healthy_location_id>"],
  since=24
)
```

**What to look for:**
- Does the underperforming location show a consistent low score or a sudden drop?
- Does the score correlate with specific times of day (peak hours)?
- Are multiple applications affected at this location, or just one?

---

### Step 4: Compare Metrics Across Locations

Drill into metrics for the specific application at each location.

**Page Fetch Time by location:**
```
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="pft",
  location_id=["<location_a_id>"]
)
```

```
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="pft",
  location_id=["<location_b_id>"]
)
```

**DNS by location:**
```
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="dns",
  location_id=["<location_a_id>"]
)
```

**Availability by location:**
```
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="availability",
  location_id=["<location_a_id>"]
)
```

---

### Step 5: Compare Impacted Users by Location

Understand user impact at each location.

```
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor",
  location_id=["<worst_location_id>"]
)
```

```
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor",
  location_id=["<healthy_location_id>"]
)
```

**Calculate impact ratios:** If Location A has 5 poor users out of 50 total (10%) vs Location B with 25 poor users out of 100 total (25%), Location B has a more severe issue despite Location A having fewer total users.

---

### Step 6: Check Location-Specific Alerts

```
zdx_list_alerts(location_id=["<worst_location_id>"], since=48)
```

```
zdx_list_historical_alerts(location_id=["<worst_location_id>"], since=168)
```

Recurring alerts at a specific location indicate a persistent infrastructure issue at that site.

---

### Step 7: Assess Device Health at Underperforming Locations

Check if the issue is device-related rather than network-related.

```
zdx_list_devices(location_id=["<worst_location_id>"])
```

For specific devices showing issues:
```
zdx_get_device(device_id="<device_id>")
```

Check for:
- High CPU/memory usage across many devices (hardware refresh needed)
- Outdated ZCC agent versions
- WiFi issues (common in specific offices)

---

### Step 8: Present Comparison Report

Present all data in **HTML table format** with detailed analysis.

**Location Ranking (HTML table):**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Rank</th>
  <th style="padding:8px;border:1px solid #ddd">Location</th>
  <th style="padding:8px;border:1px solid #ddd">Score</th>
  <th style="padding:8px;border:1px solid #ddd">Page Fetch Time</th>
  <th style="padding:8px;border:1px solid #ddd">DNS</th>
  <th style="padding:8px;border:1px solid #ddd">Availability</th>
  <th style="padding:8px;border:1px solid #ddd">Poor Users</th>
  <th style="padding:8px;border:1px solid #ddd">Active Alerts</th>
</tr></thead>
<tbody>
  <tr style="background:#d4edda"><td style="padding:8px">1</td><td style="padding:8px">San Jose</td><td style="padding:8px;font-weight:bold;color:green">92</td><td style="padding:8px">1.8s</td><td style="padding:8px">18ms</td><td style="padding:8px">100%</td><td style="padding:8px">0/120</td><td style="padding:8px">0</td></tr>
  <tr style="background:#d4edda"><td style="padding:8px">2</td><td style="padding:8px">London</td><td style="padding:8px;font-weight:bold;color:green">88</td><td style="padding:8px">2.1s</td><td style="padding:8px">22ms</td><td style="padding:8px">99%</td><td style="padding:8px">2/85</td><td style="padding:8px">0</td></tr>
  <tr style="background:#fff3cd"><td style="padding:8px">4</td><td style="padding:8px">Tokyo</td><td style="padding:8px;font-weight:bold;color:orange">71</td><td style="padding:8px">3.8s</td><td style="padding:8px">45ms</td><td style="padding:8px">98%</td><td style="padding:8px">8/55</td><td style="padding:8px">1</td></tr>
  <tr style="background:#f8d7da"><td style="padding:8px">5</td><td style="padding:8px">Dallas</td><td style="padding:8px;font-weight:bold;color:red">42</td><td style="padding:8px">8.2s</td><td style="padding:8px">180ms</td><td style="padding:8px">95%</td><td style="padding:8px">35/90</td><td style="padding:8px">2</td></tr>
</tbody></table>
```

**After the table, ALWAYS provide:**

1. **Analysis:** "Dallas is the clear outlier with a score of 42, significantly below the organization average of 75. DNS resolution at 180ms is 4x the average of other locations (28ms), which is cascading into elevated Page Fetch Times. Tokyo is borderline at 71 and should be monitored. The top 3 locations (San Jose, London, Singapore) are all healthy."

2. **Root Cause for Worst Performer:** "Dallas shows a persistent DNS infrastructure issue. Historical data reveals 5 similar DNS alerts in the past 2 weeks, all isolated to this location. The local DNS resolver is likely experiencing capacity or configuration problems."

3. **Next Steps / Resolution:**
   - **Dallas (Critical -- score 42):**
     1. Investigate local DNS server health and capacity
     2. Compare DNS resolver configuration with healthy locations (San Jose, London)
     3. Consider switching to a redundant DNS provider or Zscaler DNS proxy
     4. If using local DNS caching, verify cache integrity and TTL settings
   - **Tokyo (Monitor -- score 71):**
     1. Review ISP path quality for latency sources
     2. Track the active alert -- if it persists beyond 24h, escalate
   - **All Other Locations:** No action needed. Scores are healthy.

---

## Department Comparison Variant

The same workflow applies when comparing departments instead of locations.

```
zdx_list_applications(department_id=["<dept_a_id>"], since=24)
zdx_list_applications(department_id=["<dept_b_id>"], since=24)
```

**Department comparison is useful for:**
- Understanding if a specific team is disproportionately affected
- Compliance reporting (e.g., "How is the Finance team's experience?")
- Device fleet differences between departments (older hardware, different OS)

---

## Multi-Application Comparison

Compare how all applications perform at a single location.

```
zdx_list_applications(location_id=["<location_id>"], since=24)
```

If all applications are degraded at one location:
- The issue is likely network infrastructure (ISP, WiFi, LAN)
- Not application-specific

If only one application is degraded at a location:
- Likely application-specific routing or server issue for that region
- Check application CDN or server closest to that location

---

## Edge Cases

### Location with No Active Devices

```
No active devices found at location "<location_name>" in the
requested time window. The office may be closed, or devices
may not be reporting.

Verify:
- Is the office operational?
- Are ZDX agents deployed at this location?
- Check the 'since' parameter (try a wider window)
```

### All Locations Equally Degraded

If all locations show similar poor scores:
- The issue is not location-specific
- Likely an application server or Zscaler service-wide event
- Switch to the **Analyze Application Health** skill

### New Location Without Baseline

For recently added locations with no historical data:
- Cannot reliably compare with established locations
- Collect at least 1 week of data before drawing conclusions
- Use current metrics as the initial baseline

---

## Quick Reference

**Primary workflow:** List Locations/Depts → Compare App Scores → Drill Trends → Compare Metrics → Check Users → Review Alerts → Report

**Tools used:**
- `zdx_list_locations()` -- enumerate locations
- `zdx_list_departments()` -- enumerate departments
- `zdx_list_applications(location_id/department_id)` -- scores by dimension
- `zdx_get_application_score_trend(app_id, location_id)` -- trend by location
- `zdx_get_application_metric(app_id, metric_name, location_id)` -- metrics by location
- `zdx_list_application_users(app_id, score_bucket, location_id)` -- impacted users by location
- `zdx_list_alerts(location_id)` -- location-specific alerts
- `zdx_list_historical_alerts(location_id)` -- recurring patterns
- `zdx_list_devices(location_id)` -- devices at a location
- `zdx_get_device(device_id)` -- device health details

**Comparison dimensions:**
- `location_id` -- by office / ZIA location
- `department_id` -- by business unit
- `geo_id` -- by geographic region

**Related skills:**
- [Troubleshoot User Experience](../troubleshoot-user-experience/) -- individual user drill-down
- [Analyze Application Health](../analyze-application-health/) -- org-wide app health
- [Investigate Alerts](../investigate-alerts/) -- alert-focused investigation
