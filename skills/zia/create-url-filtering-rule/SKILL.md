---
name: zia-create-url-filtering-rule
description: "Create a ZIA URL Filtering rule that controls user access to web content by URL category, protocol, request method, user agent, user/group/department, location, device trust level, and optional time-of-day schedule (Time Interval). Supported actions: ALLOW, BLOCK, CAUTION, ISOLATE. Use when an admin asks to 'create a URL filtering rule', 'block category X', 'allow category Y', 'show a caution page for Z', 'isolate access to risky sites', 'block social media during work hours', or 'add a URL filtering exception'. Supports both recurring schedules (`time_windows`) and one-shot date-range validity (`enforce_time_validity`). This skill creates exactly one URL Filtering rule and chains to `zia-manage-time-interval` when the admin's request includes a recurring schedule."
---

# ZIA: Create URL Filtering Rule

## How to talk to the admin

- Don't narrate tool calls, JMESPath filters, search keys, or internal lookup logic. Just confirm what was created and which scoping was applied.
- Empty list responses are authoritative. If a `zia_list_*` lookup returns no match for an exact-name search, treat the resource as "does not exist." Do not retry with split keywords or unfiltered listings.
- Don't claim a tool doesn't exist without checking. If `zia_create_*` and `zia_get_*` are visible for a resource, the matching `zia_list_*` exists too.
- Don't narrate strategy pivots. If you have to retry quietly, retry quietly and report only the final outcome.
- After every successful create, **mention the activation step explicitly** — ZIA changes are staged until activated. The agent must call `zia_activate_configuration()` and tell the admin the change is now live.

## Scope of this skill

This skill creates **one** URL Filtering rule per invocation. Anything outside that scope is a hard stop:

- **It does not create** the auxiliary objects the rule references (URL categories, label IDs, group/department/user IDs, location groups). If those don't exist, this skill stops and points the admin at the right place to create them — it does not improvise.
- **It does not modify SSL Inspection, Cloud Firewall, DLP, or any other ZIA rule type.** Those are separate resource types and have their own skills (`zia-create-ssl-inspection-rule`, `zia-create-firewall-filtering-rule`).
- **It does not classify URLs.** If the admin gives a literal URL, look up its category via `zia_url_lookup` first, then scope the rule by the resulting category names — URL Filtering rules match on `url_categories`, not on raw URLs.

## Hard stop conditions

Stop and report plainly when:

- **The admin's stated URL categories, label/group IDs, or location names cannot be resolved.** Resolve once via the appropriate `zia_list_*` tool; if empty, say so and stop. Do not skip the field, do not invent IDs.
- **A recurring schedule was requested but no schedule details were provided.** Don't guess. Ask once for `start_time`, `end_time`, and `days_of_week`, then chain to `zia-manage-time-interval`.
- **An action was requested that doesn't exist on this rule type.** Valid actions are exactly: `ALLOW`, `BLOCK`, `CAUTION`, `ISOLATE`. Anything else (e.g. `DECRYPT`, `INSPECT`, `BYPASS`, `BLOCK_DROP`) belongs to other rule types and is a hard stop here.
- **`ISOLATE` was requested without Browser Isolation entitlement.** ISOLATE requires a Browser Isolation subscription. If the admin asks for it on a tenant without entitlement, the API will reject the rule. Confirm the admin has the entitlement before proceeding; if unsure, suggest `CAUTION` as the closest non-isolation alternative.
- **`block_override=True` was requested without `rule_action="BLOCK"`.** Override only applies to BLOCK actions. Reject combinations that don't match.
- **`enforce_time_validity=True` was requested without start/end timestamps.** When validity windows are enforced, `validity_start_time`, `validity_end_time`, and `validity_time_zone_id` are required. Don't guess the dates.

Never improvise around a missing dependency — hand off or stop.

## Action types (what each does)

| Action | Effect on matched URL traffic | Common reasons to choose this |
|---|---|---|
| `ALLOW` | Permit the request. Other downstream policies (DLP, SSL inspection, etc.) may still apply. | Explicit allowlist for known-good URL categories or for an exception that overrides a broader BLOCK rule above. |
| `BLOCK` | Deny the request and show a BLOCK page to the user. | Block disallowed categories outright (adult content, gambling, malware, etc.). Often paired with `block_override=True` plus `override_users` / `override_groups` for managed exceptions. |
| `CAUTION` | Show the user a warning interstitial; the user may click through and continue. | Soft enforcement for risky-but-not-banned categories where awareness matters more than a hard block. |
| `ISOLATE` | Render the page in a remote isolated browser session — pixels stream to the user; the local browser never touches the site. | High-risk categories where data exfiltration / drive-by malware is the concern but a hard BLOCK is too disruptive. **Requires Browser Isolation entitlement.** |

## Two kinds of "time" on this rule type

URL Filtering exposes two different time controls — they solve different problems:

1. **`time_windows` — recurring schedule.** Attach one or more Time Interval IDs to enforce the rule on a recurring time-of-day / day-of-week pattern (e.g. "block social media 09:00-17:00 Mon-Fri"). Use `zia-manage-time-interval` to find or create the interval. Idempotent on name.

2. **`enforce_time_validity` + `validity_start_time` / `validity_end_time` / `validity_time_zone_id` — one-shot date range.** A non-recurring window during which the rule is active (e.g. "this exception is valid from Mar 1 to Mar 15 only"). Outside the window, the rule has no effect.

The two are independent and can be combined (e.g. "valid from Mar 1 to Mar 31, and only during business hours within that window"). If the admin's request implies one or the other, pick the right field — don't conflate them. If the admin says "between 9am and 5pm Mon-Fri" → that's `time_windows`. If they say "until end of March" → that's `enforce_time_validity`.

## Workflow

### Step 1: Gather requirements from the admin

Required:

- **Rule name**
- **Action** — one of `ALLOW`, `BLOCK`, `CAUTION`, `ISOLATE`

At least one matching criterion (otherwise the rule is too broad to be useful):

- **URL categories** (most common scope on this rule type)
- Protocols (e.g. `["HTTP_RULE", "HTTPS_RULE"]`)
- Request methods (`GET`, `POST`, `CONNECT`, etc.)
- User agent types (`CHROME`, `FIREFOX`, etc.)
- Users / groups / departments
- Locations / location groups
- Devices / device groups / device trust levels
- A time-of-day window (`time_windows`) and/or a one-shot validity range (`enforce_time_validity`)

Optional:

- Description, rank (1-7), order (defaults to bottom)
- `block_override=True` plus `override_users` / `override_groups` (BLOCK action only — lets specified users override)
- `end_user_notification_url` — custom block-page URL
- `size_quota`, `time_quota` — bandwidth / time budgets per session
- `ciparule=True` — flags the rule as a CIPA-compliance rule

### Step 2: Resolve every named resource (read-before-write)

**Shared rule targets — delegate to `zia-look-up-rule-targets`.** For every user, group, department, location, location group, URL category, device, device group, workload group, label, or time interval the admin named, follow `zia-look-up-rule-targets` to get the IDs (or canonical UPPER_SNAKE strings, for `url_categories` — URL Filtering takes the string form, not numeric IDs). Stop and report if any lookup is empty — never invent IDs, never substitute. (URL Filtering accepts every shared rule-target field in that skill, including `time_windows` and `workload_groups`.)

**URL-filtering-specific helpers — use here.** The shared skill handles named URL categories. Use the tool below when the admin gives you a literal URL instead of a category name.

| Admin named | Resolution tool | Lookup knob | Returns |
|---|---|---|---|
| Literal URL ("can users access foo.com?") | `zia_url_lookup` | (URL list) | category names — feed those into `url_categories=[...]` |

Don't skip a field that the admin named because lookup failed — the skill stops, the admin fixes the naming or creates the missing object first.

### Step 3: Resolve the schedule (only if the admin asked for time-of-day scoping)

If the admin's request includes any time-of-day language ("during business hours", "after hours", "weekends only", "between 8am-5pm Mon-Fri", "block social media at work", etc.), **chain to `zia-manage-time-interval`** to find or create the Time Interval and obtain its `interval_id`. That ID becomes the `time_windows=[<id>]` value on the URL Filtering rule.

If the admin asked for a one-shot validity range ("only valid until April 30", "from Mar 1 to Mar 15"), that goes into `enforce_time_validity=True` plus `validity_start_time` / `validity_end_time` / `validity_time_zone_id` — not into `time_windows`.

If the admin did not mention a schedule at all, leave `time_windows` and `enforce_time_validity` unset. Don't invent a default.

Do **not** call `zia_activate_configuration()` from within `zia-manage-time-interval` when chaining — defer activation to the end of this skill so a single activation flushes both the new Time Interval and the new URL Filtering rule.

### Step 4: Build the payload

Map admin language to canonical fields:

- "block adult content" → `rule_action="BLOCK"`, `url_categories=["OTHER_ADULT_MATERIAL", ...]`
- "block social media during work hours" → `rule_action="BLOCK"`, `url_categories=["SOCIAL_NETWORKING"]`, `time_windows=[<business-hours-interval-id>]`
- "isolate risky sites for finance team" → `rule_action="ISOLATE"`, `url_categories=[...]`, `groups=[<finance-group-id>]`
- "warn users about gambling sites" → `rule_action="CAUTION"`, `url_categories=["GAMBLING"]`
- "allow X but only for these users" → `rule_action="ALLOW"`, `url_categories=[...]`, `users=[...]`
- "block, but let admins override" → `rule_action="BLOCK"`, `block_override=True`, `override_groups=[<admin-group-id>]`
- "exception valid through end of March" → `enforce_time_validity=True`, `validity_start_time=...`, `validity_end_time=...`, `validity_time_zone_id=...`
- "block by URL foo.com" → look up category via `zia_url_lookup` first, then scope by `url_categories`
- "block downloads (POST/PUT only)" → `request_methods=["POST", "PUT"]`

### Step 5: Create the rule

Call:

```text
zia_create_url_filtering_rule(
    name=<name>,
    rule_action="ALLOW" | "BLOCK" | "CAUTION" | "ISOLATE",
    description=<optional>,
    enabled=True,
    rank=<1-7, optional>,
    order=<optional, defaults to bottom>,
    url_categories=[...],
    url_categories2=[...],          # AND-ed with url_categories when both are set
    protocols=[...],
    request_methods=[...],
    user_agent_types=[...],
    device_trust_levels=[...],
    devices=[...],
    device_groups=[...],
    groups=[...],
    departments=[...],
    users=[...],
    locations=[...],
    location_groups=[...],
    labels=[...],
    time_windows=[<interval_id>],   # only if recurring schedule was requested
    enforce_time_validity=<bool>,   # only if one-shot validity range was requested
    validity_start_time=<...>,
    validity_end_time=<...>,
    validity_time_zone_id=<...>,
    block_override=<bool>,          # BLOCK action only
    override_users=[...],
    override_groups=[...],
    end_user_notification_url=<optional custom URL>,
    size_quota=<optional KB>,
    time_quota=<optional minutes>,
    ciparule=<optional bool>,
)
```

Capture the returned `id`.

### Step 6: Activate the configuration

ZIA changes are staged until activation. After every successful create, run:

```text
zia_activate_configuration()
```

Tell the admin: "URL Filtering rule created (ID `<id>`) and activated." If activation fails, surface the error — the rule exists but is not live.

### Step 7: Echo back what was applied

Confirm in plain language:

- The rule name and action (`ALLOW` / `BLOCK` / `CAUTION` / `ISOLATE`)
- Each scoping dimension applied (one bullet per — categories, users, locations, schedule, etc.)
- The interval ID if a recurring schedule was attached, with the schedule in human form ("08:00-17:00 Mon-Fri")
- The validity window if `enforce_time_validity=True`, in human form
- Override config if `block_override=True`
- The activation status

Don't restate operand IDs or internal field names that the admin doesn't need to see.

## Quick Reference

**Tools used:**

- Read: `zia_list_url_filtering_rules(search=...)` — only on explicit admin request for ordering / duplicate checks
- Read: `zia_url_lookup` — when the admin gives a literal URL instead of a category name
- Write: `zia_create_url_filtering_rule(name, rule_action, ...)`
- Activation: `zia_activate_configuration()`

**Schedule sub-skill:**

- `zia-manage-time-interval` — chain whenever the admin's request mentions recurring time-of-day or day-of-week. Not used for `enforce_time_validity` (that's a one-shot date range, not an interval).

**Related ID-resolution tools (one call per resource, exact name):**

- `zia_list_url_categories`, `zia_list_user_groups`, `zia_list_user_departments`, `zia_list_users`, `zia_list_locations`, `zia_list_rule_labels`

### Related skills

- `zia-manage-time-interval` — find-or-create helper for recurring schedule scoping (see Step 3).
- `zia-investigate-url-category` — read-only audit of how a URL category is referenced across rules. Use before creating a new rule when the admin wants to understand existing coverage.
- `zia-look-up-cloud-app-name` — only relevant if the admin's "URL category" request is actually a cloud-application policy decision; URL Filtering does not match on cloud-app names directly.

**Different ZIA rule types — do not chain through this skill:**

- `zia-create-ssl-inspection-rule` — SSL Inspection is a separate resource type and does NOT support `time_windows`. If the admin wants time-of-day enforcement on SSL behaviour, the schedule typically belongs on the URL Filtering layer instead.
- `zia-create-firewall-filtering-rule` — Cloud Firewall is L3/L4 (IPs, ports, network apps), not URL-based. If the admin's request is about hostnames or URL categories, this skill is the right one.
- DLP / Sandbox / Cloud App Control — also separate resource types.

**Typical chain when a recurring schedule is requested:**

```text
zia-manage-time-interval         (find or create the Time Interval, return its ID)
        ↓
zia-create-url-filtering-rule    (this skill — attach the interval ID and create the rule)
        ↓
zia_activate_configuration()     (one activation flushes both)
```

**Don't pre-list rules before creating.** Skip `zia_list_url_filtering_rules` unless the admin explicitly asks about ordering or wants to inspect existing rules — direct create + activate is the default flow.
