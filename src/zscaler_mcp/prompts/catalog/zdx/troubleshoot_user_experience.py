"""ZDX prompt: troubleshoot a user's digital experience.

A user-invokable playbook (the MCP Prompts capability) that turns the
``zdx-troubleshoot-user-experience`` skill into a guided, parameterized workflow.
The client renders the function's parameters as the "Enter prompt inputs" form;
on submit, the rendered text seeds the conversation and the agent drives the
read-only ZDX tools (``zdx_list_devices`` → scores → metrics → alerts → deep
trace) to localize the bottleneck.

All inputs are strings (MCP prompt arguments are string-typed), keeping the
wizard clean. ``since_hours`` maps to the ZDX ``since`` parameter, which is a
lookback window in HOURS (not a timestamp).
"""

from __future__ import annotations

from zscaler_mcp.prompts import prompt

__all__ = ["troubleshoot_user_experience"]


@prompt(
    name="zdx_troubleshoot_user_experience",
    title="ZDX: Troubleshoot User Experience",
    service="zdx",
)
def troubleshoot_user_experience(
    user_or_device: str,
    application: str = "",
    since_hours: str = "24",
) -> str:
    """Troubleshoot a user's ZDX digital experience: device health, application
    score trend, network-path metrics, and active alerts, to localize whether a
    slowdown is on the device, the network, or the application server.

    Args:
        user_or_device: The user's name/email or the device hostname to
            investigate (used as the ``search`` term for ``zdx_list_devices``).
        application: Optional application name to focus on (e.g. "Microsoft 365",
            "Salesforce"). Leave empty to triage across all monitored apps.
        since_hours: Lookback window in HOURS for ZDX queries (the ``since``
            parameter). Defaults to 24.
    """
    app_line = (
        f'Focus on the application: "{application}".'
        if application.strip()
        else "No specific application was given — triage across all monitored applications "
        "and call out the worst-scoring one(s)."
    )

    return f"""\
You are a Zscaler Digital Experience (ZDX) expert. Troubleshoot the digital
experience for **{user_or_device}** over the last **{since_hours} hours** and
produce a clear root-cause diagnosis.

{app_line}

Important ZDX facts:
- The `since` parameter is in HOURS, not a timestamp. Use since={since_hours} on
  every ZDX query that accepts it.
- ZDX is read-only. Do not attempt writes unless you reach Step 5 AND the user
  explicitly asks to start a deep trace (which requires write tools to be enabled).
- Score bands: 80-100 = Good, 50-79 = Degraded, 0-49 = Poor.
- Pass all IDs as strings.

Follow this workflow, narrating findings in plain language (not tool plumbing):

Step 1 — Find the device
- `zdx_list_devices(search="{user_or_device}")` to locate the device. Note its
  device id, OS, ZDX agent version, and last-active time. If several devices
  match, ask which one (or pick the most recently active and say so).
- `zdx_get_device(device_id=...)` for device-level health (CPU, memory, disk,
  network adapter, ZCC tunnel status).

Step 2 — Application experience scores
- `zdx_list_applications()` to see monitored apps and current scores.
- For the affected app: `zdx_get_application_score_trend(app_id=...)` and
  `zdx_get_application(app_id=...)`. Note whether the score is steady-low or
  fluctuating (intermittent).

Step 3 — Isolate the bottleneck
- Pull each metric with `zdx_get_application_metric(app_id=..., metric_name=...)`
  for: dns_time (<50ms), tcp_connect_time (<100ms), ssl_handshake_time (<150ms),
  server_response_time (<500ms), page_load_time (<3000ms).
- Map the worst offender to a layer: high DNS → resolver; high TCP → network
  path; high SSL → cert/server load; high server response → app server; high
  page load → client rendering.

Step 4 — Scope: one user or many?
- `zdx_list_alerts()`; if an alert matches the app, `zdx_get_alert(alert_id=...)`
  and `zdx_list_alert_affected_devices(alert_id=...)` to tell isolated-vs-
  widespread. `zdx_list_historical_alerts()` for recurring patterns.

Step 5 — Deep trace (only if needed)
- `zdx_list_device_deep_traces(device_id=...)`. If a trace exists, analyze it via
  the `zdx_get_device_deep_trace`, `zdx_get_deeptrace_webprobe_metrics`,
  `zdx_get_deeptrace_cloudpath`(_metrics), `zdx_get_deeptrace_health_metrics`,
  `zdx_list_deeptrace_top_processes`, and `zdx_get_deeptrace_events` tools.
- If NO trace exists and the metrics point at the network, offer to start one
  (only if write tools are enabled): discover probe ids with `zdx_get_web_probes`
  / `zdx_list_cloudpath_probes`, then `zdx_start_deeptrace(...)`.

Deliver a diagnosis with three parts:
1. Summary — which metric(s) are out of range and by how much (quote numbers).
2. Root cause — the dominant bottleneck and what it points to; cite any alert
   correlation and whether the issue is isolated or shared.
3. Remediation — 3-6 concrete, prioritized actions (Immediate / Investigate /
   Monitor / Communicate).

If no ZDX data exists for {user_or_device}, stop and report that ZDX may not be
monitoring this device (check the ZCC profile) rather than guessing.
"""
