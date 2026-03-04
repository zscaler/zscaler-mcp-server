---
name: zdx-analyze-application-health
description: "Analyze the health of one or more monitored applications across the organization using ZDX scores, metrics, and affected-user breakdowns. Identifies which applications are degraded, which metrics are the bottleneck, and which users are most impacted. Aligned with ZDX Copilot analytics use cases. Use when an administrator asks: 'How are my applications performing?', 'Which apps have low ZDX scores?', 'Show me the number of applications impacted by alerts', or 'What is the ZDX Score for Zoom?'"
---

# ZDX: Analyze Application Health

## Keywords
application health, zdx score, application performance, app monitoring, degraded apps, poor score, application analytics, score trend, page fetch time, dns time, availability, impacted users, application overview

## Overview

Perform an organization-wide analysis of application health using ZDX. This skill retrieves all monitored applications, identifies those with degraded or poor scores, drills into metric-level details to find the bottleneck, and lists the most impacted users. It answers the "big picture" question: How are our applications performing right now?

**Use this skill when:** An administrator wants a health overview of monitored applications, needs to identify which apps are underperforming, or wants to compare application performance across locations or departments.

**ZDX Copilot alignment:** This skill covers the Analytics category -- "Show me the number of applications impacted by alerts", "What is John Doe's ZDX Score for the Zoom application in the last 4 hours?"

---

## Data Presentation Requirements

**ALWAYS present ZDX data using HTML tables** for clear, structured output. Use `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling for readability.

After each table, provide:
1. **Detailed analysis** explaining what the data means in plain language
2. **Root cause identification** for degraded or poor applications
3. **Next steps / resolution** with specific, actionable recommendations prioritized by impact

Use color-coded status indicators in tables:
- Green/Good: scores 66-100, metrics within normal range
- Yellow/Okay: scores 34-65, metrics approaching thresholds
- Red/Poor: scores 0-33, metrics exceeding thresholds

## Output Artifacts — MANDATORY

**You MUST generate BOTH files below. Do NOT skip the HTML page. Do NOT consider this optional. Both files are REQUIRED output for every application health analysis.**

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `application_health_report_<date>.docx` containing:
- Executive summary with overall health posture (healthy/degraded/poor counts)
- Application health table (app name, score, status, PFT, DNS, availability, impacted users, bottleneck)
- Per-application deep dive for degraded/poor apps with metric trends
- Root cause analysis per degraded application
- User impact breakdown by location and department
- Prioritized remediation actions

### 2. Interactive HTML Web Page (.html) — REQUIRED

Write a **fully functional, self-contained HTML file** to disk named `application_health_report_<date>.html`. This file MUST contain working CSS and JavaScript — not placeholders or comments. Copy the template below and populate `<tbody>` with one `<tr>` per application. Replace `{{TOTAL_APPS}}`, `{{GOOD_COUNT}}`, `{{OKAY_COUNT}}`, `{{POOR_COUNT}}`, and `{{MOST_IMPACTED}}` with actual values.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Application Health Report</title>
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
tr.good{background:#d4edda}
tr.okay{background:#fff3cd}
tr.poor{background:#f8d7da}
tr:hover{filter:brightness(.97)}
.status-good{color:#27ae60;font-weight:700}
.status-okay{color:#e67e22;font-weight:700}
.status-poor{color:#e74c3c;font-weight:700}
@media(max-width:800px){.summary{flex-direction:column;align-items:center}table{font-size:.85em}}
</style>
</head>
<body>
<h1>Application Health Report</h1>
<div class="summary">
  <div class="card"><div class="num">{{TOTAL_APPS}}</div><div class="label">Total Apps</div></div>
  <div class="card"><div class="num" style="color:#27ae60">{{GOOD_COUNT}}</div><div class="label">Good</div></div>
  <div class="card"><div class="num" style="color:#e67e22">{{OKAY_COUNT}}</div><div class="label">Okay</div></div>
  <div class="card"><div class="num" style="color:#e74c3c">{{POOR_COUNT}}</div><div class="label">Poor</div></div>
  <div class="card"><div class="num">{{MOST_IMPACTED}}</div><div class="label">Most Impacted</div></div>
</div>
<div class="filters">
  <input type="text" id="search" placeholder="Search application, bottleneck..." oninput="applyFilters()">
  <select id="statusFilter" onchange="applyFilters()"><option value="">All Status</option><option value="Good">Good</option><option value="Okay">Okay</option><option value="Poor">Poor</option></select>
  <select id="bottleneckFilter" onchange="applyFilters()"><option value="">All Bottlenecks</option><option value="DNS">DNS</option><option value="PFT">PFT</option><option value="Availability">Availability</option><option value="None">None</option></select>
  <button onclick="exportCSV()">Export CSV</button>
</div>
<table id="healthTable">
<thead><tr>
  <th onclick="sortTable(0)">Application &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(1)">Score &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(2)">Status &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(3)">Page Fetch Time &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(4)">DNS &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(5)">Availability &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(6)">Impacted Users &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(7)">Bottleneck &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="good|okay|poor"> per application.
     Example row:
  <tr class="poor">
    <td>Microsoft 365</td><td>28</td><td class="status-poor">Poor</td><td>12.4s</td>
    <td>22ms</td><td>94%</td><td>47</td><td>PFT</td>
  </tr>
-->
</tbody>
</table>
<script>
let sortDir=[1,1,1,1,1,1,1,1];
function sortTable(c){const t=document.getElementById('healthTable'),b=t.tBodies[0],rows=Array.from(b.rows);sortDir[c]*=-1;rows.sort((a,b_)=>{let x=a.cells[c].textContent.trim(),y=b_.cells[c].textContent.trim();const xn=parseFloat(x),yn=parseFloat(y);if(!isNaN(xn)&&!isNaN(yn))return(xn-yn)*sortDir[c];return x.localeCompare(y)*sortDir[c]});rows.forEach(r=>b.appendChild(r))}
function applyFilters(){const q=document.getElementById('search').value.toLowerCase(),s=document.getElementById('statusFilter').value,bn=document.getElementById('bottleneckFilter').value;const rows=document.querySelectorAll('#healthTable tbody tr');rows.forEach(row=>{const txt=row.textContent.toLowerCase(),st=row.cells[2]?.textContent.trim()||'',bt=row.cells[7]?.textContent.trim()||'';let show=true;if(q&&!txt.includes(q))show=false;if(s&&st!==s)show=false;if(bn&&bt!==bn)show=false;row.style.display=show?'':'none'})}
function exportCSV(){const t=document.getElementById('healthTable'),rows=Array.from(t.rows).filter(r=>r.style.display!=='none');let csv=rows.map(r=>Array.from(r.cells).map(c=>'"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='application_health.csv';a.click()}
</script>
</body>
</html>
```

**MANDATORY STEPS:**
1. Copy this template exactly
2. Replace the `{{...}}` placeholders in the summary cards with real values
3. Add one `<tr>` row inside `<tbody>` for every application
4. Set the row class to `good`, `okay`, or `poor` based on score
5. Write the file to disk and provide the file path to the user

**Both files must be saved to the user's working directory** and the file paths provided in the response.

---

## Workflow

### Step 1: List All Monitored Applications

Retrieve the full list of applications monitored by ZDX.

```
zdx_list_applications()
```

Optionally filter by location, department, or geolocation:

```
zdx_list_applications(
  location_id=["<location_id>"],
  department_id=["<department_id>"],
  since=4
)
```

**Categorize results by score:**
- **Good (66-100):** Healthy, no action needed
- **Okay (34-65):** Degraded, investigate further
- **Poor (0-33):** Critical, immediate attention

---

### Step 2: Investigate Degraded Applications

For each application with a degraded or poor score, get the score trend to understand if this is a new or ongoing issue.

```
zdx_get_application_score_trend(
  app_id="<app_id>",
  since=24
)
```

**Interpret the trend:**
- **Sudden drop:** Likely an incident (server, network, or ISP issue)
- **Gradual decline:** Resource exhaustion, growing user base, or config drift
- **Intermittent spikes:** Unstable network path or periodic load spikes

Get application details for additional context:

```
zdx_get_application(app_id="<app_id>")
```

---

### Step 3: Drill Into Metrics

For each degraded application, check individual metrics to isolate the bottleneck.

**Page Fetch Time (overall web performance):**
```
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="pft"
)
```

**DNS Resolution Time:**
```
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="dns"
)
```

**Availability:**
```
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="availability"
)
```

**Metric interpretation guide:**

| Metric | What It Measures | Healthy | Degraded | Critical |
|---|---|---|---|---|
| `pft` | Page Fetch Time (full load) | < 3s | 3-8s | > 8s |
| `dns` | DNS resolution | < 50ms | 50-200ms | > 200ms |
| `availability` | App reachability | 99-100% | 95-99% | < 95% |

**Bottleneck mapping:**
- High `pft` + normal `dns` + high `availability` → Server or CDN slow
- High `pft` + high `dns` + high `availability` → DNS resolution issues
- Low `availability` → Application or network unreachable

---

### Step 4: Identify Impacted Users

For each degraded application, list the impacted users.

**Users with poor scores:**
```
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor"
)
```

**Users with okay scores (borderline):**
```
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="okay"
)
```

**Filter by location to scope the impact:**
```
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor",
  location_id=["<location_id>"]
)
```

**For a specific user, get detailed experience data:**
```
zdx_get_application_user(
  app_id="<app_id>",
  user_id="<user_id>"
)
```

---

### Step 5: Cross-Reference with Alerts

Check if any active alerts correlate with the degraded applications.

```
zdx_list_alerts(since=24)
```

For relevant alerts:
```
zdx_get_alert(alert_id="<alert_id>")
zdx_list_alert_affected_devices(alert_id="<alert_id>")
```

---

### Step 6: Present Application Health Report

Present all data in **HTML table format** with detailed analysis.

**Application Health Overview (HTML table):**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Application</th>
  <th style="padding:8px;border:1px solid #ddd">Score</th>
  <th style="padding:8px;border:1px solid #ddd">Status</th>
  <th style="padding:8px;border:1px solid #ddd">PFT</th>
  <th style="padding:8px;border:1px solid #ddd">DNS</th>
  <th style="padding:8px;border:1px solid #ddd">Availability</th>
  <th style="padding:8px;border:1px solid #ddd">Impacted Users</th>
  <th style="padding:8px;border:1px solid #ddd">Bottleneck</th>
</tr></thead>
<tbody>
  <tr style="background:#f8d7da"><td style="padding:8px;border:1px solid #ddd">Microsoft 365</td><td style="padding:8px;font-weight:bold;color:red">28</td><td style="padding:8px">POOR</td><td style="padding:8px">12.4s</td><td style="padding:8px">22ms</td><td style="padding:8px">94%</td><td style="padding:8px">47 poor, 23 okay</td><td style="padding:8px">Page Fetch Time</td></tr>
  <tr style="background:#fff3cd"><td style="padding:8px;border:1px solid #ddd">Salesforce</td><td style="padding:8px;font-weight:bold;color:orange">52</td><td style="padding:8px">OKAY</td><td style="padding:8px">4.2s</td><td style="padding:8px">180ms</td><td style="padding:8px">99%</td><td style="padding:8px">12 poor, 31 okay</td><td style="padding:8px">DNS Resolution</td></tr>
  <tr style="background:#d4edda"><td style="padding:8px;border:1px solid #ddd">Zoom</td><td style="padding:8px;font-weight:bold;color:green">92</td><td style="padding:8px">GOOD</td><td style="padding:8px">1.2s</td><td style="padding:8px">18ms</td><td style="padding:8px">100%</td><td style="padding:8px">0</td><td style="padding:8px">-</td></tr>
</tbody></table>
```

**After the table, ALWAYS provide:**

1. **Analysis:** Explain the overall health posture -- how many apps are healthy vs degraded, what the dominant issues are, and whether this is a localized or organization-wide pattern.

2. **Root Cause per Degraded App:** For each degraded/poor application, state the primary bottleneck metric and what it indicates (e.g., "Microsoft 365 PFT at 12.4s indicates server-side or CDN latency, not DNS or network").

3. **Next Steps / Resolution:**
   - **Critical apps (score 0-33):** Immediate investigation required. Check service health dashboards, ISP paths, and Zscaler cloud path. Engage application vendor if server-side.
   - **Degraded apps (score 34-65):** Monitor trend. If declining, investigate the bottleneck metric. If stable, may be a capacity or configuration issue.
   - **Healthy apps:** No action needed. Note any that are borderline (score 66-70) for proactive monitoring.
   - Prioritize by user impact count -- apps affecting the most users should be addressed first.

---

## Filtering Strategies

### By Location
Useful for investigating office-specific issues.

```
zdx_list_applications(location_id=["<location_id>"])
zdx_get_application_score_trend(app_id="<app_id>", location_id=["<location_id>"])
zdx_get_application_metric(app_id="<app_id>", metric_name="pft", location_id=["<location_id>"])
```

### By Department
Useful for understanding impact on specific business units.

```
zdx_list_applications(department_id=["<dept_id>"])
zdx_list_application_users(app_id="<app_id>", department_id=["<dept_id>"])
```

### By Geolocation
Useful for regional analysis.

```
zdx_list_applications(geo_id=["<geo_id>"])
```

### By Time Window
Adjust `since` (hours) for different investigation windows:
- `since=2` -- current issues (default)
- `since=4` -- recent trends
- `since=24` -- daily overview
- `since=168` -- weekly review

---

## Edge Cases

### No Degraded Applications

```
All 12 monitored applications are healthy (score > 66).

Top performers:
1. GitHub (94)
2. Zoom (92)
3. Box (91)

No action required. Consider reviewing alert thresholds
if you want earlier notification of potential issues.
```

### All Applications Degraded

If most applications show poor scores simultaneously:
- Likely a network-wide or ISP issue, not application-specific
- Check ZDX alerts for ISP or network incidents
- Compare across locations to see if it's localized or global

### Single User Reports Issue but Scores Are Good

If the application score is healthy org-wide but one user reports issues:
- Use `zdx_get_application_user(app_id, user_id)` for user-specific data
- Switch to the **Troubleshoot User Experience** skill for individual investigation

---

## Quick Reference

**Primary workflow:** List Apps → Identify Degraded → Check Trends → Drill Into Metrics → List Impacted Users → Cross-Reference Alerts → Report

**Tools used:**
- `zdx_list_applications()` -- list all monitored apps with scores
- `zdx_get_application(app_id)` -- application details
- `zdx_get_application_score_trend(app_id)` -- score over time
- `zdx_get_application_metric(app_id, metric_name)` -- pft, dns, availability
- `zdx_list_application_users(app_id, score_bucket)` -- impacted users
- `zdx_get_application_user(app_id, user_id)` -- per-user detail
- `zdx_list_alerts(since)` -- correlated alerts
- `zdx_get_alert(alert_id)` -- alert details
- `zdx_list_alert_affected_devices(alert_id)` -- alert scope

**Score buckets:**
- `good`: 66-100
- `okay`: 34-65
- `poor`: 0-33

**Metric names:** `pft`, `dns`, `availability`

**Related skills:**
- [Troubleshoot User Experience](../troubleshoot-user-experience/) -- for individual user investigation
- [Investigate Alerts](../investigate-alerts/) -- for alert-focused investigation
- [Compare Location Experience](../compare-location-experience/) -- for cross-location analysis
