---
name: zdx-diagnose-deeptrace
description: "Run a ZDX deep trace diagnostics session to investigate network and device issues. Start new sessions, analyze web probe metrics, cloud path topology, device health, top processes, and event timelines to pinpoint root cause. Use when an administrator asks: 'Start a deep trace for this user', 'Analyze the diagnostics session', 'Why is the network path slow?', 'Check cloud path for packet loss', or 'What happened during the trace?'"
---

# ZDX: Deep Trace Diagnostics

## Keywords
deep trace, diagnostics session, cloud path, web probe, network path, packet loss, latency, jitter, health metrics, top processes, events, troubleshoot network, hop analysis, DNS time, TCP connect, SSL handshake, device health, CPU, memory, diagnostics, deeptrace

## Overview

Perform deep trace diagnostics on a user's device to capture detailed network path data, web probe performance, device health metrics, and event timelines. Deep traces are the most powerful troubleshooting tool in ZDX — they provide granular, time-series data that standard application scores and metrics cannot.

**Use this skill when:** An administrator needs to investigate network connectivity issues, isolate packet loss or latency on specific network hops, analyze device-level performance during an incident, or start a new diagnostics session to capture evidence of an intermittent problem.

**ZDX Diagnostics alignment:** This skill covers the full diagnostics workflow — starting sessions (Deep Tracing), evaluating session information (In Progress / History), and analyzing session results (web probes, cloud paths, health, events).

---

## Data Presentation Requirements

**ALWAYS present ZDX data using HTML tables** for clear, structured output. Use `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling for readability.

After each table, provide:
1. **Detailed analysis** explaining what the metrics reveal about the user's connectivity
2. **Root cause identification** mapped to the specific layer (device, network, DNS, application, configuration)
3. **Next steps / resolution** with specific, actionable recommendations

Use color-coded status indicators:
- Green/Good: Metrics within normal range (latency < 50ms, packet loss 0%, healthy CPU/memory)
- Yellow/Degraded: Metrics approaching thresholds (latency 50-150ms, packet loss 1-5%, moderate resource usage)
- Red/Critical: Metrics exceeding thresholds (latency > 150ms, packet loss > 5%, resource exhaustion)

## Output Artifacts — MANDATORY

**You MUST generate BOTH files below. Do NOT skip the HTML page. Do NOT consider this optional. Both files are REQUIRED output for every deep trace diagnosis.**

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `deep_trace_diagnosis_<date>.docx` containing:
- Session summary (name, type, user, device, status, start/end time, duration)
- Web probe metrics breakdown (DNS, TCP, SSL, HTTP response times)
- Cloud path topology with per-hop latency, packet loss, and jitter analysis
- Device health assessment (CPU, memory, disk I/O, network utilization)
- Top processes consuming resources during the trace
- Event correlation timeline (Zscaler, hardware, software, network changes)
- Root cause analysis mapped to the affected layer
- Prioritized remediation actions

### 2. Interactive HTML Web Page (.html) — REQUIRED

Write a **fully functional, self-contained HTML file** to disk named `deep_trace_diagnosis_<date>.html`. This file MUST contain working CSS and JavaScript — not placeholders or comments. Copy the template below and populate `<tbody>` with data from the deep trace. Replace `{{USER}}`, `{{DEVICE}}`, `{{SESSION}}`, `{{STATUS}}`, `{{DURATION}}`, and `{{ROOT_CAUSE}}` with actual values.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Deep Trace Diagnosis</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f6fa;color:#2d3436;padding:20px}
h1{text-align:center;margin-bottom:20px;color:#1a1a2e}
h2{margin:24px 0 12px;color:#1a1a2e}
.summary{display:flex;gap:15px;justify-content:center;flex-wrap:wrap;margin-bottom:20px}
.card{background:#fff;border-radius:10px;padding:18px 28px;box-shadow:0 2px 8px rgba(0,0,0,.1);text-align:center;min-width:160px}
.card .num{font-size:2em;font-weight:700;color:#1a1a2e}
.card .label{font-size:.85em;color:#636e72;margin-top:4px}
.filters{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:18px}
.filters input,.filters select{padding:8px 14px;border:1px solid #ddd;border-radius:6px;font-size:.95em}
.filters input{min-width:260px}
.filters button{padding:8px 18px;background:#0984e3;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.95em}
.filters button:hover{background:#0767b2}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:24px}
th{background:#1a1a2e;color:#fff;padding:10px 12px;cursor:pointer;position:sticky;top:0;user-select:none;white-space:nowrap}
th:hover{background:#2d3460}
td{padding:9px 12px;border-bottom:1px solid #eee}
tr.good{background:#d4edda}
tr.degraded{background:#fff3cd}
tr.critical{background:#f8d7da}
tr:hover{filter:brightness(.97)}
.status-good{color:#27ae60;font-weight:700}
.status-degraded{color:#e67e22;font-weight:700}
.status-critical{color:#e74c3c;font-weight:700}
@media(max-width:800px){.summary{flex-direction:column;align-items:center}table{font-size:.85em}}
</style>
</head>
<body>
<h1>Deep Trace Diagnosis Report</h1>
<div class="summary">
  <div class="card"><div class="num">{{USER}}</div><div class="label">User</div></div>
  <div class="card"><div class="num">{{DEVICE}}</div><div class="label">Device</div></div>
  <div class="card"><div class="num">{{SESSION}}</div><div class="label">Session</div></div>
  <div class="card"><div class="num">{{STATUS}}</div><div class="label">Status</div></div>
  <div class="card"><div class="num">{{DURATION}}</div><div class="label">Duration</div></div>
  <div class="card"><div class="num" style="color:#e74c3c">{{ROOT_CAUSE}}</div><div class="label">Root Cause Layer</div></div>
</div>

<h2>Web Probe Metrics</h2>
<div class="filters">
  <input type="text" id="search" placeholder="Search metrics, hops, processes..." oninput="applyFilters('probeTable')">
  <button onclick="exportCSV()">Export CSV</button>
</div>
<table id="probeTable">
<thead><tr>
  <th onclick="sortTable('probeTable',0)">Metric &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('probeTable',1)">Value &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('probeTable',2)">Threshold &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('probeTable',3)">Status &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="good|degraded|critical"> per web probe metric -->
</tbody>
</table>

<h2>Cloud Path Topology</h2>
<table id="pathTable">
<thead><tr>
  <th onclick="sortTable('pathTable',0)">Hop &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('pathTable',1)">IP / Hostname &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('pathTable',2)">Latency (ms) &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('pathTable',3)">Packet Loss (%) &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('pathTable',4)">Jitter (ms) &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('pathTable',5)">Status &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="good|degraded|critical"> per hop -->
</tbody>
</table>

<h2>Device Health</h2>
<table id="healthTable">
<thead><tr>
  <th onclick="sortTable('healthTable',0)">Metric &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('healthTable',1)">Value &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('healthTable',2)">Status &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr class="good|degraded|critical"> per health metric -->
</tbody>
</table>

<h2>Top Processes</h2>
<table id="processTable">
<thead><tr>
  <th onclick="sortTable('processTable',0)">Process &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('processTable',1)">CPU % &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('processTable',2)">Memory % &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr> per top process -->
</tbody>
</table>

<h2>Events Timeline</h2>
<table id="eventTable">
<thead><tr>
  <th onclick="sortTable('eventTable',0)">Timestamp &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('eventTable',1)">Type &#x25B4;&#x25BE;</th>
  <th onclick="sortTable('eventTable',2)">Description &#x25B4;&#x25BE;</th>
</tr></thead>
<tbody>
<!-- POPULATE: one <tr> per event -->
</tbody>
</table>

<script>
let sortDirs={};
function sortTable(tid,c){const t=document.getElementById(tid),b=t.tBodies[0],rows=Array.from(b.rows);const k=tid+c;if(!sortDirs[k])sortDirs[k]=1;sortDirs[k]*=-1;rows.sort((a,b_)=>{let x=a.cells[c].textContent.trim(),y=b_.cells[c].textContent.trim();const xn=parseFloat(x),yn=parseFloat(y);if(!isNaN(xn)&&!isNaN(yn))return(xn-yn)*sortDirs[k];return x.localeCompare(y)*sortDirs[k]});rows.forEach(r=>b.appendChild(r))}
function applyFilters(tid){const q=document.getElementById('search').value.toLowerCase();document.querySelectorAll('table tbody tr').forEach(row=>{row.style.display=row.textContent.toLowerCase().includes(q)?'':'none'})}
function exportCSV(){const tables=['probeTable','pathTable','healthTable','processTable','eventTable'];let csv='';tables.forEach(tid=>{const t=document.getElementById(tid),rows=Array.from(t.rows).filter(r=>r.style.display!=='none');csv+=rows.map(r=>Array.from(r.cells).map(c=>'"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\n')+'\n'});const blob=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='deep_trace_diagnosis.csv';a.click()}
</script>
</body>
</html>
```

**MANDATORY STEPS:**
1. Copy this template exactly
2. Replace the `{{...}}` placeholders in the summary cards with real values
3. Add `<tr>` rows inside each `<tbody>` with data from the deep trace tools
4. Set the row class to `good`, `degraded`, or `critical` based on thresholds
5. Write the file to disk and provide the file path to the user

**Both files must be saved to the user's working directory** and the file paths provided in the response.

---

## Workflow

### Step 1: Find the User's Device

```
zdx_list_devices(search="<username_or_email>")
```

Note the `device_id`. If multiple devices, ask the user which one.

---

### Step 2: Check Existing Deep Trace Sessions

```
zdx_list_device_deep_traces(device_id="<device_id>")
```

Review the sessions:
- **In Progress**: The session is still collecting data. Note the expected end time.
- **Completed**: Proceed to analysis (Step 4).
- **No sessions found**: Offer to start a new one (Step 3).

The sessions list shows: Name, Session Type, User, Device, Created Time, Start Time, Status, Application, Created By, Duration (for in-progress), and End Time (for completed).

---

### Step 3: Start a New Diagnostics Session (Write Operation)

Requires `--enable-write-tools`. Only if no suitable trace exists.

First, discover the probe IDs for the target application:

```
zdx_get_web_probes(device_id="<device_id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<device_id>", app_id="<app_id>")
```

Then start the deep trace with all required IDs (all IDs must be integers):

```
zdx_start_deeptrace(
  device_id="<device_id>",
  session_name="Diag-<user>-<date>",
  app_id=<app_id>,
  web_probe_id=<web_probe_id>,
  cloudpath_probe_id=<cloudpath_probe_id>,
  session_length_minutes=15,
  probe_device=True
)
```

**Session duration guidance:**
- **5 minutes**: Quick verification of an intermittent issue
- **15 minutes**: Standard diagnostics session (recommended)
- **30 minutes**: Extended capture for hard-to-reproduce problems
- **60 minutes**: Long-running capture for periodic issues

**Configuration options (from ZDX Admin Portal):**
- **Device Probing**: When enabled, collects device-level CPU, memory, disk, network stats
- **Application**: Target a specific monitored application or add a special URL
- **Web Probe**: DNS, TCP, SSL, HTTP response times
- **Cloud Path Probe**: Hop-by-hop latency, packet loss, jitter with optional thresholds

After starting, inform the user of the expected completion time and wait.

---

### Step 4: Get Trace Summary

```
zdx_get_device_deep_trace(device_id="<device_id>", trace_id="<trace_id>")
```

Review the trace status, start/end times, and high-level findings.

---

### Step 5: Analyze Web Probe Metrics

```
zdx_get_deeptrace_webprobe_metrics(device_id="<device_id>", trace_id="<trace_id>")
```

**Key metrics and thresholds:**

| Metric | Normal | Degraded | Critical | Indicates |
|--------|--------|----------|----------|-----------|
| DNS resolution | < 50ms | 50-150ms | > 150ms | DNS server performance |
| TCP connect | < 100ms | 100-300ms | > 300ms | Network reachability |
| SSL handshake | < 150ms | 150-500ms | > 500ms | TLS negotiation issues |
| HTTP response | < 500ms | 500-2000ms | > 2000ms | Application server health |

**Diagnosis patterns:**
- High DNS only → DNS server or resolution issue
- High TCP + SSL → Network path congestion
- High HTTP only → Application server overload
- All high → Major network or infrastructure event

---

### Step 6: Analyze Cloud Path

```
zdx_get_deeptrace_cloudpath(device_id="<device_id>", trace_id="<trace_id>")
```

View the full hop-by-hop network path. Identify:
- Hops with abnormally high latency (compared to previous hop)
- Hops where packet loss begins
- Whether the issue is in the local network, ISP, or cloud segment

```
zdx_get_deeptrace_cloudpath_metrics(device_id="<device_id>", trace_id="<trace_id>")
```

Check per-hop latency trends, packet loss percentage, and jitter over the trace duration.

**Cloud path interpretation:**
- Latency spike at hop 1-3 → Local network / WiFi issue
- Latency spike at mid-path → ISP backbone issue
- Latency spike at final hops → Cloud provider or application datacenter issue
- Packet loss at a specific hop → Congested or misconfigured router/firewall

---

### Step 7: Analyze Device Health

```
zdx_get_deeptrace_health_metrics(device_id="<device_id>", trace_id="<trace_id>")
```

Check device resource utilization during the trace:
- **CPU > 80%**: Device may be throttling network operations
- **Memory > 90%**: System under memory pressure, swapping
- **Disk I/O high**: Background operations competing for resources
- **Network throughput low**: Interface saturation or driver issues

```
zdx_list_deeptrace_top_processes(device_id="<device_id>", trace_id="<trace_id>")
```

Identify resource-heavy processes. Common culprits:
- Backup software consuming bandwidth
- Security scans consuming CPU
- Browser with many tabs consuming memory
- VPN clients conflicting with Zscaler

---

### Step 8: Review Events Timeline

```
zdx_get_deeptrace_events(device_id="<device_id>", trace_id="<trace_id>")
```

Review all events that occurred during the trace window:

| Event Type | Examples | Impact |
|------------|----------|--------|
| **Zscaler** | Policy changes, tunnel reconnections, service edge switches | May cause temporary connectivity drops |
| **Hardware** | Driver updates, hardware failures, display changes | May impact network adapter performance |
| **Software** | OS updates, app installations, crashes | May compete for resources or change behavior |
| **Network** | Interface changes, WiFi roaming, VPN connect/disconnect | Directly impacts connectivity |

**Correlation technique:** Overlay event timestamps with metric degradation windows. If a Zscaler tunnel reconnection at 10:15 AM coincides with a 30-second spike in TCP connect time, the tunnel reconnection is the likely cause.

---

### Step 9: Present Diagnosis

**Root cause layer identification:**

| Layer | Evidence | Action |
|-------|----------|--------|
| **Device** | High CPU/memory + resource-heavy processes | Optimize device, close unnecessary apps |
| **Local Network** | Packet loss on hops 1-3 + WiFi events | Check WiFi AP, switch, local routing |
| **ISP** | Latency spike mid-path + no device issues | Contact ISP with hop data as evidence |
| **Zscaler** | Tunnel events + correlated metric spikes | Check service edge health, PAC file |
| **Application** | High HTTP response + clean network path | Escalate to app team with ZDX evidence |
| **DNS** | High DNS time + normal TCP/SSL | Check DNS resolver, consider DNS proxy |

Present the complete diagnosis with all tables and analysis as described in the Output Artifacts section.

---

### Step 10: Cleanup (Optional Write Operation)

If the diagnostics session is no longer needed:

```
zdx_delete_deeptrace(device_id="<device_id>", trace_id="<trace_id>")
```

This is a **destructive operation**. Always confirm with the user before deleting.

---

## Edge Cases

### Session Still In Progress

```
Diagnostics session "<session_name>" is still collecting data.
Started: <start_time>
Expected completion: <end_time> (approximately <remaining> minutes)

Partial data may be available. Wait for completion for the most accurate analysis.
```

### No Application Configured

If the user wants to trace an app that isn't monitored:

```
The application is not configured for ZDX monitoring.
You can start a deep trace with a special application URL:

zdx_start_deeptrace(
  device_id="<device_id>",
  session_name="Custom-App-Trace",
  app_url="https://example.com",
  session_length_minutes=15
)
```

### Device Has Active Session

A device can only have one active diagnostics session at a time:

```
Device already has an active diagnostics session:
  Session: <session_name>
  Status: In Progress
  Started: <start_time>

Wait for the current session to complete, or delete it first (requires write tools):
  zdx_delete_deeptrace(device_id="<device_id>", trace_id="<trace_id>")
```

---

## Quick Reference

**Primary workflow:** Find Device → Check Traces → Start/Analyze → Web Probes → Cloud Path → Health → Processes → Events → Diagnosis

**Read-only tools:**
- `zdx_list_device_deep_traces(device_id)` — list all trace sessions
- `zdx_get_device_deep_trace(device_id, trace_id)` — trace summary
- `zdx_get_deeptrace_webprobe_metrics(device_id, trace_id)` — DNS, TCP, SSL, HTTP times
- `zdx_get_deeptrace_cloudpath(device_id, trace_id)` — hop-by-hop network path
- `zdx_get_deeptrace_cloudpath_metrics(device_id, trace_id)` — per-hop latency, loss, jitter
- `zdx_get_deeptrace_health_metrics(device_id, trace_id)` — CPU, memory, disk, network
- `zdx_list_deeptrace_top_processes(device_id, trace_id)` — resource-heavy processes
- `zdx_get_deeptrace_events(device_id, trace_id)` — event timeline

**Probe discovery tools (call before starting a deep trace):**
- `zdx_get_web_probes(device_id, app_id)` — get web_probe_id for the app
- `zdx_list_cloudpath_probes(device_id, app_id)` — get cloudpath_probe_id for the app

**Write tools (require `--enable-write-tools`):**
- `zdx_start_deeptrace(device_id, session_name, app_id, web_probe_id, cloudpath_probe_id, ...)` — start a diagnostics session
- `zdx_delete_deeptrace(device_id, trace_id)` — delete a trace session

**Related skills:**
- [Troubleshoot User Experience](../troubleshoot-user-experience/) — for ZDX score and metric analysis
- [Investigate Alerts](../investigate-alerts/) — for alert-driven investigation
- [Compare Location Experience](../compare-location-experience/) — for site-by-site comparison
