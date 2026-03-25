---
disable-model-invocation: true
argument-hint: "<username_or_email> [application_name] [action: analyze|start|cleanup]"
description: "Run a ZDX deep trace diagnostics session — start, analyze, or clean up deep traces for a user's device."
---

# Deep Trace Diagnostics Session

Perform deep trace diagnostics for: **$ARGUMENTS**

## Step 1: Parse Input

Extract:
- **Username or email** (required)
- **Application name** (optional — if not provided, the session covers all monitored apps)
- **Action** (default: analyze)
  - `analyze` — Check existing traces and analyze results
  - `start` — Start a new diagnostics session (requires write tools)
  - `cleanup` — Delete completed/stale traces (requires write tools)

## Step 2: Find the User's Device

```
zdx_list_devices(search="<username>")
```

Note the `device_id`. If multiple devices, ask the user which one.

## Step 3: Check Existing Deep Traces

```
zdx_list_device_deep_traces(device_id="<device_id>")
```

Review existing sessions:
- **In Progress** sessions: Wait for completion or analyze partial data
- **Completed** sessions: Proceed to analysis
- **No sessions**: Offer to start a new one (requires write tools)

## Step 4: Start a New Session (if action=start)

Requires `--enable-write-tools`.

A diagnostics session can include Deep Tracing, Hi-Fi Cloud Path, Bandwidth Testing, or Packet Capture Probing. Through the MCP tools, we support Deep Tracing sessions.

First, discover the probe IDs for the target application:

```
zdx_get_web_probes(device_id="<device_id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<device_id>", app_id="<app_id>")
```

Then start the deep trace with all required IDs (all IDs must be integers):

```
zdx_start_deeptrace(
  device_id="<device_id>",
  session_name="Diag-<user>-<date>",
  app_id=<app_id>,                 (integer, from zdx_list_applications)
  web_probe_id=<probe_id>,         (integer, from zdx_get_web_probes)
  cloudpath_probe_id=<probe_id>,   (integer, from zdx_list_cloudpath_probes)
  session_length_minutes=15,       (5, 15, 30, or 60 minutes)
  probe_device=True                (collect device-level statistics)
)
```

Configuration guidance:
- **5 minutes**: Quick check for intermittent issues
- **15 minutes**: Standard diagnostics session (recommended default)
- **30 minutes**: Extended capture for hard-to-reproduce issues
- **60 minutes**: Long-running capture for periodic/scheduled issues

After starting, inform the user of the expected completion time.

## Step 5: Analyze Deep Trace Results

For a completed trace, collect all diagnostics data:

### 5a. Trace Summary
```
zdx_get_device_deep_trace(device_id="<device_id>", trace_id="<trace_id>")
```

### 5b. Web Probe Metrics
```
zdx_get_deeptrace_webprobe_metrics(device_id="<device_id>", trace_id="<trace_id>")
```
Check DNS resolution, TCP connect, SSL handshake, and HTTP response times. These indicate where application connectivity bottlenecks exist.

### 5c. Cloud Path Topology
```
zdx_get_deeptrace_cloudpath(device_id="<device_id>", trace_id="<trace_id>")
```
View the full hop-by-hop network path from the user's device to the application. Identify hops with high latency or that are unreachable.

### 5d. Cloud Path Metrics
```
zdx_get_deeptrace_cloudpath_metrics(device_id="<device_id>", trace_id="<trace_id>")
```
Check per-hop latency, packet loss percentage, and jitter. Spikes on specific hops isolate the network segment causing degradation.

### 5e. Device Health Metrics
```
zdx_get_deeptrace_health_metrics(device_id="<device_id>", trace_id="<trace_id>")
```
Check CPU utilization, memory usage, disk I/O, and network interface throughput. High resource usage indicates device-side performance problems.

### 5f. Top Processes
```
zdx_list_deeptrace_top_processes(device_id="<device_id>", trace_id="<trace_id>")
```
Identify processes consuming the most CPU and memory during the trace. Resource-heavy processes can explain device-level degradation.

### 5g. Events Timeline
```
zdx_get_deeptrace_events(device_id="<device_id>", trace_id="<trace_id>")
```
Review events that occurred during the trace window:
- **Zscaler events**: Policy changes, tunnel reconnections
- **Hardware events**: Driver changes, hardware failures
- **Software events**: Updates, installations, crashes
- **Network events**: Interface changes, connectivity drops

Correlate event timestamps with metric degradation to identify root cause.

## Step 6: Cleanup (if action=cleanup)

Requires `--enable-write-tools`.

```
zdx_delete_deeptrace(device_id="<device_id>", trace_id="<trace_id>")
```

This is a destructive operation. Confirm with the user before proceeding.

## Step 7: Present Diagnosis

**ALWAYS present data in HTML tables** using `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` tags with inline styling. Use color-coded rows: green for healthy, yellow for degraded, red for critical.

Include:
1. **Session summary table** (session name, type, user, device, status, start/end time, duration)
2. **Web probe metrics table** (DNS time, TCP connect, SSL handshake, HTTP response — each with value, threshold, and status)
3. **Cloud path table** (hop number, IP/hostname, latency, packet loss, jitter — color-coded by severity)
4. **Device health table** (CPU, memory, disk, network — with values and health status)
5. **Top processes table** (process name, CPU %, memory %, status)
6. **Events timeline** (timestamp, event type, description, correlated impact)
7. **Root cause analysis**: Identify the layer where the issue exists:
   - **Device**: High CPU/memory, resource-heavy processes
   - **Network**: Packet loss or latency on specific hops
   - **DNS**: Slow resolution affecting all applications
   - **Application**: High server response time with clean network path
   - **Configuration**: Correlated Zscaler policy or connector changes
8. **Remediation actions** prioritized by confidence level

## Step 8: Generate Downloadable Artifacts — MANDATORY

**You MUST create BOTH files. Do NOT skip the HTML page.**

1. **Word document** (`deep_trace_diagnosis_<date>.docx`): Session summary, all metrics tables, cloud path analysis, device health assessment, event correlation, root cause analysis, and prioritized remediation steps.

2. **Interactive HTML page** (`deep_trace_diagnosis_<date>.html`): Use the complete HTML template from the `zdx-diagnose-deeptrace` skill. The file must be fully functional with working search bar, sortable columns, filter dropdowns, color-coded rows, summary dashboard, and CSV export button. All CSS and JavaScript inline — no external dependencies. Populate the `<tbody>` with data from all deep trace metrics.

**Write both files to disk and provide the file paths to the user.**
