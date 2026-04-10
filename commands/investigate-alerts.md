---
disable-model-invocation: true
argument-hint: "[since_hours] [severity: all|critical|warning]"
description: "Investigate active and historical ZDX alerts to understand scope, root cause, and impact."
---

# Investigate ZDX Alerts

Investigate alerts: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Time window** in hours (default: 24)
- **Severity filter** (default: all)

## Step 2: List Active Alerts

```text
zdx_list_alerts(since=<hours>)
```text

## Step 3: For Each Alert, Investigate

For each active or recent alert:

```text
zdx_get_alert(alert_id="<id>")
```text

Note: alert type, severity, affected application, start time, end time (if resolved).

## Step 4: Check Affected Devices

```text
zdx_list_alert_affected_devices(alert_id="<id>")
```text

Determine scope: one user, one office, one ISP, or organization-wide.

## Step 5: Correlate with Application Metrics

For the affected application:

```text
zdx_get_application_score_trend(app_id="<app_id>", since=<hours>)
zdx_get_application_metric(app_id="<app_id>", metric_name="dns_time", since=<hours>)
```text

Check if metrics degraded around the alert start time.

## Step 6: Present Report

**ALWAYS present data in HTML tables** using `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling. Use color-coded rows: red (high priority), yellow (medium), green (low/resolved).

Include:

1. **Active alerts summary table** (priority, alert name, application, duration, affected devices, locations, bottleneck metric)
2. **Metric correlation table** per alert (PFT, DNS, availability, root cause indicator)
3. **Detailed analysis** explaining alert severity, scope (isolated vs widespread), and correlation between alerts
4. **Historical pattern analysis** -- is this recurring? What time patterns exist?
5. **Next steps / resolution** per alert:
   - High priority: immediate actions (check service health, ISP paths, engage vendor)
   - Medium priority: investigate specific bottleneck (DNS, network path)
   - Low priority: monitor, check for transient causes (deployments, maintenance)
   - Proactive: start a deep trace (`zdx_start_deeptrace`) for recurring alerts to capture detailed network path evidence, then analyze with `zdx_get_deeptrace_webprobe_metrics`, `zdx_get_deeptrace_cloudpath`, and `zdx_get_deeptrace_events`

## Step 7: Generate Downloadable Artifacts — MANDATORY

**You MUST create BOTH files. Do NOT skip the HTML page.**

1. **Word document** (`alert_investigation_report_<date>.docx`): Executive summary, active alerts table, metric correlation per alert, historical pattern analysis, per-alert root cause, prioritized remediation and escalation paths.

2. **Interactive HTML page** (`alert_investigation_report_<date>.html`): Use the complete HTML template from the `zdx-investigate-alerts` skill. The file must be fully functional with working search bar, sortable columns, filter dropdowns, color-coded rows, summary dashboard, and CSV export button. All CSS and JavaScript inline — no external dependencies. Populate the `<tbody>` with one `<tr>` per alert from the collected data.

**Write both files to disk and provide the file paths to the user.**
