---
disable-model-invocation: true
argument-hint: "[application_name] [since_hours]"
description: "Analyze application health across the organization using ZDX scores and metrics."
---

# Analyze Application Health

Analyze health for: **$ARGUMENTS**

## Step 1: Parse Input

Extract:
- **Application name** (optional -- analyze all monitored apps if not provided)
- **Time window** in hours (default: 2)

## Step 2: List Monitored Applications

```
zdx_list_applications()
```

## Step 3: Get Scores for Each Application

For each application (or the specified one):

```
zdx_get_application(app_id="<app_id>", since=<hours>)
zdx_get_application_score_trend(app_id="<app_id>", since=<hours>)
```

## Step 4: Investigate Degraded Applications

For any application with score < 66:

```
zdx_get_application_metric(app_id="<app_id>", metric_name="dns_time", since=<hours>)
zdx_get_application_metric(app_id="<app_id>", metric_name="availability", since=<hours>)
```

Identify the metric causing degradation.

## Step 5: Check Most Impacted Users

```
zdx_list_devices(app_id="<app_id>")
```

## Step 6: Present Report

**ALWAYS present data in HTML tables** using `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling. Use color-coded rows: green (score 66-100), yellow (score 34-65), red (score 0-33).

Include:
1. **Application health overview table** (app name, score, status, PFT, DNS, availability, impacted users, bottleneck)
2. **Detailed analysis** for each degraded/poor application explaining what the bottleneck metric indicates
3. **Root cause** per degraded app (DNS resolver, server-side, CDN, ISP, etc.)
4. **Next steps / resolution** prioritized by user impact count:
   - Critical apps: immediate investigation, check service health, engage vendor
   - Degraded apps: monitor trend, investigate bottleneck metric, check ISP paths
   - Healthy apps: no action, note any borderline (66-70) for proactive monitoring

## Step 7: Generate Downloadable Artifacts — MANDATORY

**You MUST create BOTH files. Do NOT skip the HTML page.**

1. **Word document** (`application_health_report_<date>.docx`): Executive summary, application health table, per-app deep dive for degraded apps, root cause analysis, user impact breakdown, prioritized remediation actions.

2. **Interactive HTML page** (`application_health_report_<date>.html`): Use the complete HTML template from the `zdx-analyze-application-health` skill. The file must be fully functional with working search bar, sortable columns, filter dropdowns, color-coded rows, summary dashboard, and CSV export button. All CSS and JavaScript inline — no external dependencies. Populate the `<tbody>` with one `<tr>` per application from the collected data.

**Write both files to disk and provide the file paths to the user.**
