---
name: zia-manage-time-interval
description: "Find an existing ZIA Time Interval by name, or create a new one when no match exists, then return the interval ID so the caller can attach it to a policy rule via its `time_windows` field. Time Intervals are reusable schedule objects (start time, end time, days of the week) that ZIA Cloud Firewall Filtering, URL Filtering, Cloud App Control, File Type Control, and Sandbox rules reference to enforce recurring time-of-day / day-of-week schedules (e.g. 'only between 8am-5pm Monday-Friday'). Note: SSL Inspection rules do NOT support `time_windows` and cannot consume the output of this skill. Use when an admin asks for 'a schedule', 'business hours', 'after-hours', 'weekends only', 'time window', 'time interval', or any rule that should fire on a recurring time pattern. Other ZIA rule-creation skills chain to this one when the admin's request includes a schedule."
---

# ZIA: Manage Time Interval (find-or-create)

## How to talk to the admin

- Don't narrate tool calls, search filters, or internal lookup logic. Just confirm what was found or created.
- Empty search results are authoritative — if `zia_list_time_intervals(search="<name>")` returns nothing for the exact name, treat it as "does not exist" and offer to create it. Do not fan out into broader searches.
- Don't invent the schedule. Time-of-day fields (`start_time`, `end_time`) and `days_of_week` must come from the admin. If they didn't give a complete schedule, ask once for the missing fields. Don't guess "business hours = 9-5".
- Don't translate clock-time to minutes silently in the explanation. Show the schedule back to the admin in human form (e.g. "08:00-17:00 Mon-Fri") and let the API call carry the minute conversion internally.
- Time Intervals are independent of any specific rule. This skill returns the interval ID and stops. Attaching the ID to a rule is the calling skill's job, not this one's.

## Naming constraint (ZIA-imposed)

ZIA rejects Time Interval names that contain **digits or special characters**. Allowed characters are ASCII letters and spaces only.

- ✅ Valid: `Business Hours`, `After Hours`, `Weekday Mornings`, `Weekend All Day`, `Maintenance Window`, `Lunch Break`
- ❌ Invalid (will be rejected): `Mon-Fri 08:00-17:00`, `Q1 Maintenance`, `9-5 Window`, `Business Hours — Mon-Fri`

The `zia_create_time_interval` tool validates this client-side and raises `ValueError` before the API call, so the agent fails fast. If the admin proposes a name with digits or punctuation, silently rename it to a letters-only equivalent (e.g. "8am to 5pm window" → `Business Hours`) and confirm the renamed value back to the admin in the final reply. Never quietly drop the schedule details — those go on the `start_time` / `end_time` / `days_of_week` fields, not on the name.

## Overview

ZIA's mechanism for recurring time-of-day / day-of-week scheduling on a policy rule is the **Time Interval** object. Once created, a Time Interval is referenced by ID through the `time_windows` field on any ZIA rule type that supports scheduling. This skill is the find-or-create helper that other ZIA rule-creation skills call when the admin's request includes a schedule.

**Which rule types accept `time_windows`:** Cloud Firewall Filtering, URL Filtering, Cloud App Control, File Type Control, Sandbox, Web DLP. Most other ZIA rule types also accept it.

**Which rule type does NOT:** SSL Inspection rules have no `time_windows` field on the API. If the admin's request is for time-of-day SSL Inspection scoping, the schedule does not belong on this skill's output — the calling skill must redirect the schedule to a different layer (typically URL Filtering or Cloud Firewall Filtering).

The skill is **idempotent on name**: if an interval with the requested name already exists with the right schedule, it is reused; otherwise a new one is created. Same-name with a *different* schedule is treated as a hard stop — the admin must rename or update the existing one before this skill creates a new one.

## What this skill returns

The skill returns a single dict the caller can consume:

```json
{
  "interval_id": "12345",
  "name": "Business Hours",
  "start_time": 480,
  "end_time": 1020,
  "days_of_week": ["MON", "TUE", "WED", "THU", "FRI"],
  "outcome": "found_existing"   // or "created_new"
}
```

`interval_id` is the value the caller writes into the rule's `time_windows: [<id>]` field.

## Hard stop conditions

- **Same name, different schedule.** If `zia_list_time_intervals(search="<name>")` returns an interval with the same name but different `start_time`, `end_time`, or `days_of_week`, **stop**. Tell the admin: "An interval named 'X' already exists but with schedule Y. Update the existing one or pick a different name." Do not silently overwrite or create a near-duplicate.
- **Schedule incomplete.** If the admin only said "during business hours" without specifying days or times, ask once for the missing fields. Do not assume a default. ZIA does not have a built-in "business hours" preset.
- **Schedule is clock-based, not session-based.** This is for time-of-day scheduling only. If the admin asks "block X for the next 4 hours after a user logs in", that's a session-length policy and does not belong here. Say so plainly and stop.
- **Cross-midnight windows.** ZIA does not support a single interval that crosses midnight (e.g. 22:00-06:00). If the admin asks for one, explain the constraint and offer to create two intervals (22:00-23:59 and 00:00-06:00) referenced together on the rule.

## Workflow

### Step 1: Gather schedule

Required from the admin (or extract from the prompt):

- **Name** — the interval label (e.g. "Business Hours", "Maintenance Window", "Weekends Only")
- **Start time** — clock time (e.g. "08:00", "9am") or `0`-`1439` minutes from midnight
- **End time** — clock time or minutes from midnight; use `1439` for end-of-day
- **Days of week** — any subset of `EVERYDAY`, `SUN`, `MON`, `TUE`, `WED`, `THU`, `FRI`, `SAT`. Convert friendly inputs ("Mon-Fri", "weekdays", "weekends") to the canonical list before the API call.

Common shorthand mappings (do these silently):

| Admin says | Convert to |
|---|---|
| "weekdays" / "Mon-Fri" / "M-F" | `["MON","TUE","WED","THU","FRI"]` |
| "weekends" / "Sat-Sun" | `["SAT","SUN"]` |
| "every day" / "all week" / "24/7" | `["EVERYDAY"]` |
| "9 to 5" | `start_time=540, end_time=1020` |
| "8am to 5pm" | `start_time=480, end_time=1020` |
| "after hours" + business hours = 8-17 | two intervals: `0-479` and `1020-1439`, or use `start_time=1020, end_time=1439` if only the evening half is needed |

Time-of-day conversion: minutes-from-midnight = `(hour * 60) + minute`.

### Step 2: Look up the existing interval

```text
zia_list_time_intervals(search="<exact name>")
```

One call, exact name. **Empty result = does not exist.** Do not retry with split keywords or `search=None`.

If the search returns one match:

- **Schedule matches** the admin's request → return `outcome="found_existing"` with the existing ID. Done. Do not create a duplicate.
- **Schedule differs** → hard stop (see Hard stop conditions above).

If the search returns multiple matches with the same name (rare; ZIA usually enforces uniqueness): list them by ID and ask the admin which to reuse.

### Step 3: Create the interval (only if Step 2 returned nothing)

```text
zia_create_time_interval(
    name="<name>",
    start_time=<minutes from midnight>,
    end_time=<minutes from midnight>,
    days_of_week=["MON", "TUE", "WED", "THU", "FRI"]   # canonical list
)
```

The tool returns the full record, including `id`. Capture it.

### Step 4: Activate (only when this skill is the *terminal* step in the admin's session)

If this skill is being called as a sub-step of `zia-create-ssl-inspection-rule` or `zia-create-firewall-filtering-rule`, **do not activate yet** — the caller will activate after attaching the interval and creating the rule. Activation flushes staged config; running it mid-chain causes two activations instead of one.

Only when this skill is the *only* thing the admin asked for (e.g. "create a Business Hours time interval and stop"):

```text
zia_activate_configuration()
```

### Step 5: Return the result

Return a structured dict the caller can use:

```json
{
  "interval_id": "<id>",
  "name": "<name>",
  "start_time": <minutes>,
  "end_time": <minutes>,
  "days_of_week": ["..."],
  "outcome": "found_existing" | "created_new"
}
```

Echo back to the admin in human form: "Reusing existing interval 'Business Hours' (08:00-17:00 Mon-Fri, ID 12345)" or "Created new interval 'Business Hours' (08:00-17:00 Mon-Fri, ID 12345)."

## Quick Reference

**Time-of-day examples (minutes from midnight):**

| Schedule | start_time | end_time |
|---|---|---|
| Entire day (00:00-23:59) | 0 | 1439 |
| Business hours (08:00-17:00) | 480 | 1020 |
| Lunch hour (12:00-13:00) | 720 | 780 |
| After hours (17:00-23:59) | 1020 | 1439 |
| Early morning maintenance (02:00-04:00) | 120 | 240 |

**Tools used:**

- `zia_list_time_intervals(search=...)` — find by name (exact match preferred)
- `zia_get_time_interval(interval_id=...)` — fetch a known interval (used when the caller already has the ID)
- `zia_create_time_interval(name, start_time, end_time, days_of_week)` — write
- `zia_activate_configuration()` — ZIA-wide activation; only when this skill is terminal

### Related skills

- `zia-create-firewall-filtering-rule` — calls into this skill when the admin requested a time-of-day Cloud Firewall rule.
- `zia-create-url-filtering-rule` — calls into this skill when the admin requested a time-of-day URL Filtering rule.

**Not compatible:**

- `zia-create-ssl-inspection-rule` — SSL Inspection rules do not support `time_windows`. Do not chain this skill into SSL Inspection. If the admin's request landed on SSL Inspection but really needs time-of-day enforcement, redirect the schedule to URL Filtering or Cloud Firewall Filtering instead.

This skill is a **dependency, not a standalone end-to-end flow**. Its output (the interval ID) is meant to be consumed by another skill that attaches it to a rule.
