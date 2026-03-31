# Cross-Product Troubleshooting Steering

## Overview

Many Zscaler issues span multiple services. A user connectivity problem might involve ZCC (agent status), ZDX (experience metrics), ZPA (private app access), and ZIA (internet access policies). This steering guide covers cross-product investigation workflows.

## When to Use Cross-Product Troubleshooting

- User reports "I can't access an application" (could be ZPA policy, ZIA block, ZCC issue, or network problem)
- User reports "everything is slow" (could be ZDX-measurable degradation, ZIA SSL inspection overhead, or ZPA path issues)
- Incident triage requires understanding the full picture across security and access layers

## Workflow: User Connectivity Troubleshooting

### Step 1 — Gather Issue Details
Ask the user for: username/email, affected application, error messages, when it started.

### Step 2 — Check ZCC Device Status
```
1. zcc_list_devices              → Find the user's device, check enrollment status
2. zcc_list_forwarding_profiles  → Verify traffic forwarding configuration
3. zcc_list_trusted_networks     → Check if user is on a trusted network (may bypass ZPA/ZIA)
```

### Step 3 — Check ZDX Experience Metrics
```
1. zdx_list_devices              → Find device in ZDX monitoring
2. zdx_get_device                → Get device health details
3. zdx_get_application           → Check app score (since=2 for last 2 hours)
4. zdx_get_application_score_trend → Look for score drops
5. zdx_get_application_metric    → Check DNS, TCP, SSL, PFT, server response metrics
6. zdx_list_alerts               → Check active alerts for this app/device
7. zdx_list_device_deep_traces   → Check for existing diagnostic sessions
```

### Step 3a — Deep Trace Diagnostics (if ZDX score is degraded/poor)
If a deep trace session exists, analyze its data for root cause:
```
1. zdx_get_device_deep_trace             → Get trace summary
2. zdx_get_deeptrace_webprobe_metrics    → DNS, TCP, SSL, HTTP times
3. zdx_get_deeptrace_cloudpath           → Hop-by-hop network path
4. zdx_get_deeptrace_cloudpath_metrics   → Per-hop latency, packet loss, jitter
5. zdx_get_deeptrace_health_metrics      → CPU, memory, disk, network utilization
6. zdx_list_deeptrace_top_processes      → Resource-heavy processes
7. zdx_get_deeptrace_events              → Zscaler, HW, SW, network changes
```
If no trace exists and network issues are suspected, discover probe IDs and start a new one (requires write tools):
```
zdx_get_web_probes(device_id="<id>", app_id="<app_id>")
zdx_list_cloudpath_probes(device_id="<id>", app_id="<app_id>")
zdx_start_deeptrace(device_id="<id>", session_name="Troubleshoot-<user>", app_id=<app_id>, web_probe_id=<id>, cloudpath_probe_id=<id>, session_length_minutes=15, probe_device=True)
```

### Step 4 — Check ZPA Configuration (for private applications)
```
1. zpa_list_application_segments → Find the target application segment
2. zpa_get_application_segment   → Verify domains, ports, server group assignment
3. zpa_list_access_policy_rules  → Check if user's identity matches an allow rule
4. zpa_list_app_connector_groups → Verify connector health and location
5. zpa_list_server_groups        → Confirm server group has healthy connectors
```

### Step 5 — Check ZIA Configuration (for internet/SaaS applications)
```
1. zia_list_url_filtering_rules  → Check if URL is blocked by policy
2. zia_url_lookup                → Classify the target URL
3. zia_list_ssl_inspection_rules → Check if SSL inspection is interfering
4. zia_list_cloud_firewall_rules → Check firewall rules that may block traffic
5. zia_list_web_dlp_rules        → Check if DLP is blocking content
```

### Step 6 — Check for Broader Issues
```
1. zdx_list_alerts                    → Look for org-wide alerts (not just this user)
2. zdx_list_alert_affected_devices    → See how many devices are affected
3. zins_get_cyber_incidents      → Check for active security incidents
4. zins_get_web_traffic_by_location → Check traffic anomalies at user's location
```

### Step 7 — Present Diagnosis

Structure findings as:

1. **Affected User** — Username, device, location
2. **Symptoms** — What the user is experiencing
3. **Root Cause** — What layer the problem is at (ZCC agent, network, ZPA policy, ZIA policy, application server)
4. **Evidence** — ZDX scores, policy rule matches, connector status, error messages
5. **Recommended Action** — Specific fix (policy change, connector restart, network investigation)

## Common Root Causes by Layer

| Layer | Symptoms | Tools to Check |
|-------|----------|----------------|
| **ZCC Agent** | No connectivity at all | `zcc_list_devices` — check enrollment status |
| **Network/DNS** | Slow or intermittent access | `zdx_get_application_metric` — check DNS, TCP metrics; `zdx_get_deeptrace_webprobe_metrics` + `zdx_get_deeptrace_cloudpath` for detailed path analysis |
| **ZPA Policy** | "Access denied" to private app | `zpa_list_access_policy_rules` — verify user matches allow rule |
| **ZPA Connector** | Timeout to private app | `zpa_list_app_connector_groups` — check connector health |
| **ZIA URL Policy** | "Blocked" page for web/SaaS | `zia_url_lookup` + `zia_list_url_filtering_rules` |
| **ZIA SSL** | Certificate errors, broken pages | `zia_list_ssl_inspection_rules` — check DO_NOT_INSPECT rules |
| **ZIA DLP** | Upload/download blocked | `zia_list_web_dlp_rules` — check content inspection rules |
| **Application** | Server errors (5xx) | `zdx_get_application_metric` — check server response time |

## Best Practices

1. **Always start with ZDX** — ZDX metrics give the fastest signal about what layer is broken
2. **Check the simple things first** — ZCC enrollment status and trusted network config eliminate many issues
3. **Don't assume one layer** — A "slow app" could be DNS (network), SSL inspection (ZIA), or connector placement (ZPA)
4. **Use time correlation** — Ask when the problem started, then check ZDX score trends for that timeframe
5. **Scale check** — If one user is affected, it's likely policy/device specific. If many users are affected, check location-wide alerts and Z-Insights
