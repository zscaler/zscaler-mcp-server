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

**All tables are rendered by the HTML template, not by hand.** Do not author `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, or `<td>` markup in your reply or in the report. You produce a JSON payload (see *Data Payload Contract*) and the template at `./templates/report.html.template` turns it into the styled, sortable, exportable tables shown in `./example/report.example.html`.

After each table, provide:

1. **Detailed analysis** explaining what the data means in plain language
2. **Root cause identification** for degraded or poor applications
3. **Next steps / resolution** with specific, actionable recommendations prioritized by impact

Use color-coded status indicators in tables:

- Green/Good: scores 66-100, metrics within normal range
- Yellow/Okay: scores 34-65, metrics approaching thresholds
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

4. **Write** the result to disk as `application_health_report_<YYYYMMDD-HHMMSS>.html` next to the .docx, and give the user a `computer://` link to it.

This template already provides: Zscaler header with logo · sticky top bar · scope summary bar · KPI cards with severity-coded top borders · per-table search + filter chips · sortable color-coded tables · per-table CSV export · light/dark theme toggle · top-right language dropdown (EN / ES / PT / FR / JA) · printable PDF view · localStorage prefs · Analysis / Root Cause / Remediation block.

**If you find yourself writing `<html>`, `<style>`, or `<table>` in a code-block destined for the user, stop. Read the template instead.**

A populated reference rendering ships with this skill at `./example/report.example.html` (relative to the skill folder). Open it in a browser to preview the exact layout and depth expected.

### Data Payload Contract

The full `__ZDX_DATA__` payload is one JSON object. Every field below is **required** unless marked optional.

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
    "good": "<int>",
    "okay": "<int>",
    "poor": "<int>",
    "mostImpacted": "<app name or '—'>"
  },
  "tables": {
    "apps": [
      {
        "severity": "critical | warning | good",
        "name": "<application name>",
        "score": "<0-100>",
        "status": "Good | Okay | Poor",
        "pft": "<page fetch time, e.g. '1.2s'>",
        "dns": "<dns time, e.g. '18ms'>",
        "availability": "<percentage, e.g. '99%'>",
        "impactedUsers": "<int or summary string>",
        "bottleneck": "DNS | PFT | Availability | None"
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

Map each row's `severity` from `status`: `Good` → `good`, `Okay` → `warning`, `Poor` → `critical`.

## Output Artifacts — MANDATORY

You MUST generate BOTH files below. Both are REQUIRED output for every application health analysis.

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `application_health_report_<YYYYMMDD-HHMMSS>.docx` containing:

- Executive summary with overall health posture (healthy/degraded/poor counts)
- Application health table (app name, score, status, PFT, DNS, availability, impacted users, bottleneck)
- Per-application deep dive for degraded/poor apps with metric trends
- Root cause analysis per degraded application
- User impact breakdown by location and department
- Prioritized remediation actions

### 2. Interactive HTML Web Page (.html) — REQUIRED

Generated by the template-substitution flow described in the **HTML OUTPUT** section above. Filename: `application_health_report_<YYYYMMDD-HHMMSS>.html`. Do not hand-author HTML or CSS — the template ships everything the report needs.

---

## Workflow

### Step 1: List All Monitored Applications

Retrieve the full list of applications monitored by ZDX.

```text
zdx_list_applications()
```text

Optionally filter by location, department, or geolocation:

```text
zdx_list_applications(
  location_id=["<location_id>"],
  department_id=["<department_id>"],
  since=4
)
```text

**Categorize results by score:**

- **Good (66-100):** Healthy, no action needed
- **Okay (34-65):** Degraded, investigate further
- **Poor (0-33):** Critical, immediate attention

---

### Step 2: Investigate Degraded Applications

For each application with a degraded or poor score, get the score trend to understand if this is a new or ongoing issue.

```text
zdx_get_application_score_trend(
  app_id="<app_id>",
  since=24
)
```text

**Interpret the trend:**

- **Sudden drop:** Likely an incident (server, network, or ISP issue)
- **Gradual decline:** Resource exhaustion, growing user base, or config drift
- **Intermittent spikes:** Unstable network path or periodic load spikes

Get application details for additional context:

```text
zdx_get_application(app_id="<app_id>")
```text

---

### Step 3: Drill Into Metrics

For each degraded application, check individual metrics to isolate the bottleneck.

**Page Fetch Time (overall web performance):**

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="pft"
)
```text

**DNS Resolution Time:**

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="dns"
)
```text

**Availability:**

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="availability"
)
```text

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

```text
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor"
)
```text

**Users with okay scores (borderline):**

```text
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="okay"
)
```text

**Filter by location to scope the impact:**

```text
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor",
  location_id=["<location_id>"]
)
```text

**For a specific user, get detailed experience data:**

```text
zdx_get_application_user(
  app_id="<app_id>",
  user_id="<user_id>"
)
```text

---

### Step 5: Cross-Reference with Alerts

Check if any active alerts correlate with the degraded applications.

```text
zdx_list_alerts(since=24)
```text

For relevant alerts:

```text
zdx_get_alert(alert_id="<alert_id>")
zdx_list_alert_affected_devices(alert_id="<alert_id>")
```text

---

### Step 6: Present Application Health Report

Assemble the `__ZDX_DATA__` payload defined in the *Data Payload Contract* and render it through `./templates/report.html.template` (see the **HTML OUTPUT** section). The template already produces the application table, KPI cards, color coding, search/sort, and CSV export — do **not** hand-author any HTML or markdown table here.

What you DO write is the `analysis` block inside the payload. **Do not skip it.** This is what makes the report useful:

- **`analysis.summary`** (3–5 sentences): overall health posture — how many apps are good vs. okay vs. poor, the dominant bottleneck pattern across degraded apps, and whether this is a localized or organization-wide degradation.
- **`analysis.rootCause`** (1–3 sentences per degraded app): state the primary bottleneck metric and what it indicates (e.g., "Microsoft 365 PFT at 12.4s indicates server-side or CDN latency, not DNS or network"). Quote the numbers from the metric calls in Steps 2–3.
- **`analysis.remediation`** (4–6 items): label each with a priority bucket and a concrete action.

| Priority | Apply to | Action |
|---|---|---|
| `Immediate` | Apps with score 0–33 | Check service health dashboards, ISP paths, and Zscaler cloud path. Engage the application vendor if server-side. |
| `Investigate` | Apps with score 34–65 | If declining, drill into the bottleneck metric. If stable, suspect a capacity or configuration issue. |
| `Monitor` | Borderline apps (score 66–70) | Proactive monitoring. No action unless score drops below 66 within 24h. |
| `Communicate` | Apps with the highest user impact | Notify affected user list; route to the application team with the metric evidence. |

---

## Filtering Strategies

### By Location

Useful for investigating office-specific issues.

```text
zdx_list_applications(location_id=["<location_id>"])
zdx_get_application_score_trend(app_id="<app_id>", location_id=["<location_id>"])
zdx_get_application_metric(app_id="<app_id>", metric_name="pft", location_id=["<location_id>"])
```text

### By Department

Useful for understanding impact on specific business units.

```text
zdx_list_applications(department_id=["<dept_id>"])
zdx_list_application_users(app_id="<app_id>", department_id=["<dept_id>"])
```text

### By Geolocation

Useful for regional analysis.

```text
zdx_list_applications(geo_id=["<geo_id>"])
```text

### By Time Window

Adjust `since` (hours) for different investigation windows:

- `since=2` -- current issues (default)
- `since=4` -- recent trends
- `since=24` -- daily overview
- `since=168` -- weekly review

---

## Edge Cases

### No Degraded Applications

```text
All 12 monitored applications are healthy (score > 66).

Top performers:
1. GitHub (94)
2. Zoom (92)
3. Box (91)

No action required. Consider reviewing alert thresholds
if you want earlier notification of potential issues.
```text

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
