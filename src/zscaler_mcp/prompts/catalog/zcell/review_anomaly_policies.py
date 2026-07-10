"""ZCell prompt: review anomaly / geofence policies.

A user-invokable playbook (the MCP Prompts capability) that produces a read-only
posture review of the Zscaler Cellular anomaly policies (geofencing and other
anomaly types): which policies exist, whether they are running, how many
violations each has generated in the window, which SIM location groups they
watch, and which ICCIDs are offending. The agent drives the read-only
``zcell_*`` policy + location-group tools.

All inputs are strings (MCP prompt arguments are string-typed). ``since_days``
maps to the ZCell ``days`` lookback window (a whole number of days, not a
timestamp).
"""

from __future__ import annotations

from zscaler_mcp.prompts import prompt

__all__ = ["review_anomaly_policies"]


@prompt(
    name="zcell_review_anomaly_policies",
    title="ZCell: Review Anomaly Policies",
    service="zcell",
)
def review_anomaly_policies(since_days: str = "30", policy_type: str = "") -> str:
    """Review Zscaler Cellular anomaly/geofence policies: their run state, the
    location groups they watch, and the violations (and offending SIMs) they have
    generated over a window — a posture check on cellular anomaly detection.

    Args:
        since_days: Lookback window in DAYS for violations/logs (the ZCell
            ``days`` parameter). Defaults to 30.
        policy_type: Optional policy type to focus on (e.g. "GEOFENCING"). Leave
            empty to review all anomaly policy types.
    """
    type_line = (
        f'Focus on policies of type "{policy_type}" (pass policy_type="{policy_type}" '
        f"to zcell_list_anomaly_policies)."
        if policy_type.strip()
        else "No policy type was specified — review all anomaly policy types and "
        "group your findings by type."
    )

    return f"""\
You are a Zscaler Cellular (ZCell) expert. Review the tenant's cellular anomaly
policies and their violations over the last **{since_days} days**, and assess the
detection posture.

{type_line}

Important ZCell facts:
- Every tool is read-only and is scoped to the tenant via ZCELL_CUSTOMER_ID —
  you never pass a customer id.
- Time-bounded tools take a `days` lookback window (a whole number of days), not
  a timestamp. Use days={since_days} on every tool that accepts it.
- Pass all IDs (policy ids, group ids, ICCIDs) as strings.
- GEOFENCING policies reference one or more SIM location groups via
  `sim_location_group_ids`; the group holds the actual fence definition.
- Empty results are authoritative — a policy with zero violations is a finding
  (it may be working, or it may be watching nothing), not a reason to retry.

Follow this workflow, narrating findings in plain language (not tool plumbing):

Step 1 — Inventory the policies
- `zcell_list_anomaly_policies(days={since_days}{', policy_type="' + policy_type + '"' if policy_type.strip() else ""})`.
  For each policy note: id, name, type, enabled, running status, its
  sim_location_group_ids, and the violation count if reported.

Step 2 — Location-group context (geofencing)
- For each GEOFENCING policy, `zcell_get_sim_location_group(group_id=<id>)` for
  every referenced group: the fence definition, the linked policies, and which
  ICCIDs are inside/tracked. Flag groups that track zero devices.

Step 3 — Violations
- For each policy, `zcell_list_anomaly_policy_violations(policy_id=<id>, days={since_days})`
  to get the offending ICCIDs, and `zcell_list_anomaly_policy_logs(policy_id=<id>)`
  for the policy's recent enable/disable/run activity.
- For a hot policy, drill into a specific offender with
  `zcell_list_iccid_violations(policy_id=<id>, iccid=<iccid>, days={since_days})`
  to see the individual violation events (event_type + timestamps).

Deliver a posture review with:
1. Inventory — the policies (id, name, type, run state) and what each watches.
2. Coverage gaps — disabled or non-running policies, and location groups that
   track zero devices (a fence watching nothing).
3. Violations — the noisiest policies and top offending ICCIDs in the window,
   with counts and representative timestamps.
4. Recommendations — 2-5 concrete actions (e.g. enable a stopped policy, widen
   or tighten a fence, investigate the top offending SIMs, add tracked ICCIDs to
   an empty group).

If there are no anomaly policies configured, stop and report that the tenant has
no cellular anomaly detection in place rather than guessing.
"""
