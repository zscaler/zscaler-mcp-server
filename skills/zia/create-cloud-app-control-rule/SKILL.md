---
name: zia-create-cloud-app-control-rule
description: "Create a ZIA Cloud App Control rule that enforces granular, action-level decisions on cloud applications (Dropbox, OneDrive, ChatGPT, GitHub, YouTube, Slack, etc.). Cloud App Control is action-level, not block/allow at the connection layer — actions are things like ALLOW_FILE_SHARE_UPLOAD, BLOCK_WEBMAIL_ATTACH, ISOLATE_AI_ML_WEB_USE, DENY_AI_ML_CHAT, BLOCK_SOCIAL_NETWORKING_POST. Each rule belongs to a category (rule_type) such as FILE_SHARE, WEBMAIL, AI_ML, SYSTEM_AND_DEVELOPMENT, SOCIAL_NETWORKING, STREAMING_MEDIA, etc. The available actions are defined per category, not per app — every app in the same category shares the same action set. Use when an admin asks to 'allow Dropbox uploads', 'block ChatGPT', 'restrict GitHub edits', 'isolate AI tools', 'block YouTube uploads', 'allow only viewing on OneDrive', or 'create a Cloud App Control rule for X'. This skill creates exactly one Cloud App Control rule and chains to `zia-look-up-cloud-app-name` and `zia-manage-time-interval` when needed."
---

# ZIA: Create Cloud App Control Rule

## How to talk to the admin

- Don't narrate tool calls, search filters, JMESPath expressions, or internal lookup logic. Just confirm what was created and which scoping was applied.
- Empty list responses are authoritative. If a `zia_list_*` lookup returns no match for an exact-name search, treat the resource as "does not exist." Do not retry with split keywords or unfiltered listings.
- Don't claim a tool doesn't exist without checking. If `zia_create_*` and `zia_get_*` are visible for a resource, the matching `zia_list_*` exists too.
- Don't narrate strategy pivots. If you have to retry quietly, retry quietly and report only the final outcome.
- After every successful create, **mention the activation step explicitly** — ZIA changes are staged until activated. The agent must call `zia_activate_configuration()` and tell the admin the change is now live.

## Scope of this skill

This skill creates **one** Cloud App Control rule per invocation. Anything outside that scope is a hard stop:

- **It does not create** the auxiliary objects the rule references (location IDs, label IDs, group/department/user IDs, device groups, time intervals). If those don't exist, this skill stops and points the admin at the right place to create them — it does not improvise.
- **It does not modify SSL Inspection, Cloud Firewall, URL Filtering, DLP, File Type Control, or any other ZIA rule type.** Those are separate resource types and have their own skills (`zia-create-ssl-inspection-rule`, `zia-create-firewall-filtering-rule`, `zia-create-url-filtering-rule`). Cloud App Control is **not** the same as URL Filtering — URL Filtering blocks at the URL/category level; Cloud App Control allows or blocks specific *operations* (upload, share, edit, comment, attach) inside an application.
- **It does not bypass SSL inspection.** Cloud App Control needs the traffic to be decrypted to enforce action-level decisions. If the traffic is in a `DO_NOT_DECRYPT` SSL Inspection rule, the action enforcement will not happen — surface this as a known limitation if the admin asks why a rule isn't taking effect.

## Hard stop conditions

Stop and report plainly when:

- **The admin's stated cloud app cannot be resolved** to a canonical ZIA name after one targeted lookup. Do not invent canonical names, do not silently substitute a similar app. Hand off to `zia-look-up-cloud-app-name` if the admin needs help finding the right canonical name.
- **The admin asked for an action that doesn't exist on this app's category.** Cloud App Control actions are category-scoped. `BLOCK_FILE_SHARE_UPLOAD` works for `DROPBOX` (category `FILE_SHARE`) but not for `GMAIL` (category `WEBMAIL`, where the equivalent is `BLOCK_WEBMAIL_ATTACH`). Always discover the valid actions for the target app's category first — do not guess action enums.
- **The admin asked for plain "BLOCK" or "ALLOW".** Cloud App Control does not have a connection-level block/allow. Pick the right granular action (e.g. `BLOCK_FILE_SHARE_UPLOAD`, `ALLOW_FILE_SHARE_VIEW`). If the admin really wants a connection-level block of an entire application, that's a Cloud Firewall rule (`zia-create-firewall-filtering-rule`) or URL Filtering rule, not Cloud App Control.
- **The admin's stated location names, user/group/department IDs, label names, or time-interval names cannot be resolved.** Resolve once via the appropriate `zia_list_*` tool; if empty, say so and stop. Do not skip the field, do not invent IDs.
- **`rank` is outside the inclusive range `0..7`.** ZIA's admin rank is a 0-7 integer; the tool will reject any other value before the API call. See [admin rank documentation](https://help.zscaler.com/zia/about-admin-rank).
- **A recurring schedule was requested but no schedule details were provided.** Don't guess. Ask once for `start_time`, `end_time`, and `days_of_week`, then chain to `zia-manage-time-interval`.

Never improvise around a missing dependency — hand off or stop.

## How Cloud App Control differs from other rule types

| Question | Answer for Cloud App Control |
|---|---|
| What does the rule act on? | A specific cloud application (or set of apps in the same category). |
| Is the action applied to the connection or the operation? | The **operation**. The connection still flows, but specific operations (upload, share, edit, comment, post, attach) are allowed, blocked, or isolated. |
| Is the action set the same for every app? | **No.** Actions are defined at the **category level**. Every app in `FILE_SHARE` shares the same actions; `AI_ML` apps share their own action set; etc. The same action enum (e.g. `BLOCK_FILE_SHARE_UPLOAD`) is rejected by the API if used with the wrong category. |
| Can a rule cover multiple categories? | **No.** A single rule has exactly one `rule_type` (category). To cover two categories, create two rules. |
| Does the rule require SSL decryption to take effect? | **Yes** for most actions. If the matching traffic is in a `DO_NOT_DECRYPT` SSL Inspection rule, action enforcement does not happen. |
| Does the rule require an `order`? | **Yes.** ZIA rejects create payloads without `order`. Default is 1 (top of policy table) when omitted. |

## Action vocabulary (a few illustrative examples)

The exact enums vary per category — **always** discover them via `zia_list_cloud_app_control_actions(cloud_app=<app>)` before creating a rule. For reference, here are typical patterns:

| Category | Sample apps | Sample actions |
|---|---|---|
| `FILE_SHARE` | `DROPBOX`, `BOX`, `ONEDRIVE`, `GOOGLE_DRIVE` | `ALLOW_FILE_SHARE_VIEW`, `ALLOW_FILE_SHARE_UPLOAD`, `BLOCK_FILE_SHARE_UPLOAD`, `BLOCK_FILE_SHARE_DOWNLOAD`, `BLOCK_FILE_SHARE_SHARE`, `CAUTION_FILE_SHARE` |
| `WEBMAIL` | `GMAIL`, `GOOGLE_WEBMAIL`, `OUTLOOK_WEB_ACCESS`, `YAHOO_WEBMAIL` | `ALLOW_WEBMAIL_VIEW`, `BLOCK_WEBMAIL_ATTACH`, `BLOCK_WEBMAIL_SEND`, `CAUTION_WEBMAIL` |
| `AI_ML` | `CHATGPT_AI`, `GEMINI`, `ANTHROPIC_CLAUDE`, `MICROSOFT_COPILOT` | `ALLOW_AI_ML_WEB_USE`, `DENY_AI_ML_CHAT`, `ISOLATE_AI_ML_WEB_USE`, `CAUTION_AI_ML_WEB_USE` |
| `SYSTEM_AND_DEVELOPMENT` | `GITHUB`, `GITLAB`, `AZURE_DEVOPS`, `JIRA` | `ALLOW_SYSTEM_DEVELOPMENT_CREATE`, `BLOCK_SYSTEM_DEVELOPMENT_EDIT`, `BLOCK_SYSTEM_DEVELOPMENT_SHARE`, `DEV_CONDITIONAL_ACCESS` |
| `STREAMING_MEDIA` | `YOUTUBE`, `NETFLIX`, `VIMEO`, `TWITCH` | `ALLOW_STREAMING_VIEW`, `BLOCK_STREAMING_UPLOAD`, `CAUTION_STREAMING` |
| `SOCIAL_NETWORKING` | `FACEBOOK`, `TWITTER`, `LINKEDIN`, `INSTAGRAM` | `ALLOW_SOCIAL_NETWORKING_VIEW`, `BLOCK_SOCIAL_NETWORKING_POST`, `BLOCK_SOCIAL_NETWORKING_CHAT` |
| `INSTANT_MESSAGING` | `SLACK`, `MICROSOFT_TEAMS`, `DISCORD`, `WHATSAPP` | `ALLOW_CHAT`, `BLOCK_FILE_TRANSFER_UPLOAD`, `BLOCK_FILE_TRANSFER_DOWNLOAD` |
| `ENTERPRISE_COLLABORATION` | `ZOOM`, `WEBEX`, `GOOGLE_MEET`, `MICROSOFT_TEAMS_MEETING` | `ALLOW_COLLABORATION_VIEW`, `BLOCK_COLLABORATION_RECORD`, `BLOCK_COLLABORATION_SHARE_FILE` |

**Action prefixes mean:**

- `ALLOW_*` — permit the operation.
- `BLOCK_*` / `DENY_*` — deny the operation outright.
- `CAUTION_*` — show the user a warning page; they can proceed by acknowledging.
- `ISOLATE_*` — hand the session to Browser Isolation (requires Isolation entitlement).
- `*_CONDITIONAL_ACCESS` — apply Conditional Access policy logic.

The treatment of "view-only" mode is typically `ALLOW_*_VIEW` paired with `BLOCK_*_UPLOAD` / `BLOCK_*_DOWNLOAD` / `BLOCK_*_SHARE` in the same rule.

## Workflow

### Step 1: Gather requirements from the admin

Required:

- **Rule name** (max 31 chars).
- **Target cloud application** — the app the admin wants to govern (e.g. "Dropbox", "ChatGPT", "GitHub", "YouTube"). Friendly names are OK; the resolver in step 2 will translate them.
- **What operations to allow / block / isolate** — the admin's intent in plain language. Examples: "allow viewing but block uploads", "block any file sharing", "isolate the session", "let users chat but block file transfers".
- **`order`** — 1-based position in the evaluation sequence. The tool defaults to `1` (top) when omitted, but the agent should set it explicitly whenever creating more than one rule in a session. ZIA evaluates rules top-to-bottom — order matters.
- **`rank`** — admin rank, integer in the inclusive range `0..7`. The tool defaults to `7` (highest) when omitted; this matches ZIA's documented default. See [admin rank documentation](https://help.zscaler.com/zia/about-admin-rank).

At least one matching criterion (otherwise the rule is too broad to be useful):

- The cloud application(s) themselves (`cloud_applications=[...]`)
- Users / groups / departments
- Locations / location groups
- Device trust levels / devices / device groups
- User-agent types (e.g. browser-only enforcement)
- A time-of-day window (Time Interval)
- A validity window (`enforce_time_validity` + `validity_start_time` / `validity_end_time` / `validity_time_zone_id`) for temporary rules

Optional:

- Description, rank (1-7), order (defaults to top), labels, size/time quotas

### Step 2: Resolve the cloud application to a canonical enum

The admin will usually name the app in plain English (`"Dropbox"`, `"ChatGPT"`, `"Microsoft OneDrive"`). Cloud App Control needs the canonical ZIA enum (`DROPBOX`, `CHATGPT_AI`, `ONEDRIVE`).

The create/update tools auto-resolve friendly names via the policy-engine catalog, but **the discovery tool in step 3 needs the canonical enum (or a friendly name it can resolve)** to look up the category and actions. Cleanest path:

1. Call `zia_list_cloud_app_policy(search="<app name>", query="[*].{enum: app, name: app_name, parent: parent}")`.
2. Pick the matching `enum` value.
3. Note the `parent` field — this is the category the app belongs to (this is what becomes the rule's `rule_type` in step 4).

If the search returns nothing, the app is not in the policy-engine catalog — stop and tell the admin. Do not fall back to Shadow IT analytics (`zia_list_shadow_it_apps`) — that's a different catalog and its IDs are not valid Cloud App Control inputs.

If the search returns multiple plausible matches (e.g. `"sharepoint"` → `SHAREPOINT_ONLINE` and `SHAREPOINT_FOR_BUSINESS`), ask the admin which one they want **before** moving to step 3.

For deeper canonical-name lookup help, chain to `zia-look-up-cloud-app-name`.

### Step 3: Discover the rule_type and the available actions for that app

Once you have the canonical enum (or a friendly name the resolver can handle), call:

```text
zia_list_cloud_app_control_actions(cloud_app="<canonical enum or friendly name>")
```

The response is a structured dict. The fields that matter for rule creation:

- `category` — this is the value to pass as `rule_type` on the create call.
- `actions` — the full list of valid action enums for that category. Pick the subset that matches the admin's stated intent.
- `resolved_app` — confirms how the input was resolved.
- `actions_surfaced_via` — diagnostic; the app the API actually returned actions for (may differ from `resolved_app` because actions are category-level and not every app is a "representative" the API returns actions for — the tool walks the category until it finds one that does).

**Why you cannot skip this step:** the action enum vocabulary varies per category. Hand-typing `BLOCK_DROPBOX_UPLOAD` will be silently rejected by ZIA — the real enum is `BLOCK_FILE_SHARE_UPLOAD` (and only valid because Dropbox is in `FILE_SHARE`).

If the admin's intent maps to multiple actions, pick all of them and pass the full list (e.g. `actions=["ALLOW_FILE_SHARE_VIEW", "BLOCK_FILE_SHARE_UPLOAD", "BLOCK_FILE_SHARE_SHARE"]` for "view-only on Dropbox"). If the admin's intent doesn't map to any actions in the returned set, stop and ask — don't substitute.

### Step 4: Resolve shared operands (read-before-write)

For every user, group, department, location, location group, device, device group, label, or time interval the admin named, **delegate to `zia-look-up-rule-targets`** to get the IDs. That skill is the single source of truth for these lookups and enforces the project's hard rules (one call per rule target, empty list = does not exist, never invent IDs, never narrate). Cloud App Control accepts every shared rule-target field listed there **except** `url_categories` and `workload_groups` (CAC is operation-level inside an app — its scoping uses cloud applications, not URL categories or workload groups).

Stop and report if any lookup is empty — never invent IDs, never substitute.

### Step 5: Resolve the schedule (only if the admin asked for time-of-day scoping)

If the admin's request includes any time-of-day language ("during business hours", "after hours", "weekends only", "between 8am-5pm Mon-Fri", "block YouTube at lunch"), **chain to `zia-manage-time-interval`** to find or create the Time Interval and obtain its `interval_id`. That ID becomes the `time_windows=[<id>]` value on the rule.

If the admin did not mention a schedule, leave `time_windows` unset. Don't invent a default.

For a temporary rule (e.g. "block this during a 30-day audit window") use `enforce_time_validity=True` + `validity_start_time` + `validity_end_time` + `validity_time_zone_id` instead — that's an absolute date range, distinct from the recurring weekly window of `time_windows`.

Do **not** call `zia_activate_configuration()` from within `zia-manage-time-interval` when chaining — defer activation to the end of this skill so a single activation flushes both the new Time Interval and the new Cloud App Control rule.

### Step 6: Build and create the rule

Call:

```text
zia_create_cloud_app_control_rule(
    rule_type=<category from step 3, e.g. "FILE_SHARE">,
    name=<rule name (max 31 chars)>,
    actions=[<one or more action enums from step 3>],
    cloud_applications=[<canonical enum(s) from step 2>],
    description=<optional>,
    enabled=True,
    rank=<0-7, default 7>,                     # always send; tool defaults to 7
    order=<1-based position, default 1>,       # always send; tool defaults to 1 (top)
    device_trust_levels=[...],                 # ANY, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST, UNKNOWN_DEVICETRUSTLEVEL
    user_agent_types=[...],
    locations=[...],
    location_groups=[...],
    groups=[...],
    departments=[...],
    users=[...],
    time_windows=[<interval_id>],              # only if schedule was requested
    labels=[...],
    devices=[...],
    device_groups=[...],
    enforce_time_validity=<bool>,
    validity_start_time=<...>,
    validity_end_time=<...>,
    validity_time_zone_id=<...>,
    size_quota=<KB>,
    time_quota=<minutes>,
)
```

Notes on the call:

- **`rule_type` is required** and must match the `category` returned by `zia_list_cloud_app_control_actions` — passing the wrong category for the chosen `actions` is the #1 way to get a 400 from this API.
- **`actions` is required** and must be a subset of the action list returned in step 3 for the same category.
- **`cloud_applications`** maps internally to the SDK's `applications` kwarg. We surface it as `cloud_applications` to stay consistent with other ZIA rule tools (SSL Inspection, Web DLP, File Type Control). Friendly names are auto-resolved; if any name is auto-resolved, the response includes a `_cloud_applications_resolution` audit field — surface it when echoing back to the admin so they see exactly which canonical enum each input became.
- Capture the returned `id`.

### Step 7: Activate the configuration

ZIA changes are staged until activation. After every successful create, run:

```text
zia_activate_configuration()
```

Tell the admin: "Cloud App Control rule created (ID `<id>`) and activated." If activation fails, surface the error — the rule exists but is not live.

### Step 8: Echo back what was applied

Confirm in plain language:

- The rule name.
- The cloud application(s) it applies to (use the friendly display name, not the enum, when speaking to the admin).
- Each granular action that was applied, in human terms ("uploads blocked, viewing allowed, sharing blocked").
- Each scoping dimension that was applied (one bullet per — users, locations, schedule, device trust, etc.).
- The `rule_type` (category), so the admin knows where to find the rule in the ZIA UI.
- The activation status.

Don't restate operand IDs or internal field names that the admin doesn't need to see. Don't restate the `_cloud_applications_resolution` audit verbatim — paraphrase ("`'Dropbox'` → `DROPBOX`, `'OneDrive'` → `ONEDRIVE`").

## Quick Reference

**Tools used:**

- Discovery: `zia_list_cloud_app_policy(search=...)` — find the canonical app enum and its `parent` category.
- Discovery: `zia_list_cloud_app_control_actions(cloud_app=...)` — find the `category` (rule_type) and valid `actions` for the target app. **Always call this before create.**
- Read: `zia_list_cloud_app_control_rules(rule_type=..., search=...)` — only on explicit admin request for ordering / duplicate checks. `rule_type` is required by the SDK.
- Read: `zia_get_cloud_app_control_rule(rule_type=..., rule_id=...)` — fetch a specific rule (also used as the implicit pre-step inside `update` for silent backfill of `name`).
- Write: `zia_create_cloud_app_control_rule(rule_type, name, actions, cloud_applications, ...)`.
- Write: `zia_update_cloud_app_control_rule(rule_type, rule_id, ...)` — partial updates work; the tool silently backfills `name` from the existing rule when omitted.
- Write: `zia_delete_cloud_app_control_rule(rule_type, rule_id)` — destructive, returns an HMAC confirmation token first; pass it back to confirm.
- Activation: `zia_activate_configuration()`.

**Schedule sub-skill:**

- `zia-manage-time-interval` — chain whenever the admin's request mentions time-of-day or day-of-week.

**Cloud-app enum sub-skill:**

- `zia-look-up-cloud-app-name` — chain when the admin's app name is ambiguous, mistyped, or when you need to confirm the canonical name before discovery.

**Related ID-resolution tools:**

- **Shared rule targets** (users, groups, departments, locations, location groups, devices, device groups, labels, time windows): handled by `zia-look-up-rule-targets`. CAC does not use `url_categories` or `workload_groups`.
- **CAC-specific discovery**: `zia_list_cloud_app_policy`, `zia_list_cloud_app_control_actions`.

### Related skills

- `zia-look-up-rule-targets` — shared name-to-ID lookups for users, groups, departments, locations, location groups, devices, device groups, labels, and time windows. Chain to it from Step 4.
- `zia-look-up-cloud-app-name` — friendly-name → canonical-name lookups (see Step 2).
- `zia-manage-time-interval` — find-or-create helper for schedule scoping (see Step 5).

**Different ZIA rule types — do not chain through this skill:**

- `zia-create-ssl-inspection-rule` — SSL Inspection is a separate resource type. If the admin wants Cloud App Control to enforce action-level decisions on encrypted traffic, the matching connections must already be `DECRYPT`'d by an SSL Inspection rule — that's a separate prerequisite, not part of this skill.
- `zia-create-firewall-filtering-rule` — for connection-level allow/block of an entire application, that's a Cloud Firewall rule, not Cloud App Control.
- `zia-create-url-filtering-rule` — for URL- or category-level allow/block, that's URL Filtering. Cloud App Control is operation-level inside an app, not URL-level.
- File Type Control / Web DLP / Sandbox / Cloud Firewall DNS / Cloud Firewall IPS rules — also separate resource types.

**Typical chain when a schedule is requested:**

```text
zia_list_cloud_app_policy(search="<app>")       (find canonical enum + parent category)
        ↓
zia_list_cloud_app_control_actions(cloud_app=…) (find rule_type + valid actions)
        ↓
zia-manage-time-interval                        (find or create the Time Interval, return its ID)
        ↓
zia-create-cloud-app-control-rule               (this skill — attach interval ID and create the rule)
        ↓
zia_activate_configuration()                    (one activation flushes both)
```

**Don't pre-list rules before creating.** Skip `zia_list_cloud_app_control_rules` unless the admin explicitly asks about ordering or wants to inspect existing rules — direct discover + create + activate is the default flow.
