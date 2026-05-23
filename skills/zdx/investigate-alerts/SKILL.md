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

**All tables are rendered by the HTML template, not by hand.** Do not author `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, or `<td>` markup in your reply or in the report. You produce a JSON payload (see *Data Payload Contract*) and the template at `./templates/report.html.template` turns it into the styled, sortable, exportable tables shown in `./example/report.example.html`.

After each table, provide:

1. **Detailed analysis** explaining the alert severity, scope, and correlation between alerts
2. **Root cause identification** based on metric correlation and affected scope
3. **Next steps / resolution** with specific remediation actions, escalation paths, and monitoring recommendations

Use color-coded rows by alert priority:

- Red: High priority alerts (many affected devices, critical applications, long duration)
- Yellow: Medium priority alerts (moderate impact, localized scope)
- Green: Low priority or resolved alerts

## ⚠ HTML OUTPUT — READ THIS BEFORE PRODUCING ANY HTML

There is exactly one acceptable way to produce the HTML output:

1. **Read the template from disk** — do NOT inline a copy in your response. The template lives next to this SKILL.md inside the skill's package, at:

   ```text
   ./templates/report.html.template
   ```

   The `./` prefix is intentional: this path is **relative to the skill folder** (the directory containing this SKILL.md), **never** an absolute path. Most agents that load skills from an uploaded `.zip` extract the package into a working directory and expose its contents via that relative path — read the file by joining the skill's own root directory with `./templates/report.html.template`. Do not rewrite this to an absolute path that points at the author's machine.

2. **Build a single JSON object** (`__ZDX_DATA__` payload) shaped exactly as documented in the *Data Payload Contract* section below. Aggregate the responses from the ZDX MCP tool calls (Steps 1–6 of the *Workflow*) into that object.

3. **Replace** the literal token `__ZDX_DATA__` (which appears once, inside `<script type="application/json" id="zdx-data">__ZDX_DATA__</script>`) with the JSON object. Do not edit any other part of the template.

4. **Write** the result to disk as `alert_investigation_report_<YYYYMMDD-HHMMSS>.html` next to the .docx, and give the user a `computer://` link to it.

This template already provides: Zscaler header with logo · sticky top bar · scope summary bar · KPI cards with severity-coded top borders · per-table search + filter chips · sortable color-coded tables · per-table CSV export · light/dark theme toggle · top-right language dropdown (EN / ES / PT / FR / JA) · printable PDF view · localStorage prefs · Analysis / Root Cause / Remediation block.

**If you find yourself writing `<html>`, `<style>`, or `<table>` in a code-block destined for the user, stop. Read the template instead.**

A populated reference rendering ships with this skill at `./example/report.example.html` (relative to the skill folder). Open it in a browser to preview the exact layout and depth expected.

### Data Payload Contract

The full `__ZDX_DATA__` payload is one JSON object. Every field below is **required** unless marked optional. This skill emits **two tables**: the active alert summary and the per-alert metric correlation.

```json
{
  "generated_at": "<ISO 8601 timestamp>",
  "scope_en": "Free-form description in English",
  "scope_es": "...in Spanish (optional, falls back to scope_en)",
  "scope_pt": "...in Portuguese (optional)",
  "scope_fr": "...in French (optional)",
  "scope_ja": "...in Japanese (optional)",
  "kpis": {
    "total": "<int>",
    "high": "<int>",
    "medium": "<int>",
    "low": "<int>",
    "mostAffectedApp": "<app name or '—'>",
    "impactedDevices": "<int>"
  },
  "tables": {
    "alerts": [
      {
        "severity": "critical | warning | good",
        "priority": "High | Medium | Low",
        "name": "<alert title>",
        "application": "<app name>",
        "duration": "<e.g. '6 hours'>",
        "affectedDevices": "<int>",
        "locations": "<comma-separated location names>",
        "bottleneck": "<e.g. 'PFT: 12.4s'>",
        "status": "Active | Resolved"
      }
    ],
    "correlation": [
      {
        "severity": "critical | warning | good",
        "alert": "<alert title>",
        "pft": "<value or '—'>",
        "dns": "<value or '—'>",
        "availability": "<value or '—'>",
        "rootCauseIndicator": "Server-side / CDN | Local DNS resolver | Application server instability | ISP path | …"
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

Map each row's `severity` from `priority`: `High` → `critical`, `Medium` → `warning`, `Low` → `good`.

## Output Artifacts — MANDATORY

You MUST generate BOTH files below. Both are REQUIRED output for every alert investigation.

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `alert_investigation_report_<YYYYMMDD-HHMMSS>.docx` containing:

- Executive summary with active alert count, severity breakdown, and scope
- Active alerts table (priority, alert name, application, duration, affected devices, locations, bottleneck)
- Metric correlation per alert (PFT, DNS, availability, root cause indicator)
- Historical pattern analysis (recurring alerts, frequency, time patterns)
- Per-alert root cause analysis with supporting evidence
- Prioritized remediation actions and escalation paths

### 2. Interactive HTML Web Page (.html) — REQUIRED

Generated by the template-substitution flow described in the **HTML OUTPUT** section above. Filename: `alert_investigation_report_<YYYYMMDD-HHMMSS>.html`. Do not hand-author HTML or CSS — the template ships everything the report needs.

---

## Workflow

### Step 1: List Active Alerts

Retrieve all currently active alerts.

```text
zdx_list_alerts()
```text

For a broader time window (e.g., last 48 hours):

```text
zdx_list_alerts(since=48)
```text

Filter by location or department for scoped investigation:

```text
zdx_list_alerts(
  location_id=["<location_id>"],
  since=24
)
```text

```text
zdx_list_alerts(
  department_id=["<department_id>"],
  since=24
)
```text

**Triage by severity and scope:**

- How many alerts are active?
- Which applications are affected?
- How long have they been active?
- Are multiple alerts pointing to the same root cause?

---

### Step 2: Get Alert Details

For each alert that warrants investigation:

```text
zdx_get_alert(alert_id="<alert_id>")
```text

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

```text
zdx_list_alert_affected_devices(alert_id="<alert_id>")
```text

Filter by location to understand geographic scope:

```text
zdx_list_alert_affected_devices(
  alert_id="<alert_id>",
  location_id=["<location_id>"]
)
```text

Filter by department for business impact:

```text
zdx_list_alert_affected_devices(
  alert_id="<alert_id>",
  department_id=["<department_id>"]
)
```text

**Scope determination:**

- **Single user:** Likely a device or local network issue
- **Single location:** Office-specific issue (local ISP, WiFi, LAN)
- **Multiple locations, same geo:** Regional ISP or cloud region issue
- **Global:** Application server issue or major ISP backbone problem

---

### Step 4: Correlate with Application Metrics

Cross-reference the alert with application performance data to confirm the bottleneck.

```text
zdx_get_application_score_trend(
  app_id="<affected_app_id>",
  since=24
)
```text

```text
zdx_get_application_metric(
  app_id="<affected_app_id>",
  metric_name="pft"
)
```text

```text
zdx_get_application_metric(
  app_id="<affected_app_id>",
  metric_name="dns"
)
```text

```text
zdx_get_application_metric(
  app_id="<affected_app_id>",
  metric_name="availability"
)
```text

**Correlation mapping:**

- Alert + high PFT + normal DNS → Application or CDN issue
- Alert + high DNS → DNS infrastructure problem
- Alert + low availability → Network or application unreachable
- Alert + all metrics degraded → Major infrastructure event

---

### Step 5: Check Historical Patterns

Look for recurring patterns in past alerts.

```text
zdx_list_historical_alerts(since=336)
```text

Filter by location or department:

```text
zdx_list_historical_alerts(
  location_id=["<location_id>"],
  since=168
)
```text

**Pattern analysis:**

- Same alert recurring daily at specific times? → Scheduled load or maintenance window
- Same alert recurring weekly? → Periodic resource constraints
- Same location repeatedly affected? → Infrastructure issue at that site
- Same application repeatedly affected? → Application stability concerns

---

### Step 6: Deep Trace for Network Path Analysis

If the alert suggests a network issue, check if deep traces exist for affected devices.

```text
zdx_list_devices(location_id=["<affected_location_id>"])
```text

For a specific affected device:

```text
zdx_list_device_deep_traces(device_id="<device_id>")
```text

If a trace exists, analyze the full diagnostics data:

```text
zdx_get_device_deep_trace(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_webprobe_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_health_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_list_deeptrace_top_processes(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_events(device_id="<device_id>", trace_id="<trace_id>")
```text

If no trace exists and the alert is recurring, discover probe IDs and start a proactive deep trace to capture evidence during the next occurrence (requires write tools):

```text
zdx_get_web_probes(device_id="<device_id>", app_id="<affected_app_id>")
zdx_list_cloudpath_probes(device_id="<device_id>", app_id="<affected_app_id>")
zdx_start_deeptrace(device_id="<device_id>", session_name="Alert-Investigation-<date>", app_id=<app_id>, web_probe_id=<id>, cloudpath_probe_id=<id>, session_length_minutes=30, probe_device=True)
```text

Deep traces reveal hop-by-hop latency and packet loss, pinpointing the exact network segment causing the issue. Web probe metrics isolate DNS vs TCP vs SSL bottlenecks, and event timelines correlate configuration changes with metric degradation.

For comprehensive deep trace analysis, see the [Diagnose Deep Trace](../diagnose-deeptrace/) skill.

---

### Step 7: Present Alert Investigation Report

Assemble the `__ZDX_DATA__` payload defined in the *Data Payload Contract* and render it through `./templates/report.html.template` (see the **HTML OUTPUT** section). The template already produces both the alert table and the metric-correlation table, plus KPI cards, color coding by priority, search/sort, and CSV export — do **not** hand-author any HTML or markdown table here.

What you DO write is the `analysis` block inside the payload. **Do not skip it.** This is what makes the investigation useful:

- **`analysis.summary`** (3–5 sentences): rank the alerts by impact, name the highest-priority one and why, and call out whether multiple alerts share a root cause. Quote concrete numbers from Steps 2–4 (e.g., *"47 devices across 3 locations with PFT at 12.4s indicates a server-side issue, not a local network problem"*).
- **`analysis.rootCause`** (1–3 sentences per active alert): map the alert to the dominant bottleneck. Cite the historical pattern data from Step 5 (recurring vs. new) and the deep-trace evidence from Step 6 when available.
- **`analysis.remediation`** (4–6 items): label each with a priority bucket and a concrete action.

| Priority | Apply to | Action |
|---|---|---|
| `Immediate` | HIGH alerts and any alert with > 25 affected devices | Engage the vendor / service-health dashboard. Validate Zscaler cloud path. Open a P1 with supporting ZDX evidence (PFT / DNS / loss / hop). |
| `Investigate` | MEDIUM alerts and recurring alerts | Compare the affected location/department against healthy peers. Drill into the bottleneck metric. Open a P2 with the historical pattern as evidence. |
| `Monitor` | LOW alerts and brand-new alerts (< 30 min) | Watch for 1 hour. If still active or impact grows, promote to `Investigate`. |
| `Communicate` | Any alert with multi-location impact | Notify location IT contacts; surface the alert in the next change/incident review. |

---

## Common Investigation Scenarios

### ISP-Related Issues

When an alert suggests ISP problems:

1. Check affected locations -- if all are in the same region, likely a regional ISP
2. Use deep traces to identify the specific ISP hop with high latency/loss
3. Compile the evidence (deep trace data, affected users, time range) for the ISP

```text
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
```text

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

```text
No active alerts in the requested time window.

All monitored applications are within normal thresholds.

Consider:
- Checking historical alerts for recent resolved issues
- Reviewing alert configuration to ensure thresholds are appropriate
- Using the Analyze Application Health skill for a proactive review
```text

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

**Time windows for `since` (hours):**

- `2` -- current issues (default)
- `24` -- last day
- `48` -- last 2 days
- `168` -- last week
- `336` -- last 2 weeks (max)

**Related skills:**

- [Troubleshoot User Experience](../troubleshoot-user-experience/) -- for individual user investigation
- [Diagnose Deep Trace](../diagnose-deeptrace/) -- for comprehensive deep trace analysis
- [Analyze Application Health](../analyze-application-health/) -- for app-level overview
- [Compare Location Experience](../compare-location-experience/) -- for location-based analysis
