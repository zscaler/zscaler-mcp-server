---
disable-model-invocation: true
argument-hint: "<username_or_email> [application_name] [since_hours]"
description: "Troubleshoot a user's digital experience using ZDX scores, metrics, and network path data."
---

# Troubleshoot User Experience (ZDX)

Investigate experience for: **$ARGUMENTS**

## Step 1: Parse Input

Extract:
- **Username or email**
- **Application name** (optional -- investigate all if not provided)
- **Time window** in hours (default: 2, max: 168)

## Step 2: Find the User's Device

```
zdx_list_devices(search="<username>")
```

Note the `device_id`. If multiple devices, ask which one.

## Step 3: Get Device Details

```
zdx_get_device(device_id="<device_id>")
```

Check OS, ZCC version, location, department.

## Step 4: Check Application Scores

```
zdx_list_applications()
zdx_get_application(app_id="<app_id>", since=<hours>)
zdx_get_application_score_trend(app_id="<app_id>", since=<hours>)
```

Score interpretation:
- **66-100**: Good experience
- **34-65**: Degraded -- investigate further
- **0-33**: Poor -- significant issue

## Step 5: Drill Into Metrics

For degraded/poor scores:

```
zdx_get_application_metric(app_id="<app_id>", metric_name="dns_time", since=<hours>)
zdx_get_application_metric(app_id="<app_id>", metric_name="availability", since=<hours>)
```

Check: DNS time, TCP connect, SSL handshake, server response, page fetch time.

## Step 6: Check Alerts

```
zdx_list_alerts(since=<hours>)
```

If alerts exist for this user or application, investigate affected devices:

```
zdx_list_alert_affected_devices(alert_id="<id>")
```

## Step 7: Deep Trace Analysis

Check for existing deep trace sessions:

```
zdx_list_device_deep_traces(device_id="<device_id>")
```

If a deep trace exists, analyze its diagnostics data:

```
zdx_get_device_deep_trace(device_id="<device_id>", trace_id="<trace_id>")
zdx_list_deeptrace_top_processes(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_webprobe_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_health_metrics(device_id="<device_id>", trace_id="<trace_id>")
zdx_get_deeptrace_events(device_id="<device_id>", trace_id="<trace_id>")
```

If NO deep trace exists and metrics indicate network or connectivity issues, discover probe IDs and start a new diagnostics session (requires write tools enabled):

```
zdx_get_web_probes(device_id="<device_id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<device_id>", app_id="<app_id>")
zdx_start_deeptrace(device_id="<device_id>", session_name="Troubleshoot-<user>-<date>", app_id=<app_id>, web_probe_id=<id>, cloudpath_probe_id=<id>, session_length_minutes=15, probe_device=True)
```

### Deep Trace Analysis Checklist

- **Web probe metrics**: Check DNS resolution, TCP connect, SSL handshake, and HTTP response times. High values indicate network-layer or server-side issues.
- **Cloud path topology**: Review hop-by-hop path. Identify hops with high latency or packet loss that indicate ISP, firewall, or routing problems.
- **Cloud path metrics**: Check latency, packet loss, and jitter trends across the trace duration.
- **Health metrics**: Check CPU, memory, disk I/O, and network utilization. Device resource exhaustion can cause application-level degradation.
- **Top processes**: Identify resource-heavy processes competing for CPU/memory during the trace period.
- **Events**: Review Zscaler configuration changes, hardware/software updates, and network changes that correlate with issue onset.

## Step 8: Present Diagnosis

**ALWAYS present data in HTML tables** using `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling. Use color-coded rows: green for healthy metrics, yellow for degraded, red for critical.

Include:
1. **Device summary table** (user, device, OS, location, department, ZCC version)
2. **Metric breakdown table** (DNS, TCP connect, SSL, server response, page load -- each with current value, normal range, and status)
3. **Deep trace findings** (if available): web probe metrics, cloud path hops with latency/loss, health metrics, top processes, and correlated events
4. **Detailed analysis** explaining what the metrics indicate and where the bottleneck is
5. **Root cause** identification (client, network, ISP, or server)
6. **Next steps / resolution** with prioritized, actionable recommendations (e.g., "check server health", "start deep trace if not yet done", "verify ISP status", "check app connector health")

## Step 9: Generate Downloadable Artifacts — MANDATORY

**You MUST create BOTH files. Do NOT skip the HTML page.**

1. **Word document** (`user_experience_diagnosis_<date>.docx`): User/device summary, application scores, metric breakdown, root cause analysis, alert correlation, prioritized resolution steps.

2. **Interactive HTML page** (`user_experience_diagnosis_<date>.html`): Use the complete HTML template from the `zdx-troubleshoot-user-experience` skill. The file must be fully functional with working search bar, sortable columns, filter dropdowns, color-coded rows, summary dashboard, and CSV export button. All CSS and JavaScript inline — no external dependencies. Populate the `<tbody>` with one `<tr>` per metric from the collected data.

**Write both files to disk and provide the file paths to the user.**
