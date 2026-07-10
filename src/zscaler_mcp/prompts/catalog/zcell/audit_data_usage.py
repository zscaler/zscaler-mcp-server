"""ZCell prompt: audit cellular data usage.

A user-invokable playbook (the MCP Prompts capability) that produces a read-only
data-usage audit for the Zscaler Cellular fleet: the tenant-wide status summary,
usage broken down by country / by day / by SIM, cross-referenced with data-cap
events, so an admin can spot top consumers, unexpected roaming spend, and
runaway trends. The agent drives the read-only ``zcell_*`` analytics tools.

All inputs are strings (MCP prompt arguments are string-typed). ``since_days``
maps to the ZCell ``days`` lookback window (a whole number of days, not a
timestamp).
"""

from __future__ import annotations

from zscaler_mcp.prompts import prompt

__all__ = ["audit_data_usage"]


@prompt(
    name="zcell_audit_data_usage",
    title="ZCell: Audit Data Usage",
    service="zcell",
)
def audit_data_usage(since_days: str = "30", country: str = "") -> str:
    """Audit Zscaler Cellular data usage across the fleet: tenant status summary,
    usage by country / day / SIM, and data-cap events — to surface top consumers,
    roaming spend, and trends over a window.

    Args:
        since_days: Lookback window in DAYS for the usage analytics (the ZCell
            ``days`` parameter). Defaults to 30.
        country: Optional country to focus the audit on (e.g. "US", "GB"). Leave
            empty to audit the whole fleet and rank countries.
    """
    country_line = (
        f'Focus the audit on country: "{country}". Filter breakdowns to it where '
        f"the tool allows and call out how it compares to the fleet total."
        if country.strip()
        else "No country was specified — audit the whole fleet and rank countries "
        "by usage, calling out the top spenders."
    )

    return f"""\
You are a Zscaler Cellular (ZCell) expert. Produce a data-usage audit for the
fleet over the last **{since_days} days**.

{country_line}

Important ZCell facts:
- Every tool is read-only and is scoped to the tenant via ZCELL_CUSTOMER_ID —
  you never pass a customer id.
- Time-bounded tools take a `days` lookback window (a whole number of days), not
  a timestamp. Use days={since_days} on every tool that accepts it.
- Usage values may be pre-formatted strings (e.g. "1.2 GB"); report them as
  returned and only compare magnitudes when the units line up.
- Empty results are authoritative — if a breakdown is empty, report it as "no
  usage recorded in this window" rather than retrying.

Follow this workflow, narrating findings in plain language (not tool plumbing):

Step 1 — Fleet snapshot
- `zcell_list_sim_analytics_summary()` for the current status mix (total /
  active / inactive SIMs). This frames the scale of the audit.

Step 2 — Usage by dimension
- `zcell_list_sim_usage_by_country(days={since_days})` — rank countries by usage.
  This is where unexpected roaming spend shows up.
- `zcell_list_sim_usage_by_day(days={since_days})` — the daily trend. Note spikes
  and whether usage is flat, growing, or bursty.
- `zcell_list_sim_usage_by_sim(days={since_days})` — the per-SIM leaderboard.
  Identify the top consumers (highest usage ICCIDs).

Step 3 — Correlate with caps and events
- For the top consumers (and any surprising country), pull recent events with
  `zcell_list_network_events(days={since_days}, ...)` filtered to the relevant
  ICCID or country, and flag any `data_cap_reached=true`, roaming (unexpected
  operator/country), or RAT-downgrade events.

Deliver an audit report with:
1. Snapshot — SIM status mix and total usage for the window.
2. Top consumers — the highest-usage SIMs (ICCID + usage) and top countries,
   quoting the numbers.
3. Anomalies — roaming spend, SIMs that hit their cap, and any sharp daily
   spikes, with the dates/ICCIDs involved.
4. Recommendations — 2-5 concrete actions (e.g. review plans for the top N SIMs,
   investigate roaming in country X, set/adjust caps).

If the usage breakdowns are all empty for this window, stop and report that no
cellular usage was recorded in the last {since_days} days (the feature may be
newly enabled or the SIMs idle) rather than guessing.
"""
