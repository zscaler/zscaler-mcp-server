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

**All tables are rendered by the HTML template, not by hand.** Do not author `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, or `<td>` markup in your reply or in the report. You produce a JSON payload (see *Data Payload Contract*) and the template at `./templates/report.html.template` turns it into the styled, sortable, exportable tables shown in `./example/report.example.html`.

After each table, provide:

1. **Detailed analysis** explaining the performance differences between locations and what they indicate
2. **Root cause identification** for underperforming locations (DNS, ISP, WiFi, device fleet age, etc.)
3. **Next steps / resolution** with site-specific remediation actions prioritized by impact and feasibility

Use color-coded rows based on location ranking:

- Green: Top-performing locations (score 66-100)
- Yellow: Borderline locations (score 34-65)
- Red: Worst-performing locations (score 0-33)

## ⚠ HTML OUTPUT — READ THIS BEFORE PRODUCING ANY HTML

There is exactly one acceptable way to produce the HTML output:

1. **Read the template from disk** — do NOT inline a copy in your response. The template lives next to this SKILL.md inside the skill's package, at:

   ```text
   ./templates/report.html.template
   ```

   The `./` prefix is intentional: this path is **relative to the skill folder** (the directory containing this SKILL.md), **never** an absolute path. Most agents that load skills from an uploaded `.zip` extract the package into a working directory and expose its contents via that relative path — read the file by joining the skill's own root directory with `./templates/report.html.template`. Do not rewrite this to an absolute path that points at the author's machine.

2. **Build a single JSON object** (`__ZDX_DATA__` payload) shaped exactly as documented in the *Data Payload Contract* section below. Aggregate the responses from the ZDX MCP tool calls (Steps 1–7 of the *Workflow*) into that object.

3. **Replace** the literal token `__ZDX_DATA__` (which appears once, inside `<script type="application/json" id="zdx-data">__ZDX_DATA__</script>`) with the JSON object. Do not edit any other part of the template.

4. **Write** the result to disk as `location_comparison_report_<YYYYMMDD-HHMMSS>.html` next to the .docx, and give the user a `computer://` link to it.

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
    "totalLocations": "<int>",
    "bestLocation": "<location name>",
    "worstLocation": "<location name>",
    "avgScore": "<int, 0-100>",
    "alertCount": "<int>"
  },
  "tables": {
    "locations": [
      {
        "severity": "critical | warning | good",
        "rank": "<int>",
        "name": "<location name>",
        "score": "<0-100>",
        "pft": "<page fetch time, e.g. '1.8s'>",
        "dns": "<dns time, e.g. '18ms'>",
        "availability": "<percentage, e.g. '100%'>",
        "poorUsers": "<e.g. '0/120'>",
        "alerts": "<int>"
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

Map each row's `severity` from its tier: top (score ≥ 80) → `good`, borderline (50–79) → `warning`, poor (< 50) → `critical`.

## Output Artifacts — MANDATORY

You MUST generate BOTH files below. Both are REQUIRED output for every location comparison.

### 1. Word Document (.docx) — REQUIRED

Write a Word document to disk named `location_comparison_report_<YYYYMMDD-HHMMSS>.docx` containing:

- Executive summary with best/worst performing locations
- Location ranking table (rank, location, score, PFT, DNS, availability, poor users, alerts)
- Per-location analysis for underperforming sites with metric breakdowns
- Root cause analysis for worst performers (DNS, ISP, WiFi, device fleet)
- Cross-location metric comparison for each application
- Site-specific remediation actions prioritized by impact

### 2. Interactive HTML Web Page (.html) — REQUIRED

Generated by the template-substitution flow described in the **HTML OUTPUT** section above. Filename: `location_comparison_report_<YYYYMMDD-HHMMSS>.html`. Do not hand-author HTML or CSS — the template ships everything the report needs.

---

## Workflow

### Step 1: List Available Locations and Departments

First, enumerate the organizational dimensions available for comparison.

**List locations:**

```text
zdx_list_locations()
```text

**List departments:**

```text
zdx_list_departments()
```text

Note the IDs returned -- these are used as filters in subsequent calls.

---

### Step 2: Compare Application Scores Across Locations

For each application of interest, retrieve scores filtered by different locations.

**Location A:**

```text
zdx_list_applications(location_id=["<location_a_id>"], since=24)
```text

**Location B:**

```text
zdx_list_applications(location_id=["<location_b_id>"], since=24)
```text

**Location C:**

```text
zdx_list_applications(location_id=["<location_c_id>"], since=24)
```text

Compile the scores side by side to identify which locations are underperforming.

---

### Step 3: Drill Into Score Trends for Underperforming Locations

For the worst-performing location, check the score trend.

```text
zdx_get_application_score_trend(
  app_id="<app_id>",
  location_id=["<worst_location_id>"],
  since=24
)
```text

Compare with a healthy location:

```text
zdx_get_application_score_trend(
  app_id="<app_id>",
  location_id=["<healthy_location_id>"],
  since=24
)
```text

**What to look for:**

- Does the underperforming location show a consistent low score or a sudden drop?
- Does the score correlate with specific times of day (peak hours)?
- Are multiple applications affected at this location, or just one?

---

### Step 4: Compare Metrics Across Locations

Drill into metrics for the specific application at each location.

**Page Fetch Time by location:**

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="pft",
  location_id=["<location_a_id>"]
)
```text

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="pft",
  location_id=["<location_b_id>"]
)
```text

**DNS by location:**

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="dns",
  location_id=["<location_a_id>"]
)
```text

**Availability by location:**

```text
zdx_get_application_metric(
  app_id="<app_id>",
  metric_name="availability",
  location_id=["<location_a_id>"]
)
```text

---

### Step 5: Compare Impacted Users by Location

Understand user impact at each location.

```text
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor",
  location_id=["<worst_location_id>"]
)
```text

```text
zdx_list_application_users(
  app_id="<app_id>",
  score_bucket="poor",
  location_id=["<healthy_location_id>"]
)
```text

**Calculate impact ratios:** If Location A has 5 poor users out of 50 total (10%) vs Location B with 25 poor users out of 100 total (25%), Location B has a more severe issue despite Location A having fewer total users.

---

### Step 6: Check Location-Specific Alerts

```text
zdx_list_alerts(location_id=["<worst_location_id>"], since=48)
```text

```text
zdx_list_historical_alerts(location_id=["<worst_location_id>"], since=168)
```text

Recurring alerts at a specific location indicate a persistent infrastructure issue at that site.

---

### Step 7: Assess Device Health at Underperforming Locations

Check if the issue is device-related rather than network-related.

```text
zdx_list_devices(location_id=["<worst_location_id>"])
```text

For specific devices showing issues:

```text
zdx_get_device(device_id="<device_id>")
```text

Check for:

- High CPU/memory usage across many devices (hardware refresh needed)
- Outdated ZCC agent versions
- WiFi issues (common in specific offices)

---

### Step 8: Present Comparison Report

Assemble the `__ZDX_DATA__` payload defined in the *Data Payload Contract* and render it through `./templates/report.html.template` (see the **HTML OUTPUT** section). The template already produces the location ranking table, KPI cards, color coding by tier, search/sort, and CSV export — do **not** hand-author any HTML or markdown table here.

What you DO write is the `analysis` block inside the payload. **Do not skip it.** This is what makes the comparison useful:

- **`analysis.summary`** (3–5 sentences): rank the locations and call out the gap between best and worst. Quote concrete numbers from the metric calls in Steps 2–4 (e.g., *"Dallas is the clear outlier with a score of 42, significantly below the org average of 75. DNS resolution at 180ms is 4× the average of other locations (28ms), which is cascading into elevated Page Fetch Times."*).
- **`analysis.rootCause`** (2–4 sentences for each worst performer): identify the dominant bottleneck (DNS, ISP, WiFi, device fleet) using the historical alert pattern (Step 6) and device health (Step 7) as evidence.
- **`analysis.remediation`** (4–6 items): label each with a priority bucket and a concrete action.

| Priority | Apply to | Action |
|---|---|---|
| `Immediate` | Worst performer(s) (score < 50) | Investigate the bottleneck metric. If DNS, check local resolver health and consider a redundant DNS provider. If ISP, open a ticket with the carrier with timestamps. |
| `Investigate` | Borderline locations (score 50–79) | Compare against healthy peers; track active alerts. Escalate if score drops further within 24h. |
| `Monitor` | Healthy locations on a downward trend | Add to weekly watchlist; verify no regional events are pending. |
| `Communicate` | All affected locations | Notify site IT contacts with the metric evidence and the expected remediation timeline. |

---

## Department Comparison Variant

The same workflow applies when comparing departments instead of locations.

```text
zdx_list_applications(department_id=["<dept_a_id>"], since=24)
zdx_list_applications(department_id=["<dept_b_id>"], since=24)
```text

**Department comparison is useful for:**

- Understanding if a specific team is disproportionately affected
- Compliance reporting (e.g., "How is the Finance team's experience?")
- Device fleet differences between departments (older hardware, different OS)

---

## Multi-Application Comparison

Compare how all applications perform at a single location.

```text
zdx_list_applications(location_id=["<location_id>"], since=24)
```text

If all applications are degraded at one location:

- The issue is likely network infrastructure (ISP, WiFi, LAN)
- Not application-specific

If only one application is degraded at a location:

- Likely application-specific routing or server issue for that region
- Check application CDN or server closest to that location

---

## Edge Cases

### Location with No Active Devices

```text
No active devices found at location "<location_name>" in the
requested time window. The office may be closed, or devices
may not be reporting.

Verify:
- Is the office operational?
- Are ZDX agents deployed at this location?
- Check the 'since' parameter (try a wider window)
```text

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
