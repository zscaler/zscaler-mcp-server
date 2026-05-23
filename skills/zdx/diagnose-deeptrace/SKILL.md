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

**All tables are rendered by the HTML template, not by hand.** Do not author `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, or `<td>` markup in your reply or in the report. You produce a JSON payload (see *Data Payload Contract*) and the template at `./templates/report.html.template` turns it into the styled, sortable, exportable tables shown in `./example/report.example.html`.

After each table, provide:

1. **Detailed analysis** explaining what the metrics reveal about the user's connectivity
2. **Root cause identification** mapped to the specific layer (device, network, DNS, application, configuration)
3. **Next steps / resolution** with specific, actionable recommendations

Use color-coded status indicators:

- Green/Good: Metrics within normal range (latency < 50ms, packet loss 0%, healthy CPU/memory)
- Yellow/Degraded: Metrics approaching thresholds (latency 50-150ms, packet loss 1-5%, moderate resource usage)
- Red/Critical: Metrics exceeding thresholds (latency > 150ms, packet loss > 5%, resource exhaustion)

## ⚠ HTML OUTPUT — READ THIS BEFORE PRODUCING ANY HTML

There is exactly one acceptable way to produce the HTML output:

1. **Read the template from disk** — do NOT inline a copy in your response. The template lives next to this SKILL.md inside the skill's package, at:

   ```text
   ./templates/report.html.template
   ```

   The `./` prefix is intentional: this path is **relative to the skill folder** (the directory containing this SKILL.md), **never** an absolute path. Most agents that load skills from an uploaded `.zip` extract the package into a working directory and expose its contents via that relative path — read the file by joining the skill's own root directory with `./templates/report.html.template`. Do not rewrite this to an absolute path that points at the author's machine.

2. **Build a single JSON object** (`__ZDX_DATA__` payload) shaped exactly as documented in the *Data Payload Contract* section below. Aggregate the responses from the ZDX MCP tool calls (Steps 1–8 of the *Workflow*) into that object.

3. **Replace** the literal token `__ZDX_DATA__` (which appears once, inside `<script type="application/json" id="zdx-data">__ZDX_DATA__</script>`) with the JSON object. Do not edit any other part of the template.

4. **Write** the result to disk as `deep_trace_diagnosis_<YYYYMMDD-HHMMSS>.html` next to the .docx, and give the user a `computer://` link to it.

This template already provides: Zscaler header with logo · sticky top bar · scope summary bar · KPI cards with severity-coded top borders · per-table search + filter chips · sortable color-coded tables · per-table CSV export · light/dark theme toggle · top-right language dropdown (EN / ES / PT / FR / JA) · printable PDF view · localStorage prefs · Analysis / Root Cause / Remediation block.

**If you find yourself writing `<html>`, `<style>`, or `<table>` in a code-block destined for the user, stop. Read the template instead.**

A populated reference rendering ships with this skill at `./example/report.example.html` (relative to the skill folder). Open it in a browser to preview the exact layout and depth expected.

### Data Payload Contract

The full `__ZDX_DATA__` payload is one JSON object. Every field below is **required** unless marked optional. This skill emits **five tables**: web probe metrics, cloud path topology, device health, top processes, and events timeline.

```json
{
  "generated_at": "<ISO 8601 timestamp>",
  "scope_en": "Free-form description in English",
  "scope_es": "...in Spanish (optional, falls back to scope_en)",
  "scope_pt": "...in Portuguese (optional)",
  "scope_fr": "...in French (optional)",
  "scope_ja": "...in Japanese (optional)",
  "kpis": {
    "user": "<user name or email>",
    "device": "<device hostname>",
    "session": "<session name or id>",
    "status": "Completed | In Progress | Failed",
    "duration": "<e.g. '14m'>",
    "rootCauseLayer": "Device | Local Network | ISP | Zscaler | Application | DNS | —"
  },
  "tables": {
    "probes": [
      {
        "severity": "critical | warning | good",
        "metric": "DNS | TCP | SSL | HTTP Response",
        "value": "<measured value, e.g. '186ms'>",
        "threshold": "<expected value, e.g. '<50ms'>",
        "status": "Good | Degraded | Critical"
      }
    ],
    "path": [
      {
        "severity": "critical | warning | good",
        "hop": "<int>",
        "host": "<IP or hostname>",
        "latency": "<int, ms>",
        "loss": "<float, %>",
        "jitter": "<int, ms>",
        "status": "Good | Degraded | Critical"
      }
    ],
    "health": [
      {
        "severity": "critical | warning | good",
        "metric": "CPU | Memory | Disk I/O | Network",
        "value": "<e.g. '92%'>",
        "status": "Good | Degraded | Critical"
      }
    ],
    "processes": [
      {
        "severity": "critical | warning | good | neutral",
        "name": "<process name>",
        "cpu": "<float, %>",
        "memory": "<float, %>"
      }
    ],
    "events": [
      {
        "severity": "critical | warning | good | info",
        "timestamp": "<ISO 8601>",
        "type": "Zscaler | Hardware | Software | Network",
        "description": "<event description>"
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

Map each row's `severity` from `status` (or threshold delta for probes/path/health): `Good` → `good`, `Degraded` → `warning`, `Critical` → `critical`.

## Output Artifacts — MANDATORY

You MUST generate BOTH files below. Both are REQUIRED output for every deep trace diagnosis.

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `deep_trace_diagnosis_<YYYYMMDD-HHMMSS>.docx` containing:

- Session summary (name, type, user, device, status, start/end time, duration)
- Web probe metrics breakdown (DNS, TCP, SSL, HTTP response times)
- Cloud path topology with per-hop latency, packet loss, and jitter analysis
- Device health assessment (CPU, memory, disk I/O, network utilization)
- Top processes consuming resources during the trace
- Event correlation timeline (Zscaler, hardware, software, network changes)
- Root cause analysis mapped to the affected layer
- Prioritized remediation actions

### 2. Interactive HTML Web Page (.html) — REQUIRED

Generated by the template-substitution flow described in the **HTML OUTPUT** section above. Filename: `deep_trace_diagnosis_<YYYYMMDD-HHMMSS>.html`. Do not hand-author HTML or CSS — the template ships everything the report needs.

---

## Workflow

### Step 1: Find the User's Device

```text
zdx_list_devices(search="<username_or_email>")
```text

Note the `device_id`. If multiple devices, ask the user which one.

---

### Step 2: Check Existing Deep Trace Sessions

```text
zdx_list_device_deep_traces(device_id="<device_id>")
```text

Review the sessions:

- **In Progress**: The session is still collecting data. Note the expected end time.
- **Completed**: Proceed to analysis (Step 4).
- **No sessions found**: Offer to start a new one (Step 3).

The sessions list shows: Name, Session Type, User, Device, Created Time, Start Time, Status, Application, Created By, Duration (for in-progress), and End Time (for completed).

---

### Step 3: Start a New Diagnostics Session (Write Operation)

Requires `--enable-write-tools`. Only if no suitable trace exists.

First, discover the probe IDs for the target application:

```text
zdx_get_web_probes(device_id="<device_id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<device_id>", app_id="<app_id>")
```text

Then start the deep trace with all required IDs (all IDs must be integers):

```text
zdx_start_deeptrace(
  device_id="<device_id>",
  session_name="Diag-<user>-<date>",
  app_id=<app_id>,
  web_probe_id=<web_probe_id>,
  cloudpath_probe_id=<cloudpath_probe_id>,
  session_length_minutes=15,
  probe_device=True
)
```text

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

```text
zdx_get_device_deep_trace(device_id="<device_id>", trace_id="<trace_id>")
```text

Review the trace status, start/end times, and high-level findings.

---

### Step 5: Analyze Web Probe Metrics

```text
zdx_get_deeptrace_webprobe_metrics(device_id="<device_id>", trace_id="<trace_id>")
```text

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

```text
zdx_get_deeptrace_cloudpath(device_id="<device_id>", trace_id="<trace_id>")
```text

View the full hop-by-hop network path. Identify:

- Hops with abnormally high latency (compared to previous hop)
- Hops where packet loss begins
- Whether the issue is in the local network, ISP, or cloud segment

```text
zdx_get_deeptrace_cloudpath_metrics(device_id="<device_id>", trace_id="<trace_id>")
```text

Check per-hop latency trends, packet loss percentage, and jitter over the trace duration.

**Cloud path interpretation:**

- Latency spike at hop 1-3 → Local network / WiFi issue
- Latency spike at mid-path → ISP backbone issue
- Latency spike at final hops → Cloud provider or application datacenter issue
- Packet loss at a specific hop → Congested or misconfigured router/firewall

---

### Step 7: Analyze Device Health

```text
zdx_get_deeptrace_health_metrics(device_id="<device_id>", trace_id="<trace_id>")
```text

Check device resource utilization during the trace:

- **CPU > 80%**: Device may be throttling network operations
- **Memory > 90%**: System under memory pressure, swapping
- **Disk I/O high**: Background operations competing for resources
- **Network throughput low**: Interface saturation or driver issues

```text
zdx_list_deeptrace_top_processes(device_id="<device_id>", trace_id="<trace_id>")
```text

Identify resource-heavy processes. Common culprits:

- Backup software consuming bandwidth
- Security scans consuming CPU
- Browser with many tabs consuming memory
- VPN clients conflicting with Zscaler

---

### Step 8: Review Events Timeline

```text
zdx_get_deeptrace_events(device_id="<device_id>", trace_id="<trace_id>")
```text

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

Use the table above to pick the dominant **root cause layer**, then assemble the `__ZDX_DATA__` payload defined in the *Data Payload Contract* and render it through `./templates/report.html.template` (see the **HTML OUTPUT** section). The template already produces the five tables (probes, path, health, processes, events), KPI cards, color coding, search/sort, and CSV export — do **not** hand-author any HTML here.

Write the `analysis` block before rendering:

- **`analysis.summary`** (3–5 sentences): which layer is the bottleneck, the strongest piece of evidence (single number / hop), and whether this is a one-off or part of a recurring pattern.
- **`analysis.rootCause`** (2–4 sentences): map the layer to the evidence row that proves it (e.g., *"hop 4 (203.0.113.10) shows 187 ms latency and 6% packet loss — every downstream metric is degraded from that hop on, isolating the issue to the ISP segment, not the device or Zscaler edge"*).
- **`analysis.remediation`** (3–5 items): each `priority` uses the same buckets as the other skills (`Immediate`, `Investigate`, `Monitor`, `Communicate`).

---

### Step 10: Cleanup (Optional Write Operation)

If the diagnostics session is no longer needed:

```text
zdx_delete_deeptrace(device_id="<device_id>", trace_id="<trace_id>")
```text

This is a **destructive operation**. Always confirm with the user before deleting.

---

## Edge Cases

### Session Still In Progress

```text
Diagnostics session "<session_name>" is still collecting data.
Started: <start_time>
Expected completion: <end_time> (approximately <remaining> minutes)

Partial data may be available. Wait for completion for the most accurate analysis.
```text

### No Application Configured

If the user wants to trace an app that isn't monitored:

```text
The application is not configured for ZDX monitoring.
You can start a deep trace with a special application URL:

zdx_start_deeptrace(
  device_id="<device_id>",
  session_name="Custom-App-Trace",
  app_url="https://example.com",
  session_length_minutes=15
)
```text

### Device Has Active Session

A device can only have one active diagnostics session at a time:

```text
Device already has an active diagnostics session:
  Session: <session_name>
  Status: In Progress
  Started: <start_time>

Wait for the current session to complete, or delete it first (requires write tools):
  zdx_delete_deeptrace(device_id="<device_id>", trace_id="<trace_id>")
```text

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
