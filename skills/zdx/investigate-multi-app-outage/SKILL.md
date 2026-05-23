---
name: zdx-investigate-multi-app-outage
description: "Diagnose a multi-application outage scoped to one location by correlating ZDX alerts, affected devices, and shared cloud-path hops. Identifies the devices affected at a specific office, compares the per-application network path across multiple SaaS apps to surface the common network bottleneck, and produces an evidence-backed recommendation. Use when an admin reports: 'A ZDX alert shows users in the Columbus office cannot reach Salesforce and ServiceNow', 'Identify affected devices and the common network path issue', 'Multiple users at Dallas are having issues with several SaaS apps', 'What do these failing apps have in common at this office?', or 'Find the shared network bottleneck for the New York users hitting Workday and Box.'"
---

# ZDX: Investigate Multi-Application Outage at a Location

## Keywords

multi-app outage, location outage, office outage, common network path, shared bottleneck, cross-app correlation, hop analysis, ISP issue, cloud path, multiple applications affected, regional outage, site-wide issue, salesforce slow, servicenow slow, cross-tenant impact, shared infrastructure

## Overview

Diagnose a scenario where users at one specific office or location are unable to reach **multiple SaaS applications simultaneously**. The skill correlates active ZDX alerts, scopes impact by location, intersects the affected-device lists across the impacted apps, and then compares the per-application network path (cloud path) on a common affected device to identify the **shared upstream segment** that is the actual root cause.

**Use this skill when:** An admin receives a ZDX alert (or user complaint) that names a single office and two or more applications — e.g., "Columbus users can't reach Salesforce and ServiceNow" — and the desired output is a list of affected devices plus an evidence-backed identification of the shared network path issue.

**ZDX Copilot alignment:** Troubleshooting + Optimization — converts a coarse "users at office X can't reach apps Y/Z" complaint into a hop-level root cause and a prioritized remediation list.

---

## ⚠ HTML OUTPUT — READ THIS BEFORE PRODUCING ANY HTML

**You MUST NOT hand-write or copy/paste an HTML page for this skill.**
There is exactly one acceptable way to produce the HTML output:

1. **Read this file from disk** — do NOT inline a copy in your response. The template lives next to this SKILL.md inside the skill's package, at:

   ```text
   ./templates/report.html.template
   ```

   The `./` prefix is intentional: this path is **relative to the skill folder** (the directory containing this SKILL.md), **never** an absolute path. Most agents that load skills from an uploaded `.zip` extract the package into a working directory and expose its contents via that relative path — read the file by joining the skill's own root directory with `./templates/report.html.template`. Do not rewrite this to an absolute path that points at the author's machine.

2. **Build a single JSON object** (`__ZDX_DATA__` payload) shaped exactly as documented in the *Data Payload Contract* section below. Aggregate the responses from the ZDX MCP tool calls (Steps 1–7 of the *Workflow*) into that object.

3. **Replace** the literal token `__ZDX_DATA__` (which appears once, inside `<script type="application/json" id="zdx-data">__ZDX_DATA__</script>`) with the JSON object. Do not edit any other part of the template.

4. **Write** the result to disk as `multi_app_outage_<location>_<YYYYMMDD-HHMMSS>.html` next to the .docx, and give the user a `computer://` link to it.

This template already provides: Zscaler header with logo · sticky top bar · ACTIVE INCIDENT pill · scope summary bar · color-coded incident banner · 6 KPI cards with severity-coded top borders and subtitles · per-table search + filter chips · sortable color-coded tables · per-table CSV export · light/dark theme toggle · top-right language dropdown (EN / ES / PT / FR / JA) · printable PDF view · localStorage prefs · Analysis / Root Cause / Remediation block.

**If you find yourself writing `<html>`, `<style>`, or `<table>` in a code-block destined for the user, stop. Read the template instead.**

A populated reference rendering ships with this skill at `./example/report.example.html` (relative to the skill folder). Open it in a browser to preview the exact layout and depth expected.

### Data Payload Contract

The full `__ZDX_DATA__` payload is one JSON object. Every field below is **required** unless marked optional.

```json
{
  "generated_at": "2026-05-18T12:00:00Z",

  "scope": {
    "office":    "Columbus Office (ID: 73260557)",
    "apps":      "Salesforce Lightning (ID 18) & ServiceNow (ID 5)",
    "window":    "Last 24h",
    "generated": "2026-05-18T12:00:00Z"
  },

  "incident": {
    "severity": "critical",
    "title":    "Critical — Multi-App Availability Loss at Columbus Office",
    "body":     "2–4 sentences of plain-language explanation: which apps, which alerts (by ID), what the score and PFT/DNS numbers actually mean, what the recent-3-datapoint pattern shows. Don't be terse — the admin reads this first."
  },

  "kpis": {
    "office":          { "value": "Columbus",          "sub": "Location ID 73260557", "severity": "info" },
    "appsAffected":    { "value": 2,                   "sub": "Salesforce Lightning · ServiceNow", "severity": "critical" },
    "affectedDevices": { "value": 5,                   "sub": "Across both alerts (combined)", "severity": "critical" },
    "avgScore":        { "value": "14 / 100",          "sub": "Critical threshold < 34", "severity": "critical" },
    "sharedHop":       { "value": "Hop 3 — Local ISP", "sub": "203.0.113.4 — 4.2–4.8% loss", "severity": "critical" },
    "deepTrace":       { "value": "⚠ No Data",         "sub": "New traces required", "severity": "warning" }
  },

  "columnOverrides": {
    "hops": {
      "app1Latency": "<App1> Latency",
      "app1Loss":    "<App1> Loss",
      "app2Latency": "<App2> Latency",
      "app2Loss":    "<App2> Loss"
    }
  },

  "tables": {
    "devices": [
      {
        "severity":    "Critical",
        "scope":       "ServiceNow Only",
        "device":      "PC-Aniru-71",
        "user":        "Anirudh Singh\nanirudh.singh@thezerotrustexchange.com",
        "os":          "Windows 11 Pro",
        "deviceId":    "86937887",
        "appsFailing": "ServiceNow"
      }
    ],
    "appMetrics": [
      {
        "severity":      "critical",
        "application":   "Salesforce Lightning",
        "appId":         18,
        "zdxScoreAvg":   15.5,
        "zdxScoreMin":   0,
        "pftAvg":        "7,541 ms",
        "pftMax":        "11,855 ms",
        "dnsAvg":        "7,022 ms",
        "probeFailures": "3 / 24 probes",
        "status":        "Critical"
      }
    ],
    "hops": [
      {
        "severity":    "critical",
        "verdict":     "SHARED",
        "hop":         3,
        "address":     "203.0.113.4 (Local ISP)",
        "app1Latency": "248ms", "app1Loss": "4.2%",
        "app2Latency": "255ms", "app2Loss": "4.8%"
      }
    ]
  },

  "analysis": {
    "summary":     "3–5 sentence narrative explaining what the numbers say across the two apps, why the matching metric profile is the strongest correlation signal, and what was ruled out by comparison.",
    "rootCause":   "1–3 sentence statement of the shared bottleneck with the supporting evidence — name the exact hop or segment and quote the latency/loss numbers that pin it.",
    "remediation": [
      "Immediate (within 1 hour): … (concrete action with target)",
      "Capture evidence (within 2 hours): start two deep-trace sessions on device <id> …",
      "Investigate (within 4 hours): … (specific systems to check)",
      "Monitor: schedule a recurring 15-minute deep trace every 4 hours against one affected device per app …",
      "Communicate: notify the affected user list that the issue is identified as ISP-side and Zscaler / apps are not at fault."
    ]
  }
}
```

#### Field rules

- **`generated_at`** — ISO-8601 UTC timestamp.
- **`scope`** — REQUIRED object with `office`, `apps`, `window`, `generated`. The keys map to translated labels (`Office`, `Apps`, `Window`, `Generated`) automatically. Include the location ID and app IDs inline in the values, as shown.
- **`incident`** — REQUIRED object. `severity` is `"critical"` or `"warning"`. The `body` is plain text (no HTML); be specific — quote alert IDs, score ranges, exact metric values, and what the most recent probe attempts returned.
- **`kpis`** — REQUIRED. Every KPI value must be `{value, sub, severity}` (not just a primitive). `severity` controls the top-border color and the number color: `"critical" | "warning" | "good" | "info" | "neutral"`.
- **`columnOverrides.hops`** — REQUIRED. Rename the four generic `app1*` / `app2*` columns to the actual application names for this run so the table reads "Salesforce Latency", "ServiceNow Loss", etc.
- **`tables.devices`** — one row per affected device. `severity` is `"Critical"` (in the intersection — failing every impacted app) or `"Warning"` (failing only some). `scope` is a free-text label like `"ServiceNow Only"`, `"Salesforce Only"`, or the union string.
- **`tables.appMetrics`** — one row per impacted application. Numeric or string-with-unit values are both fine. `status` becomes a colored pill (`Critical` / `Warning` / `Good`).
- **`tables.hops`** — one row per hop. `verdict` is `"SHARED" | "Degraded" | "OK"`. Set `severity` to `"critical"` on `SHARED` rows so the row background turns red.
- **`analysis`** — REQUIRED. Be analytical, not robotic. Tie numbers to conclusions. Match the depth shown in the example.
- **Every row in every table** must include a `severity` field (`"critical" | "warning" | "good" | "info" | "neutral"`) — drives the colored row background.

---

## Output Artifacts — MANDATORY

**You MUST generate BOTH files below. Both files are REQUIRED output for every multi-app outage diagnosis.**

### 1. Word Document (.docx)

Write a Word document to disk named `multi_app_outage_<location>_<date>.docx` containing:

- Executive summary: location, applications affected, count of impacted devices, shared bottleneck identified
- Affected devices table (device, user, OS, ZCC version, last seen, list of apps the device is failing on)
- Per-application metric table at the affected location (PFT, DNS, availability) with deltas vs. organization baseline
- Cloud-path hop comparison table (one row per hop, latency/loss per app side-by-side, flag for shared bottleneck)
- Root cause analysis with supporting evidence — explicitly state which hop or segment is shared
- Healthy-reference comparison (a different office hitting the same apps cleanly, or different apps from the same office hitting cleanly)
- Prioritized remediation actions (immediate, investigate, escalate, monitor)

### 2. Interactive HTML Web Page (.html)

Produced via the template-fill workflow at the top of this file. **No inline HTML.**

---

## Workflow

This is a **multi-tool correlation** skill. Treat the steps below as gates — do not skip ahead; each step's output is required to scope the next. Capture everything you collect into the `__ZDX_DATA__` payload as you go.

### Step 1: Resolve Location & Application IDs

```text
zdx_list_locations(search="Columbus")
```

Capture the location's numeric `id`. If multiple locations match (e.g., "Columbus, OH" and "Columbus, GA"), ask the admin which one before proceeding.

```text
zdx_list_applications(
  location_id=["<location_id>"],
  since=24,
  query="[?contains(name, 'Salesforce') || contains(name, 'ServiceNow')].{id: id, name: name, score: score}"
)
```

Resolve the numeric `id` for each affected application from the response. The `score` here is the score at this location — note it for the `kpis.avgScore` field (low score confirms the alert is genuine).

If an app name is ambiguous (e.g., "Salesforce" matches both "Salesforce" and "Salesforce Marketing Cloud"), confirm with the admin which one is affected.

---

### Step 2: Confirm With Active Alerts at the Location

```text
zdx_list_alerts(location_id=["<location_id>"], since=24)
```

Filter to alerts whose `application` / `app_id` matches one of the IDs from Step 1.

For each matching alert:

```text
zdx_get_alert(alert_id="<alert_id>")
```

Capture: `start_time`, duration, alert trigger / threshold, impacted department(s), and the bottleneck (e.g., `pft`, `dns`, `availability`). Quote the alert IDs verbatim into `incident.body` — they are part of the evidence.

If NO alerts exist for either app at this location, skip to Step 3 anyway — metrics + device lists are enough.

---

### Step 3: Identify Affected Devices Per Alert and Intersect

For each alert from Step 2:

```text
zdx_list_alert_affected_devices(
  alert_id="<alert_id>",
  location_id=["<location_id>"]
)
```

Capture `device_id`, `user`, `os`, `zcc_version`, `last_seen` per device — feed each into a `tables.devices` row.

**Intersect the device lists across apps.** Devices in BOTH alert results are the strongest evidence of shared infrastructure — mark them `severity: "Critical"`, `scope: "<both app names>"` and `appsFailing: "<app1>, <app2>"`. Devices in only one alert get `severity: "Warning"` and `scope: "<that one app> Only"`.

If no alerts were found in Step 2:

```text
zdx_list_devices(location_id=["<location_id>"], since=24)
```

…and use Step 4's metric calls to identify which of those devices are degraded.

**Stop condition:** if the intersection is empty, the two app issues may be coincidental, not a single shared cause. Surface this in `incident.body` rather than forcing a shared-root-cause conclusion.

---

### Step 4: Confirm Bottleneck Pattern With Per-Application Metrics

For each affected app, scoped to the location:

```text
zdx_get_application_metric(app_id="<app_id>", metric_name="pft",          location_id=["<location_id>"], since=24)
zdx_get_application_metric(app_id="<app_id>", metric_name="dns",          location_id=["<location_id>"], since=24)
zdx_get_application_metric(app_id="<app_id>", metric_name="availability", location_id=["<location_id>"], since=24)
```

Feed one row per app into `tables.appMetrics` with averaged / max values, probe-failure count, and a `status` of `Critical` / `Warning` / `Good`.

**Compare the metric profile across the two apps:**

| Pattern | Likely shared root cause |
|---|---|
| Both apps: PFT elevated, DNS OK, availability OK | Upstream network latency (ISP, gateway, peering) |
| Both apps: DNS elevated, PFT degraded as a knock-on | Local DNS resolver / split-horizon misconfiguration |
| Both apps: availability < 100%, PFT spikes | Packet loss in shared upstream segment |
| Different bottleneck per app (one DNS, one PFT) | Not a shared cause — investigate apps separately |

A **matching bottleneck pattern across both apps at the same location** is the second-strongest signal (after the device intersection) that you're looking at one shared infrastructure problem rather than two coincident app issues. State this comparison explicitly in `analysis.summary`.

---

### Step 5: Compare the Cloud Path Across Affected Applications (the key step)

Pick one device from the Step 3 intersection. Then, for that device, gather the cloud path for each impacted app.

```text
zdx_list_device_deep_traces(device_id="<device_id>")
```

If a deep trace exists for an app on this device:

```text
zdx_get_deeptrace_cloudpath(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath_metrics(device_id="<device_id>", trace_id="<trace_id>")
```

Repeat for each impacted app. Then **build the hop comparison rows** for `tables.hops`:

- One row per hop, sorted by hop number.
- `verdict: "SHARED"` and `severity: "critical"` on any hop where every impacted app shows degraded latency or loss.
- `verdict: "Degraded"` and `severity: "warning"` for hops where some apps degrade.
- `verdict: "OK"` and `severity: "good"` for healthy hops.

**Set `columnOverrides.hops` with the actual app names** so the table headers read "Salesforce Latency / ServiceNow Latency" instead of the generic "App 1 / App 2".

If NO traces exist, populate `kpis.deepTrace` with `{"value": "⚠ No Data", "sub": "New traces required", "severity": "warning"}` and skip to Step 7.

---

### Step 6: Cross-Check With a Healthy Reference (Recommended)

To rule out "this hop is always slow," compare against either a different office hitting the same app cleanly, OR a different app from the same office that is NOT in the alert list. Include the result in `analysis.summary`.

---

### Step 7: Capture Evidence With a New Deep Trace (if none exists)

If Step 5 found NO existing traces, you can suspect a shared hop from the metric profile but not yet prove it. Start fresh traces:

```text
zdx_get_web_probes(device_id="<device_id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<device_id>", app_id="<app_id>")
zdx_start_deeptrace(
  device_id="<device_id>",
  session_name="MultiApp-Outage-<location>-<app>-<date>",
  app_id=<app_id>,
  web_probe_id=<id>,
  cloudpath_probe_id=<id>,
  session_length_minutes=15,
  probe_device=True
)
```

`zdx_start_deeptrace` is a **write tool** — requires `--write-tools "zdx_start_deeptrace"` on the server. If disabled, surface the exact commands so the admin can run them after enabling. Once both traces complete, re-run Step 5 with the new trace IDs.

For full deep-trace mechanics, see the Diagnose Deep Trace skill.

---

### Step 8: Compose the Analysis Block

Before assembling the payload, write the `analysis` object — this is what makes the report useful. **Do not skip the analysis prose.**

- **`analysis.summary`** (3–5 sentences): walk through the evidence chain in order. How many devices are in the intersection? What does the per-app metric profile show? What does the hop comparison show (or — if Step 5 was skipped — what does the metric profile alone suggest, and what's the confidence level)?
- **`analysis.rootCause`** (1–3 sentences): name the exact suspected bottleneck. Quote the latency/loss numbers from the hop comparison or the metric table. Explicitly state what was ruled out (Zscaler ingress, app-side, LAN).
- **`analysis.remediation`** (4–6 items): label each item with a priority bucket (`Immediate (within 1 hour)`, `Capture evidence`, `Investigate`, `Monitor`, `Communicate`) and a concrete action with device IDs / hop addresses / user lists inlined where applicable.

The example report at `./example/report.example.html` (relative to this skill folder) shows the depth expected here. Match that.

---

### Step 9: Render the Report

1. Build the JSON payload from Steps 1–8.
2. Read `./templates/report.html.template` (relative to this skill folder — same package as this SKILL.md, do NOT hardcode an absolute path).
3. Replace `__ZDX_DATA__` with your JSON. Verify the JSON parses by checking that all strings are properly quoted and there are no trailing commas.
4. Write the file to disk as `multi_app_outage_<location>_<YYYYMMDD-HHMMSS>.html`.
5. Generate the .docx separately.
6. Give the user `computer://` links to both files.

---

## Edge Cases

### Location name is ambiguous

```text
"Columbus" matches multiple ZDX locations:
  - id 58755: Columbus, OH (45 devices, score 42)
  - id 58756: Columbus, GA (12 devices, score 88)

Which office is affected?
```

Ask before continuing.

### Affected-device intersection is empty

If the two apps' alert device lists don't overlap, the two outages are likely coincidental. Don't force a shared-root-cause narrative — set `incident.severity` to `"warning"` and explain the split in `incident.body` and `analysis.summary`. Recommend running the Investigate Alerts skill once per alert.

### Metric profiles don't match across apps

If Step 4 shows one app bottlenecked on DNS and the other on PFT, this is also "not actually a shared cause." Surface in `analysis.summary` and adjust `analysis.rootCause` to recommend separate investigation.

### No deep traces exist on any affected device

Set `kpis.deepTrace` to `{"value": "⚠ No Data", "sub": "New traces required", "severity": "warning"}`. In `analysis.rootCause` say the attribution is "suspected from metric profile, confirmation pending deep-trace evidence." In `analysis.remediation` make "Capture evidence" the first action.

### Only one app is alerting

Step 4's metric comparison and Step 5's hop comparison work without an alert — they need app IDs and a device list. Use `zdx_list_devices(location_id=...)` for the second app.

### All apps at the location are degraded, not just two

If a quick check (`zdx_list_applications(location_id=[...], since=24)`) shows EVERY monitored app below normal score, this is a site-wide network outage. The diagnosis is the same (a shared upstream segment) but `incident.body` and `analysis.rootCause` should emphasize the office's internet uplink rather than per-app concerns.

---

## Quick Reference

**Primary workflow:** Resolve IDs → Confirm Alerts → Affected Devices + Intersect → Per-App Metrics → Compare Cloud Paths → Healthy Reference → (optional new trace) → Compose Analysis → Render Report

**Tools used:**

- `zdx_list_locations(search)` — resolve location ID by office name
- `zdx_list_applications(location_id, query)` — resolve app IDs by name with JMESPath
- `zdx_list_alerts(location_id, since)` — active alerts scoped to the office
- `zdx_get_alert(alert_id)` — per-alert metadata
- `zdx_list_alert_affected_devices(alert_id, location_id)` — per-alert device list, intersected later
- `zdx_list_devices(location_id, since)` — fallback device fleet if no alerts
- `zdx_get_application_metric(app_id, metric_name, location_id)` — per-app PFT / DNS / availability at the office
- `zdx_get_application_score_trend(app_id, location_id)` — score trend at the office
- `zdx_list_device_deep_traces(device_id)` — find existing traces per device
- `zdx_get_deeptrace_cloudpath(device_id, trace_id)` — hop-by-hop path
- `zdx_get_deeptrace_cloudpath_metrics(device_id, trace_id)` — per-hop latency / loss / jitter
- `zdx_get_web_probes(device_id, app_id)` — discover web_probe_id for new traces
- `zdx_list_cloudpath_probes(device_id, app_id)` — discover cloudpath_probe_id for new traces
- `zdx_start_deeptrace(device_id, ...)` — start a new trace (write tool — requires `--write-tools` allowlist)

**Time windows for `since` (hours, ZDX-specific):**

- `2` — current issues (default)
- `24` — last day
- `48` — last 2 days
- `168` — last week

**Related skills:**

- Investigate Alerts — single-alert deep dive (use when only one app is affected)
- Troubleshoot User Experience — single-user deep dive
- Compare Location Experience — cross-location comparison (use when admin asks "which office is worst?")
- Diagnose Deep Trace — full deep-trace analysis once traces are captured
- Analyze Application Health — when ALL apps are degraded org-wide (not just at one office)
