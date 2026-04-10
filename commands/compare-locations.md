---
disable-model-invocation: true
argument-hint: "[application_name] [location1, location2, ...] [since_hours]"
description: "Compare digital experience across locations, departments, or geolocations using ZDX."
---

# Compare Location Experience

Compare locations: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Application** (optional -- compare across all apps)
- **Locations** to compare (optional -- compare all)
- **Time window** in hours (default: 24)

## Step 2: Get Application Scores by Location

```text
zdx_list_applications()
```text

For each application:

```text
zdx_get_application(app_id="<app_id>", since=<hours>)
```text

## Step 3: Break Down by Location/Department

```text
zdx_list_devices(app_id="<app_id>")
```text

Group devices by location and calculate average scores per location.

## Step 4: Investigate Outliers

For locations with significantly worse scores:

```text
zdx_get_application_metric(app_id="<app_id>", metric_name="dns_time", since=<hours>)
```text

Check key metrics to identify the bottleneck.

## Step 5: Check Location-Specific Alerts

```text
zdx_list_alerts(since=<hours>)
```text

Correlate alerts with location data.

## Step 6: Present Report

**ALWAYS present data in HTML tables** using `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling. Use color-coded rows: green (score 66-100), yellow (score 34-65), red (score 0-33).

Include:

1. **Location ranking table** (rank, location, score, PFT, DNS, availability, poor users, active alerts)
2. **Detailed analysis** explaining the performance differences between locations and what patterns they reveal
3. **Root cause** for the worst performer(s) -- what specific metric is the bottleneck and why it's location-specific
4. **Next steps / resolution** per location:
   - Critical locations: investigate DNS/ISP infrastructure, compare config with healthy sites
   - Borderline locations: monitor closely, review ISP paths
   - Healthy locations: no action, use as reference baseline for comparison

## Step 7: Generate Downloadable Artifacts — MANDATORY

**You MUST create BOTH files. Do NOT skip the HTML page.**

1. **Word document** (`location_comparison_report_<date>.docx`): Executive summary, location ranking table, per-location analysis for underperformers, root cause per site, cross-location metric comparison, site-specific remediation actions.

2. **Interactive HTML page** (`location_comparison_report_<date>.html`): Use the complete HTML template from the `zdx-compare-location-experience` skill. The file must be fully functional with working search bar, sortable columns, filter dropdowns, color-coded rows, summary dashboard, and CSV export button. All CSS and JavaScript inline — no external dependencies. Populate the `<tbody>` with one `<tr>` per location from the collected data.

**Write both files to disk and provide the file paths to the user.**
