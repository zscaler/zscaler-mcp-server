"""ZCell prompt: investigate a single SIM.

A user-invokable playbook (the MCP Prompts capability) that turns an ICCID into a
guided, read-only triage across the Zscaler Cellular tools: SIM inventory record
→ recent network/session events → anomaly-policy violations → geofence context.
The client renders the parameters as the "Enter prompt inputs" form; on submit
the rendered text seeds the conversation and the agent drives the read-only
``zcell_*`` tools to localize why a SIM is offline, roaming, capped, or flagged.

All inputs are strings (MCP prompt arguments are string-typed). ``since_days``
maps to the ZCell ``days`` lookback window (a whole number of days, not a
timestamp).
"""

from __future__ import annotations

from zscaler_mcp.prompts import prompt

__all__ = ["investigate_sim"]


@prompt(
    name="zcell_investigate_sim",
    title="ZCell: Investigate a SIM",
    service="zcell",
)
def investigate_sim(iccid: str, since_days: str = "7") -> str:
    """Investigate one Zscaler Cellular SIM by ICCID: inventory record, recent
    network/session events, and any anomaly-policy (geofence) violations, to
    diagnose why a SIM is offline, roaming, data-capped, or flagged.

    Args:
        iccid: The ICCID of the SIM to investigate (passed as a string).
        since_days: Lookback window in DAYS for the event/violation history
            (the ZCell ``days`` parameter). Defaults to 7.
    """
    return f"""\
You are a Zscaler Cellular (ZCell) expert. Investigate the SIM with ICCID
**{iccid}** over the last **{since_days} days** and produce a clear diagnosis of
its current state and any problems.

Important ZCell facts:
- Every tool is read-only and is scoped to the tenant via ZCELL_CUSTOMER_ID —
  you never pass a customer id.
- Time-bounded tools take a `days` lookback window (a whole number of days), not
  a timestamp. Use days={since_days} on every tool that accepts it.
- Pass all IDs (ICCIDs, policy ids) as strings.
- Empty results are authoritative. If a search returns nothing, say so — do not
  retry with split keywords or a wider window "to double-check".

Follow this workflow, narrating findings in plain language (not tool plumbing):

Step 1 — The SIM record
- `zcell_get_sim_details(icc_id="{iccid}")` for the full record. Note: status,
  network_status, last-seen country + operator (location_country / location_mno),
  APN, assigned IP(s), device (brand/model/form factor), tags, and current usage.
- Classify the SIM immediately: is it active + attached, inactive, or attached in
  an unexpected country/operator (possible roaming)?

Step 2 — Recent activity
- `zcell_list_network_events(days={since_days}, filter_by=[{{"filterName": "iccid", "operator": "EQ", "values": ["{iccid}"]}}])`
  to pull this SIM's session/network events. Look at event_name, outcome, country,
  operator_name, rat_type, and data_cap_reached across the window.
- Call out failed outcomes, operator/country changes (roaming), RAT downgrades,
  and any `data_cap_reached=true` events.

Step 3 — Anomaly / geofence violations
- `zcell_list_anomaly_policies(days={since_days})` to see the configured policies
  (note GEOFENCING policies and their sim_location_group_ids).
- For each relevant policy id, `zcell_list_iccid_violations(policy_id=<id>, iccid="{iccid}", days={since_days})`
  to see whether THIS SIM violated it (e.g. left a geofence). Note event_type and
  timestamps.
- If a geofence policy is involved, `zcell_get_sim_location_group(group_id=<id>)`
  for the fence definition and whether this ICCID is inside/tracked.

Deliver a diagnosis with three parts:
1. State — the SIM's current status, attachment, location/operator, and usage
   (quote the actual values).
2. Findings — the notable events and any policy violations in the window, with
   timestamps; whether behavior looks normal, roaming, capped, or out-of-fence.
3. Next steps — 2-5 concrete, prioritized actions (e.g. verify expected country,
   review the geofence, check the data plan, confirm device pairing).

If `zcell_get_sim_details` returns nothing for {iccid}, stop and report that no
SIM with that ICCID exists in this tenant rather than guessing.
"""
