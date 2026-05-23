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

**All tables are rendered by the HTML template, not by hand.** Do not author `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, or `<td>` markup in your reply or in the report. You produce a JSON payload (see *Data Payload Contract*) and the template at `./templates/report.html.template` turns it into the styled, sortable, exportable tables shown in `./example/report.example.html`.

After each table, provide:

1. **Detailed analysis** explaining what the data means in plain language
2. **Root cause identification** based on the metrics and patterns
3. **Next steps / resolution** with specific, actionable recommendations prioritized by impact

Use color-coded status indicators in tables:

- Green/Good: scores 66-100, metrics within normal range
- Yellow/Degraded: scores 34-65, metrics approaching thresholds
- Red/Poor: scores 0-33, metrics exceeding thresholds

## ⚠ HTML OUTPUT — READ THIS BEFORE PRODUCING ANY HTML

There is exactly one acceptable way to produce the HTML output:

1. **Read the template from disk** — do NOT inline a copy in your response. The template lives next to this SKILL.md inside the skill's package, at:

   ```text
   ./templates/report.html.template
   ```

   The `./` prefix is intentional: this path is **relative to the skill folder** (the directory containing this SKILL.md), **never** an absolute path. Most agents that load skills from an uploaded `.zip` extract the package into a working directory and expose its contents via that relative path — read the file by joining the skill's own root directory with `./templates/report.html.template`. Do not rewrite this to an absolute path that points at the author's machine.

2. **Build a single JSON object** (`__ZDX_DATA__` payload) shaped exactly as documented in the *Data Payload Contract* section below. Aggregate the responses from the ZDX MCP tool calls (Steps 1–5 of the *Workflow*) into that object.

3. **Replace** the literal token `__ZDX_DATA__` (which appears once, inside `<script type="application/json" id="zdx-data">__ZDX_DATA__</script>`) with the JSON object. Do not edit any other part of the template.

4. **Write** the result to disk as `user_experience_diagnosis_<YYYYMMDD-HHMMSS>.html` next to the .docx, and give the user a `computer://` link to it.

This template already provides: Zscaler header with logo · sticky top bar · scope summary bar · KPI cards with severity-coded top borders · per-table search + filter chips · sortable color-coded tables · per-table CSV export · light/dark theme toggle · top-right language dropdown (EN / ES / PT / FR / JA) · printable PDF view · localStorage prefs · Analysis / Root Cause / Remediation block.

**If you find yourself writing `<html>`, `<style>`, or `<table>` in a code-block destined for the user, stop. Read the template instead.**

A populated reference rendering ships with this skill at `./example/report.example.html` (relative to the skill folder). Open it in a browser to preview the exact layout and depth expected.

### Data Payload Contract

The full `__ZDX_DATA__` payload is one JSON object. Every field below is **required** unless marked optional. This skill emits **two tables**: the device/user summary and the per-metric breakdown.

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
    "device": "<device hostname or model>",
    "score": "<int, 0-100>",
    "bottleneck": "DNS | TCP | SSL | Server | Page Load | —",
    "alerts": "<int>"
  },
  "tables": {
    "summary": [
      { "severity": "neutral", "field": "User",       "value": "<name (email)>" },
      { "severity": "neutral", "field": "Device",     "value": "<device_type, os_version>" },
      { "severity": "neutral", "field": "Location",   "value": "<location>" },
      { "severity": "neutral", "field": "Department", "value": "<department>" },
      { "severity": "neutral", "field": "ZCC Version","value": "<version>" },
      { "severity": "critical | warning | good", "field": "Experience Score", "value": "<score>/100 (<label>)" }
    ],
    "metrics": [
      {
        "severity": "critical | warning | good",
        "name": "DNS Resolution | TCP Connect | SSL Handshake | Server Response | Page Load",
        "current": "<e.g. '850ms' | 'Timeout' | 'N/A'>",
        "normal": "<e.g. '< 100ms'>",
        "category": "DNS | Network | Server | Client",
        "status": "OK | Degraded | Critical",
        "impact": "<short user-facing impact, e.g. 'Application unreachable'>"
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

Map each row's `severity` from `status`: `OK` → `good`, `Degraded` → `warning`, `Critical` → `critical`. The static summary rows are `neutral` except the Experience Score row, which carries the same severity bucket as the user's overall score.

## Output Artifacts — MANDATORY

You MUST generate BOTH files below. Both are REQUIRED output for every user experience diagnosis.

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `user_experience_diagnosis_<YYYYMMDD-HHMMSS>.docx` containing:

- User and device summary (name, email, device type, OS, location, department)
- Application experience scores with trend analysis
- Metric breakdown (DNS, TCP connect, SSL handshake, server response, page load)
- Root cause analysis with supporting evidence
- Alert correlation (if any active alerts match the issue)
- Recommended resolution steps prioritized by impact

### 2. Interactive HTML Web Page (.html) — REQUIRED

Generated by the template-substitution flow described in the **HTML OUTPUT** section above. Filename: `user_experience_diagnosis_<YYYYMMDD-HHMMSS>.html`. Do not hand-author HTML or CSS — the template ships everything the report needs.

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

Assemble the `__ZDX_DATA__` payload defined in the *Data Payload Contract* and render it through `./templates/report.html.template` (see the **HTML OUTPUT** section). The template already produces the device/user summary, the per-metric table, KPI cards, color coding by status, search/sort, and CSV export — do **not** hand-author any HTML or markdown table here.

What you DO write is the `analysis` block inside the payload. **Do not skip it.** This is what makes the diagnosis useful:

- **`analysis.summary`** (3–5 sentences): which metric(s) are out of range and by how much. Quote concrete numbers from Steps 2–3 (e.g., *"Server response time has degraded from normal (180ms) to timeout. TCP connect is also elevated at 850ms vs. 65ms baseline."*). Call out whether the issue is client-specific or shared (Step 4's `impacted_users`).
- **`analysis.rootCause`** (2–4 sentences): the dominant bottleneck and what it points to (network congestion, server overload, local device issue, ZCC tunnel, ZPA app-connector health, etc.). Cite alert correlation from Step 4 when present.
- **`analysis.remediation`** (4–6 items): label each with a priority bucket and a concrete action.

| Priority | Apply to | Action |
|---|---|---|
| `Immediate` | Critical-status metrics (timeout, failure) | Check application server health in the affected datacenter. If ZPA, verify app-connector health for the server group. |
| `Investigate` | Degraded metrics | Run a deep trace (see the `diagnose-deeptrace` skill) to identify the exact hop causing latency. Check ISP / cloud provider status pages. |
| `Monitor` | Borderline metrics + intermittent reports | Schedule a follow-up score check in 1–4 hours. If the score keeps dropping, promote to `Investigate`. |
| `Communicate` | Issues affecting ≥ 5 users at the same site | Notify the location IT contact with the ZDX evidence. If server-side, engage the application team. |

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
