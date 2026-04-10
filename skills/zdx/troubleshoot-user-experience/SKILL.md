---
name: zdx-troubleshoot-user-experience
description: "Troubleshoot a user's digital experience using ZDX data. Investigates device health, application scores, network path metrics, and active alerts to identify performance bottlenecks. Use when an administrator reports: 'User says app is slow', 'Check user experience', or 'Why is the application score low?'"
---

# ZDX: Troubleshoot User Experience

## Keywords

user experience, slow application, zdx score, digital experience, performance issue, latency, application slow, user complaint, experience score, network path, zdx troubleshoot, deep trace

## Overview

Investigate a user's digital experience using Zscaler Digital Experience (ZDX) metrics. This skill retrieves device information, application experience scores, network path data, and active alerts to pinpoint whether the issue is on the client device, the network, or the application server.

**Use this skill when:** An administrator receives user complaints about application performance, needs to investigate low ZDX scores, or wants to proactively check a user's digital experience.

---

## Data Presentation Requirements

**ALWAYS present ZDX data using HTML tables** for clear, structured output. Use `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling for readability.

After each table, provide:

1. **Detailed analysis** explaining what the data means in plain language
2. **Root cause identification** based on the metrics and patterns
3. **Next steps / resolution** with specific, actionable recommendations prioritized by impact

Use color-coded status indicators in tables:

- Green/Good: scores 66-100, metrics within normal range
- Yellow/Degraded: scores 34-65, metrics approaching thresholds
- Red/Poor: scores 0-33, metrics exceeding thresholds

## Output Artifacts — MANDATORY

**You MUST generate BOTH files below. Do NOT skip the HTML page. Do NOT consider this optional. Both files are REQUIRED output for every user experience diagnosis.**

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `user_experience_diagnosis_<date>.docx` containing:

- User and device summary (name, email, device type, OS, location, department)
- Application experience scores with trend analysis
- Metric breakdown (DNS, TCP connect, SSL handshake, server response, page load)
- Root cause analysis with supporting evidence
- Alert correlation (if any active alerts match the issue)
- Recommended resolution steps prioritized by impact

### 2. Interactive HTML Web Page (.html) — REQUIRED

Write a **fully functional, self-contained HTML file** to disk named `user_experience_diagnosis_<date>.html`. This file MUST contain working CSS and JavaScript — not placeholders or comments. Copy the template below and populate `<tbody>` with one `<tr>` per metric. Replace `{{USER}}`, `{{DEVICE}}`, `{{SCORE}}`, `{{BOTTLENECK}}`, and `{{ALERTS}}` with actual values.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>User Experience Diagnosis</title>
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
tr.ok{background:#d4edda}
tr.degraded{background:#fff3cd}
tr.critical{background:#f8d7da}
tr:hover{filter:brightness(.97)}
.status-ok{color:#27ae60;font-weight:700}
.status-degraded{color:#e67e22;font-weight:700}
.status-critical{color:#e74c3c;font-weight:700}
@media(max-width:800px){.summary{flex-direction:column;align-items:center}table{font-size:.85em}}
</style>
</head>
<body>
<h1>User Experience Diagnosis Report</h1>
<div class="summary">
  <div class="card"><div class="num">{{USER}}</div><div class="label">User</div></div>
  <div class="card"><div class="num">{{DEVICE}}</div><div class="label">Device</div></div>
  <div class="card"><div class="num" id="score">{{SCORE}}</div><div class="label">Experience Score</div></div>
  <div class="card"><div class="num" style="color:#e74c3c">{{BOTTLENECK}}</div><div class="label">Bottleneck</div></div>
  <div class="card"><div class="num">{{ALERTS}}</div><div class="label">Active Alerts</div></div>
</div>
<div class="filters">
  <input type="text" id="search" placeholder="Search metrics, values..." oninput="applyFilters()">
  <select id="statusFilter" onchange="applyFilters()"><option value="">All Status</option><option value="OK">OK</option><option value="Degraded">Degraded</option><option value="Critical">Critical</option></select>
  <select id="categoryFilter" onchange="applyFilters()"><option value="">All Categories</option><option value="DNS">DNS</option><option value="Network">Network</option><option value="Server">Server</option><option value="Client">Client</option></select>
  <button onclick="exportCSV()">Export CSV</button>
</div>
<table id="metricsTable">
<thead><tr>
  <th onclick="sortTable(0)">Metric &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(1)">Current Value &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(2)">Normal Range &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(3)">Category &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(4)">Status &#x25B4;&#x25BE;</th>
  <th onclick="sortTable(5)">Impact &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="ok|degraded|critical"> per metric.
     Example row:
  <tr class="critical">
    <td>Server Response Time</td><td>Timeout</td><td>&lt; 500ms</td><td>Server</td>
    <td class="status-critical">Critical</td><td>Application unreachable</td>
  </tr>
-->
</tbody>
</table>
<script>
let sortDir=[1,1,1,1,1,1];
function sortTable(c){const t=document.getElementById('metricsTable'),b=t.tBodies[0],rows=Array.from(b.rows);sortDir[c]*=-1;rows.sort((a,b_)=>{let x=a.cells[c].textContent.trim(),y=b_.cells[c].textContent.trim();const xn=parseFloat(x),yn=parseFloat(y);if(!isNaN(xn)&&!isNaN(yn))return(xn-yn)*sortDir[c];return x.localeCompare(y)*sortDir[c]});rows.forEach(r=>b.appendChild(r))}
function applyFilters(){const q=document.getElementById('search').value.toLowerCase(),s=document.getElementById('statusFilter').value,cat=document.getElementById('categoryFilter').value;const rows=document.querySelectorAll('#metricsTable tbody tr');rows.forEach(row=>{const txt=row.textContent.toLowerCase(),st=row.cells[4]?.textContent.trim()||'',ct=row.cells[3]?.textContent.trim()||'';let show=true;if(q&&!txt.includes(q))show=false;if(s&&st!==s)show=false;if(cat&&ct!==cat)show=false;row.style.display=show?'':'none'})}
function exportCSV(){const t=document.getElementById('metricsTable'),rows=Array.from(t.rows).filter(r=>r.style.display!=='none');let csv=rows.map(r=>Array.from(r.cells).map(c=>'"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='user_experience_diagnosis.csv';a.click()}
</script>
</body>
</html>
```text

**MANDATORY STEPS:**

1. Copy this template exactly
2. Replace the `{{...}}` placeholders in the summary cards with real values
3. Add one `<tr>` row inside `<tbody>` for every metric collected
4. Set the row class to `ok`, `degraded`, or `critical` based on status
5. Write the file to disk and provide the file path to the user

**Both files must be saved to the user's working directory** and the file paths provided in the response.

---

## Workflow

Follow this 5-step process to troubleshoot user experience.

### Step 1: Find the User's Device

```text
zdx_list_devices(search="<username_or_email>")
```text

Note the device ID, OS, ZDX agent version, and last active timestamp. If multiple devices, confirm which one the user is working on.

```text
zdx_get_device(device_id="<device_id>")
```text

Check device-level health:

- CPU utilization
- Memory usage
- Disk usage
- Network adapter status
- ZCC tunnel status

---

### Step 2: Check Application Experience Scores

**List monitored applications:**

```text
zdx_list_applications()
```text

**Get the score trend for the affected application:**

```text
zdx_get_application_score_trend(app_id="<app_id>")
```text

**Interpret scores:**

- **80-100:** Good experience -- issue may be intermittent or resolved
- **50-79:** Degraded -- one or more metrics are outside normal range
- **0-49:** Poor -- significant performance degradation

**Get application details:**

```text
zdx_get_application(app_id="<app_id>")
```text

---

### Step 3: Analyze Detailed Metrics

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="dns_time"
)
```text

Check each metric individually to isolate the bottleneck:

| Metric | Normal Range | Indicates |
|--------|-------------|-----------|
| `dns_time` | < 50ms | DNS resolution performance |
| `tcp_connect_time` | < 100ms | Network reachability |
| `ssl_handshake_time` | < 150ms | SSL/TLS negotiation |
| `server_response_time` | < 500ms | Application server health |
| `page_load_time` | < 3000ms | Full page rendering |

**Identify the bottleneck:**

- High DNS time → DNS server issue or resolution failure
- High TCP connect → Network congestion or routing issue
- High SSL handshake → Certificate issues or server overload
- High server response → Application server performance issue
- High page load → Client-side rendering or large page size

---

### Step 4: Check Alerts and Affected Users

**Check active alerts:**

```text
zdx_list_alerts()
```text

If an alert exists for the application:

```text
zdx_get_alert(alert_id="<alert_id>")
zdx_list_alert_affected_devices(alert_id="<alert_id>")
```text

This determines if the issue is isolated to one user or widespread.

**Check historical alerts for patterns:**

```text
zdx_list_historical_alerts()
```text

---

### Step 5: Deep Trace Diagnostics (if available or needed)

Check for existing deep trace sessions:

```text
zdx_list_device_deep_traces(device_id="<device_id>")
```text

If a trace exists, analyze all diagnostics data:

```text
zdx_get_device_deep_trace(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_webprobe_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_health_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_list_deeptrace_top_processes(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_events(device_id="<device_id>", trace_id="<trace_id>")
```text

**Deep trace analysis checklist:**

- **Web probe metrics**: DNS, TCP, SSL, HTTP response times — identify connectivity bottleneck layer
- **Cloud path topology**: Hop-by-hop path — identify hops with high latency or packet loss
- **Cloud path metrics**: Per-hop latency, packet loss, jitter trends over the trace duration
- **Health metrics**: CPU, memory, disk, network — detect device-side resource constraints
- **Top processes**: Resource-heavy processes competing for CPU/memory during the trace
- **Events**: Zscaler policy changes, hardware/software updates, network changes correlated with issue onset

If NO trace exists and metrics suggest network issues, discover probe IDs then start a new diagnostics session (requires write tools):

```text
zdx_get_web_probes(device_id="<device_id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<device_id>", app_id="<app_id>")
zdx_start_deeptrace(device_id="<device_id>", session_name="Troubleshoot-<user>-<date>", app_id=<app_id>, web_probe_id=<id>, cloudpath_probe_id=<id>, session_length_minutes=15, probe_device=True)
```text

For comprehensive deep trace analysis, see the [Diagnose Deep Trace](../diagnose-deeptrace/) skill.

---

### Present Diagnosis

Present all data in **HTML table format** with detailed analysis.

**Device & User Summary:**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Field</th>
  <th style="padding:8px;border:1px solid #ddd">Value</th>
</tr></thead>
<tbody>
  <tr><td style="padding:8px;border:1px solid #ddd">User</td><td style="padding:8px;border:1px solid #ddd">&lt;name&gt; (&lt;email&gt;)</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">Device</td><td style="padding:8px;border:1px solid #ddd">&lt;device_type&gt;, &lt;os_version&gt;</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">Location</td><td style="padding:8px;border:1px solid #ddd">&lt;location&gt;</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">Department</td><td style="padding:8px;border:1px solid #ddd">&lt;department&gt;</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">ZCC Version</td><td style="padding:8px;border:1px solid #ddd">&lt;version&gt;</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">Experience Score</td><td style="padding:8px;border:1px solid #ddd;font-weight:bold;color:red">&lt;score&gt;/100 (Poor)</td></tr>
</tbody></table>
```text

**Metric Breakdown (HTML table):**

```html
<table style="border-collapse:collapse;width:100%">
<thead><tr style="background:#1a1a2e;color:#fff">
  <th style="padding:8px;border:1px solid #ddd">Metric</th>
  <th style="padding:8px;border:1px solid #ddd">Current</th>
  <th style="padding:8px;border:1px solid #ddd">Normal Range</th>
  <th style="padding:8px;border:1px solid #ddd">Status</th>
</tr></thead>
<tbody>
  <tr><td style="padding:8px;border:1px solid #ddd">DNS Resolution</td><td style="padding:8px">15ms</td><td style="padding:8px">&lt; 50ms</td><td style="padding:8px;color:green;font-weight:bold">OK</td></tr>
  <tr style="background:#fff3cd"><td style="padding:8px;border:1px solid #ddd">TCP Connect</td><td style="padding:8px">850ms</td><td style="padding:8px">&lt; 100ms</td><td style="padding:8px;color:orange;font-weight:bold">DEGRADED</td></tr>
  <tr style="background:#fff3cd"><td style="padding:8px;border:1px solid #ddd">SSL Handshake</td><td style="padding:8px">1200ms</td><td style="padding:8px">&lt; 150ms</td><td style="padding:8px;color:orange;font-weight:bold">DEGRADED</td></tr>
  <tr style="background:#f8d7da"><td style="padding:8px;border:1px solid #ddd">Server Response</td><td style="padding:8px">Timeout</td><td style="padding:8px">&lt; 500ms</td><td style="padding:8px;color:red;font-weight:bold">CRITICAL</td></tr>
  <tr style="background:#f8d7da"><td style="padding:8px;border:1px solid #ddd">Page Load</td><td style="padding:8px">N/A</td><td style="padding:8px">&lt; 3000ms</td><td style="padding:8px;color:red;font-weight:bold">FAILED</td></tr>
</tbody></table>
```text

**After the tables, ALWAYS provide:**

1. **Analysis:** "Server response time has degraded from normal (180ms) to timeout. TCP connect time is also elevated (850ms vs 65ms), indicating network path issues between the Zscaler cloud and the application server. 15 other devices are experiencing the same issue, confirming this is NOT client-specific."

2. **Root Cause:** Identify the primary bottleneck (e.g., "Server Response timeout with elevated TCP connect time points to network congestion or application server overload in the US-East region").

3. **Next Steps / Resolution:**
   - **Immediate:** Check application server health in the affected datacenter
   - **Investigate:** Run a deep trace to identify the exact hop causing latency
   - **Verify:** Check ISP or cloud provider status pages for known outages
   - **If ZPA:** Verify app connector health for the affected server group
   - **Escalate:** If server-side, engage the application team with the ZDX evidence

---

## Edge Cases

### No ZDX Data for User

```text
No ZDX data found for user "<username>".

Possible causes:
- ZDX is not monitoring this user's device
- The user's ZCC agent does not have ZDX enabled
- The user just enrolled and data hasn't been collected yet

Action: Verify ZDX is enabled in the user's ZCC profile.
```text

### Application Not Monitored

```text
The application "<app_name>" is not configured for ZDX monitoring.

Available monitored applications:
1. Office 365 (Score: 88)
2. Salesforce (Score: 75)
3. Internal Portal (Score: 92)

To monitor this application, configure it in the ZDX Admin Portal.
```text

### Score Fluctuations (Intermittent Issues)

If the score trend shows spikes:

```text
Intermittent issue detected. Score fluctuates between 30-90 over
the past 6 hours, suggesting an unstable network path or
application with periodic performance degradation.

Recommendation: Initiate a deep trace to capture the issue during
the next degradation window.
```text

---

## Quick Reference

**Primary workflow:** Find Device → Check Scores → Analyze Metrics → Check Alerts → Deep Trace → Diagnosis

**Tools used:**

- `zdx_list_devices(search)` -- find user's device
- `zdx_get_device(device_id)` -- device health details
- `zdx_list_applications()` -- list monitored apps
- `zdx_get_application(app_id)` -- application details
- `zdx_get_application_score_trend(app_id)` -- experience score over time
- `zdx_get_application_metric(app_id, metric_name)` -- specific performance metrics
- `zdx_list_alerts()` -- active alerts
- `zdx_get_alert(alert_id)` -- alert details
- `zdx_list_alert_affected_devices(alert_id)` -- scope of impact
- `zdx_list_historical_alerts()` -- alert history
- `zdx_list_device_deep_traces(device_id)` -- available deep traces
- `zdx_get_device_deep_trace(device_id, trace_id)` -- trace summary
- `zdx_get_deeptrace_webprobe_metrics(device_id, trace_id)` -- DNS, TCP, SSL, HTTP times
- `zdx_get_deeptrace_cloudpath(device_id, trace_id)` -- hop-by-hop network path
- `zdx_get_deeptrace_cloudpath_metrics(device_id, trace_id)` -- per-hop latency, loss, jitter
- `zdx_get_deeptrace_health_metrics(device_id, trace_id)` -- CPU, memory, disk, network
- `zdx_list_deeptrace_top_processes(device_id, trace_id)` -- resource-heavy processes
- `zdx_get_deeptrace_events(device_id, trace_id)` -- event timeline
- `zdx_get_web_probes(device_id, app_id)` -- get web_probe_id for deep traces
- `zdx_list_cloudpath_probes(device_id, app_id)` -- get cloudpath_probe_id for deep traces
- `zdx_start_deeptrace(device_id, ...)` -- start a new trace (write tool)

**Score interpretation:**

- 80-100: Good
- 50-79: Degraded
- 0-49: Poor
