---
name: zdx-investigate-alerts
description: "Investigate active and historical ZDX alerts to understand their scope, root cause, and impact. Drills into affected devices, correlates with application metrics, and identifies patterns across time. Aligned with ZDX Copilot troubleshooting use cases. Use when an administrator asks: 'Show me ongoing alerts', 'What incidents happened in the last 48 hours?', 'How many users are affected by this alert?', or 'Is there an ISP issue?'"
---

# ZDX: Investigate Alerts

## Keywords
alerts, incidents, zdx alerts, active alerts, historical alerts, affected devices, alert investigation, ongoing alert, ISP issue, blackout, degradation, alert scope, impacted users, alert history

## Overview

Investigate active and historical ZDX alerts to determine their scope, affected users, root cause, and whether they represent isolated incidents or broader patterns. This skill provides a systematic approach to alert triage and investigation.

**Use this skill when:** An administrator wants to review current or past alerts, understand alert impact, investigate ISP or network incidents, or determine if a reported issue correlates with a known alert.

**ZDX Copilot alignment:** This skill covers the Troubleshooting category -- "Show me the number of ongoing alerts", "Show me the Incidents in the last 48 hours", "What can I do when I see a blackout incident with an ISP?"

---

## Data Presentation Requirements

**ALWAYS present ZDX data using HTML tables** for clear, structured output. Use `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling for readability.

After each table, provide:
1. **Detailed analysis** explaining the alert severity, scope, and correlation between alerts
2. **Root cause identification** based on metric correlation and affected scope
3. **Next steps / resolution** with specific remediation actions, escalation paths, and monitoring recommendations

Use color-coded rows by alert priority:
- Red: High priority alerts (many affected devices, critical applications, long duration)
- Yellow: Medium priority alerts (moderate impact, localized scope)
- Green: Low priority or resolved alerts

## Output Artifacts — MANDATORY

**You MUST generate BOTH files below. Do NOT skip the HTML page. Do NOT consider this optional. Both files are REQUIRED output for every alert investigation.**

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `alert_investigation_report_<date>.docx` containing:
- Executive summary with active alert count, severity breakdown, and scope
- Active alerts table (priority, alert name, application, duration, affected devices, locations, bottleneck)
- Metric correlation per alert (PFT, DNS, availability, root cause indicator)
- Historical pattern analysis (recurring alerts, frequency, time patterns)
- Per-alert root cause analysis with supporting evidence
- Prioritized remediation actions and escalation paths

### 2. Interactive HTML Web Page (.html) — REQUIRED

Write a **fully functional, self-contained HTML file** to disk named `alert_investigation_report_<date>.html`. This file MUST contain working CSS and JavaScript — not placeholders or comments. Copy the template below and populate `<tbody>` with one `<tr>` per alert. Replace `{{TOTAL_ALERTS}}`, `{{HIGH_COUNT}}`, `{{MEDIUM_COUNT}}`, `{{LOW_COUNT}}`, `{{MOST_AFFECTED}}`, and `{{IMPACTED_DEVICES}}` with actual values.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Alert Investigation Report</title>
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
tr.high{background:#f8d7da}
tr.medium{background:#fff3cd}
tr.low{background:#d4edda}
tr:hover{filter:brightness(.97)}
.priority-high{color:#e74c3c;font-weight:700}
.priority-medium{color:#e67e22;font-weight:700}
.priority-low{color:#636e72;font-weight:700}
@media(max-width:800px){.summary{flex-direction:column;align-items:center}table{font-size:.85em}}
</style>
</head>
<body>
<h1>Alert Investigation Report</h1>
<div class="summary">
  <div class="card"><div class="num">{{TOTAL_ALERTS}}</div><div class="label">Total Alerts</div></div>
  <div class="card"><div class="num" style="color:#e74c3c">{{HIGH_COUNT}}</div><div class="label">High</div></div>
  <div class="card"><div class="num" style="color:#e67e22">{{MEDIUM_COUNT}}</div><div class="label">Medium</div></div>
  <div class="card"><div class="num" style="color:#27ae60">{{LOW_COUNT}}</div><div class="label">Low</div></div>
  <div class="card"><div class="num">{{MOST_AFFECTED}}</div><div class="label">Most Affected App</div></div>
  <div class="card"><div class="num">{{IMPACTED_DEVICES}}</div><div class="label">Impacted Devices</div></div>
</div>
<div class="filters">
  <input type="text" id="search" placeholder="Search alert, application, location..." oninput="applyFilters()">
  <select id="priorityFilter" onchange="applyFilters()"><option value="">All Priority</option><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select>
  <select id="statusFilter" onchange="applyFilters()"><option value="">All Status</option><option value="Active">Active</option><option value="Resolved">Resolved</option></select>
  <button onclick="exportCSV()">Export CSV</button>
</div>
<table id="alertTable">
<thead><tr>
  <th onclick="sortTable(0)">Priority &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(1)">Alert Name &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(2)">Application &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(3)">Duration &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(4)">Affected Devices &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(5)">Locations &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(6)">Bottleneck &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(7)">Status &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="high|medium|low"> per alert.
     Example row:
  <tr class="high">
    <td class="priority-high">HIGH</td><td>M365 - High Page Fetch Time</td><td>Microsoft 365</td>
    <td>6 hours</td><td>47</td><td>New York, London</td><td>PFT: 12.4s</td><td>Active</td>
  </tr>
-->
</tbody>
</table>
<script>
let sortDir=[1,1,1,1,1,1,1,1];
function sortTable(c){const t=document.getElementById('alertTable'),b=t.tBodies[0],rows=Array.from(b.rows);sortDir[c]*=-1;rows.sort((a,b_)=>{let x=a.cells[c].textContent.trim(),y=b_.cells[c].textContent.trim();const xn=parseFloat(x),yn=parseFloat(y);if(!isNaN(xn)&&!isNaN(yn))return(xn-yn)*sortDir[c];return x.localeCompare(y)*sortDir[c]});rows.forEach(r=>b.appendChild(r))}
function applyFilters(){const q=document.getElementById('search').value.toLowerCase(),p=document.getElementById('priorityFilter').value,s=document.getElementById('statusFilter').value;const rows=document.querySelectorAll('#alertTable tbody tr');rows.forEach(row=>{const txt=row.textContent.toLowerCase(),pr=row.cells[0]?.textContent.trim()||'',st=row.cells[7]?.textContent.trim()||'';let show=true;if(q&&!txt.includes(q))show=false;if(p&&!pr.toUpperCase().includes(p.toUpperCase()))show=false;if(s&&st!==s)show=false;row.style.display=show?'':'none'})}
function exportCSV(){const t=document.getElementById('alertTable'),rows=Array.from(t.rows).filter(r=>r.style.display!=='none');let csv=rows.map(r=>Array.from(r.cells).map(c=>'"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='alert_investigation.csv';a.click()}
</script>
</body>
</html>
```

**MANDATORY STEPS:**
1. Copy this template exactly
2. Replace the `{{...}}` placeholders in the summary cards with real values
3. Add one `<tr>` row inside `<tbody>` for every alert
4. Set the row class to `high`, `medium`, or `low` based on priority
5. Write the file to disk and provide the file path to the user

**Both files must be saved to the user's working directory** and the file paths provided in the response.

---

## Workflow

### Step 1: List Active Alerts

Retrieve all currently active alerts.

```
zdx_list_alerts()
```

For a broader time window (e.g., last 48 hours):
```
zdx_list_alerts(since=48)
```

Filter by location or department for scoped investigation:
```
zdx_list_alerts(
  location_id=["<location_id>"],
  since=24
)
```

```
zdx_list_alerts(
  department_id=["<department_id>"],
  since=24
)
```

**Triage by severity and scope:**
- How many alerts are active?
- Which applications are affected?
- How long have they been active?
- Are multiple alerts pointing to the same root cause?

---

### Step 2: Get Alert Details

For each alert that warrants investigation:

```
zdx_get_alert(alert_id="<alert_id>")
```

**Key information to extract:**
- Alert type (performance degradation, availability, etc.)
- Triggered application and threshold
- Impacted departments and locations
- Geolocation data
- Alert trigger conditions
- Start time and duration

---

### Step 3: Determine Impact Scope

List all devices affected by the alert:

```
zdx_list_alert_affected_devices(alert_id="<alert_id>")
```

Filter by location to understand geographic scope:
```
zdx_list_alert_affected_devices(
  alert_id="<alert_id>",
  location_id=["<location_id>"]
)
```

Filter by department for business impact:
```
zdx_list_alert_affected_devices(
  alert_id="<alert_id>",
  department_id=["<department_id>"]
)
```

**Scope determination:**
- **Single user:** Likely a device or local network issue
- **Single location:** Office-specific issue (local ISP, WiFi, LAN)
- **Multiple locations, same geo:** Regional ISP or cloud region issue
- **Global:** Application server issue or major ISP backbone problem

---

### Step 4: Correlate with Application Metrics

Cross-reference the alert with application performance data to confirm the bottleneck.

```
zdx_get_application_score_trend(
  app_id="<affected_app_id>",
  since=24
)
```

```
zdx_get_application_metric(
  app_id="<affected_app_id>",
  metric_name="pft"
)
```

```
zdx_get_application_metric(
  app_id="<affected_app_id>",
  metric_name="dns"
)
```

```
zdx_get_application_metric(
  app_id="<affected_app_id>",
  metric_name="availability"
)
```

**Correlation mapping:**
- Alert + high PFT + normal DNS → Application or CDN issue
- Alert + high DNS → DNS infrastructure problem
- Alert + low availability → Network or application unreachable
- Alert + all metrics degraded → Major infrastructure event

---

### Step 5: Check Historical Patterns

Look for recurring patterns in past alerts.

```
zdx_list_historical_alerts(since=336)
```

Filter by location or department:
```
zdx_list_historical_alerts(
  location_id=["<location_id>"],
  since=168
)
```

**Pattern analysis:**
- Same alert recurring daily at specific times? → Scheduled load or maintenance window
- Same alert recurring weekly? → Periodic resource constraints
- Same location repeatedly affected? → Infrastructure issue at that site
- Same application repeatedly affected? → Application stability concerns

---

### Step 6: Deep Trace for Network Path Analysis

If the alert suggests a network issue, check if deep traces exist for affected devices.

```
zdx_list_devices(location_id=["<affected_location_id>"])
```

For a specific affected device:
```
zdx_list_device_deep_traces(device_id="<device_id>")
```

```
zdx_get_device_deep_trace(
  device_id="<device_id>",
  trace_id="<trace_id>"
)
```

Deep traces reveal hop-by-hop latency and packet loss, pinpointing the exact network segment causing the issue (local network, ISP, cloud provider, or application server).

---

### Step 7: Present Alert Investigation Report

Present all data in **HTML table format** with detailed analysis.

**Active Alerts Summary (HTML table):**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Priority</th>
  <th style="padding:8px;border:1px solid #ddd">Alert Name</th>
  <th style="padding:8px;border:1px solid #ddd">Application</th>
  <th style="padding:8px;border:1px solid #ddd">Duration</th>
  <th style="padding:8px;border:1px solid #ddd">Affected Devices</th>
  <th style="padding:8px;border:1px solid #ddd">Locations</th>
  <th style="padding:8px;border:1px solid #ddd">Bottleneck</th>
</tr></thead>
<tbody>
  <tr style="background:#f8d7da"><td style="padding:8px;font-weight:bold;color:red">HIGH</td><td style="padding:8px">M365 - High Page Fetch Time</td><td style="padding:8px">Microsoft 365</td><td style="padding:8px">6 hours</td><td style="padding:8px">47</td><td style="padding:8px">New York, London, Singapore</td><td style="padding:8px">PFT: 12.4s</td></tr>
  <tr style="background:#fff3cd"><td style="padding:8px;font-weight:bold;color:orange">MEDIUM</td><td style="padding:8px">Salesforce - DNS Degraded</td><td style="padding:8px">Salesforce</td><td style="padding:8px">2 hours</td><td style="padding:8px">12</td><td style="padding:8px">Dallas</td><td style="padding:8px">DNS: 180ms</td></tr>
  <tr style="background:#d4edda"><td style="padding:8px;font-weight:bold;color:gray">LOW</td><td style="padding:8px">Internal CRM - Availability Drop</td><td style="padding:8px">Internal CRM</td><td style="padding:8px">30 min</td><td style="padding:8px">3</td><td style="padding:8px">San Jose</td><td style="padding:8px">Availability: 92%</td></tr>
</tbody></table>
```

**Metric Correlation per Alert (HTML table):**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Alert</th>
  <th style="padding:8px;border:1px solid #ddd">PFT</th>
  <th style="padding:8px;border:1px solid #ddd">DNS</th>
  <th style="padding:8px;border:1px solid #ddd">Availability</th>
  <th style="padding:8px;border:1px solid #ddd">Root Cause Indicator</th>
</tr></thead>
<tbody>
  <tr><td style="padding:8px;border:1px solid #ddd">M365 - High PFT</td><td style="padding:8px;color:red;font-weight:bold">12.4s</td><td style="padding:8px;color:green">25ms</td><td style="padding:8px;color:orange">94%</td><td style="padding:8px">Server-side / CDN latency</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">Salesforce - DNS</td><td style="padding:8px;color:orange">4.2s</td><td style="padding:8px;color:red;font-weight:bold">180ms</td><td style="padding:8px;color:green">99%</td><td style="padding:8px">Local DNS resolver (Dallas)</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">CRM - Availability</td><td style="padding:8px;color:orange">Variable</td><td style="padding:8px;color:green">15ms</td><td style="padding:8px;color:red;font-weight:bold">92%</td><td style="padding:8px">Application server instability</td></tr>
</tbody></table>
```

**After the tables, ALWAYS provide:**

1. **Analysis:** "Three active alerts are impacting the organization. The M365 alert is the highest priority -- 47 devices across 3 locations with PFT at 12.4s indicates a server-side issue, not a local network problem. The Salesforce DNS issue is isolated to Dallas, suggesting a local DNS resolver problem. The CRM alert is new and low impact -- likely transient."

2. **Historical Pattern Analysis:** "The M365 High PFT alert has triggered 3 times this week (Mon 8am, Wed 2pm, Today 10am), suggesting a recurring issue possibly correlated with peak usage hours. No prior Salesforce DNS alerts exist -- this is a new issue. The CRM had one similar alert 5 days ago that resolved in 45 minutes."

3. **Next Steps / Resolution:**
   - **M365 (HIGH):** Check Microsoft 365 service health dashboard immediately. If service is healthy, investigate Zscaler cloud path to Microsoft endpoints. The recurring pattern suggests a capacity issue during peak hours -- consider engaging Microsoft support with ZDX evidence.
   - **Salesforce DNS (MEDIUM):** Investigate DNS server configuration in Dallas office. Compare with healthy locations. Consider switching to redundant DNS or Zscaler DNS proxy.
   - **CRM Availability (LOW):** Monitor for 1 hour. If it persists, check application server health and recent deployments. Check for scheduled maintenance windows.
   - **Proactive:** Set up recurring deep traces for the M365 issue to capture network path data during the next peak-hour occurrence.

---

## Common Investigation Scenarios

### ISP-Related Issues

When an alert suggests ISP problems:

1. Check affected locations -- if all are in the same region, likely a regional ISP
2. Use deep traces to identify the specific ISP hop with high latency/loss
3. Compile the evidence (deep trace data, affected users, time range) for the ISP

```
ISP Issue Detected:
  ISP: <ISP_Name>
  Hop: <hop_number> (<ip_address>)
  Latency: <current>ms (normal: <baseline>ms)
  Packet Loss: <loss>%
  Affected Users: <count> in <location>
  Duration: <hours>

  Recommended Action:
  1. Contact ISP with compiled cloud path evidence
  2. Consider rerouting traffic through alternate ISP if available
  3. Set up a recurring deep trace to monitor resolution
```

### WiFi Quality Issues

When alerts suggest WiFi instability:

1. List affected devices and check their device health
2. Look for common WiFi channel, SSID, or access point
3. Recommend channel optimization or access point adjustments

### Application Server Issues

When metrics point to the application itself:

1. Confirm with availability and PFT metrics
2. Check if the issue is across all locations (global) or specific regions
3. Cross-reference with application provider's status page

---

## Edge Cases

### No Active Alerts

```
No active alerts in the requested time window.

All monitored applications are within normal thresholds.

Consider:
- Checking historical alerts for recent resolved issues
- Reviewing alert configuration to ensure thresholds are appropriate
- Using the Analyze Application Health skill for a proactive review
```

### Too Many Alerts (Alert Fatigue)

If there are many active alerts:
1. Group by application -- multiple alerts for the same app may be one root cause
2. Group by location -- many alerts in one location suggest a local issue
3. Prioritize by affected device count -- highest impact first

### Alert Without Visible User Impact

Some alerts may fire based on threshold violations that users haven't noticed:
- Check actual user scores with `zdx_list_application_users`
- If scores are still "good", the threshold may be too sensitive
- Document for alert tuning

---

## Quick Reference

**Primary workflow:** List Alerts → Get Details → Determine Scope → Correlate Metrics → Check History → Deep Trace → Report

**Tools used:**
- `zdx_list_alerts(since)` -- list active alerts
- `zdx_get_alert(alert_id)` -- alert details
- `zdx_list_alert_affected_devices(alert_id)` -- impacted devices
- `zdx_list_historical_alerts(since)` -- past alerts for patterns
- `zdx_get_application_score_trend(app_id)` -- correlate with scores
- `zdx_get_application_metric(app_id, metric_name)` -- pinpoint metric
- `zdx_list_device_deep_traces(device_id)` -- network path data
- `zdx_get_device_deep_trace(device_id, trace_id)` -- hop-by-hop analysis

**Time windows for `since` (hours):**
- `2` -- current issues (default)
- `24` -- last day
- `48` -- last 2 days
- `168` -- last week
- `336` -- last 2 weeks (max)

**Related skills:**
- [Troubleshoot User Experience](../troubleshoot-user-experience/) -- for individual user investigation
- [Analyze Application Health](../analyze-application-health/) -- for app-level overview
- [Compare Location Experience](../compare-location-experience/) -- for location-based analysis
