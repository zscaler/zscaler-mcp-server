---
disable-model-invocation: true
argument-hint: "<username_or_email> [application_or_url] [symptom]"
description: "Cross-product troubleshooting of user connectivity across ZCC, ZDX, ZPA, and ZIA."
---

# Troubleshoot User Connectivity

Perform end-to-end troubleshooting for user: **$ARGUMENTS**

Follow this systematic workflow:

## Step 1: Parse Input

Extract from the arguments:
- **User identifier** (name or email)
- **Application or URL** (if provided)
- **Symptom** (cannot connect, slow, intermittent, access denied)

If any required information is missing, ask the administrator.

## Step 2: ZCC Client Status

```
zcc_list_devices(search="<user>")
```

Check enrollment status, ZCC version, last seen time. Verify traffic is being forwarded:

```
zcc_list_forwarding_profiles()
zcc_list_trusted_networks()
```

## Step 3: ZDX Digital Experience

```
zdx_list_devices(search="<user>")
zdx_get_device(device_id="<id>")
zdx_list_applications()
zdx_get_application_score_trend(app_id="<id>")
zdx_list_alerts()
```

Evaluate: Score > 80 = good, 50-80 = degraded, < 50 = poor. Check DNS time, TCP connect time, server response time.

### Step 3a: Deep Trace Diagnostics (if score is degraded/poor)

Check for existing deep trace sessions and analyze or start a new one:

```
zdx_list_device_deep_traces(device_id="<id>")
```

If a trace exists, analyze the diagnostics data:

```
zdx_get_device_deep_trace(device_id="<id>", trace_id="<trace_id>")
zdx_get_deeptrace_webprobe_metrics(device_id="<id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath(device_id="<id>", trace_id="<trace_id>")
zdx_get_deeptrace_cloudpath_metrics(device_id="<id>", trace_id="<trace_id>")
zdx_get_deeptrace_health_metrics(device_id="<id>", trace_id="<trace_id>")
zdx_list_deeptrace_top_processes(device_id="<id>", trace_id="<trace_id>")
zdx_get_deeptrace_events(device_id="<id>", trace_id="<trace_id>")
```

If no trace exists and the symptom suggests network issues, discover probe IDs and start one (requires write tools):

```
zdx_get_web_probes(device_id="<id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<id>", app_id="<app_id>")
zdx_start_deeptrace(device_id="<id>", session_name="Cross-Product-<user>-<date>", app_id=<app_id>, web_probe_id=<id>, cloudpath_probe_id=<id>, session_length_minutes=15, probe_device=True)
```

Use deep trace findings to narrow down: is the issue at the device (CPU/memory), network (cloud path hops), DNS, or application layer?

## Step 4: ZPA (Private Apps)

```
zpa_list_application_segments()
zpa_get_application_segment(segment_id="<id>")
zpa_get_server_group(group_id="<id>")
zpa_get_app_connector_group(group_id="<id>")
zpa_list_access_policy_rules()
```

Verify app segment exists, is enabled, connectors are healthy, and user has an ALLOW rule.

## Step 5: ZIA (Internet Apps)

```
zia_url_lookup(urls=["<url>"])
zia_list_url_filtering_rules()
zia_list_ssl_inspection_rules()
zia_list_cloud_firewall_rules()
zia_get_activation_status()
```

Evaluate URL filtering, SSL inspection, and firewall rules in priority order.

## Step 6: Broader Impact

Check if multiple users affected via ZDX alerts. Check ZIA activation status for pending changes.

## Step 7: Present Report

Provide a structured diagnosis report with: user details, device status, experience scores, configuration findings, root cause, and recommended actions. Prioritize findings as [LIKELY], [POSSIBLE], [UNLIKELY].
