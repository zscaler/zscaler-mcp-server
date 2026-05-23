---
name: zia-create-cloud-app-control-rule
description: "Create ZIA Cloud App Control rules that enforce granular, action-level decisions on cloud applications (Dropbox, OneDrive, Google Drive, ChatGPT, GitHub, YouTube, Slack, etc.). Cloud App Control is action-level, not block/allow at the connection layer — actions are things like ALLOW_FILE_SHARE_UPLOAD, BLOCK_WEBMAIL_ATTACH, ISOLATE_AI_ML_WEB_USE, DENY_AI_ML_CHAT, BLOCK_SOCIAL_NETWORKING_POST. Each rule belongs to a category (rule_type) such as FILE_SHARE, WEBMAIL, AI_ML, SYSTEM_AND_DEVELOPMENT, SOCIAL_NETWORKING, STREAMING_MEDIA, etc. Action vocabulary is surfaced at the category level, but the API validates per (rule_type, application, action) tuple — combining multiple apps in a single rule frequently fails with INVALID_INPUT_ARGUMENT, so this skill creates one rule per cloud application when the admin names multiple apps. Use when an admin asks to 'allow Dropbox uploads', 'block ChatGPT', 'restrict GitHub edits', 'isolate AI tools', 'block YouTube uploads', 'allow only viewing on OneDrive', 'block file uploads to personal cloud storage (Dropbox, Google Drive, OneDrive)', or 'create a Cloud App Control rule for X'. Chains to `zia-look-up-cloud-app-name` and `zia-manage-time-interval` when needed."
---

# ZIA: Create Cloud App Control Rule

## How to talk to the admin

- Don't narrate tool calls, search filters, JMESPath expressions, or internal lookup logic. Just confirm what was created and which scoping was applied.
- Empty list responses are authoritative. If a `zia_list_*` lookup returns no match for an exact-name search, treat the resource as "does not exist." Do not retry with split keywords or unfiltered listings.
- Don't claim a tool doesn't exist without checking. If `zia_create_*` and `zia_get_*` are visible for a resource, the matching `zia_list_*` exists too.
- Don't narrate strategy pivots. If you have to retry quietly, retry quietly and report only the final outcome.
- After every successful create, **mention the activation step explicitly** — ZIA changes are staged until activated. The agent must call `zia_activate_configuration()` and tell the admin the change is now live.

## Scope of this skill

This skill creates **one or more** Cloud App Control rules per invocation. When the admin names multiple cloud apps in one request, the skill creates **one rule per app** (see "Multi-app handling" below) — that is intentional, not a violation of scope. Anything outside that scope is a hard stop:

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
- **The rule name is longer than 31 characters.** ZIA enforces a hard 31-character maximum on the Cloud App Control rule `name`. The API rejects longer names with `{"code": "INVALID_INPUT_ARGUMENT", "message": "Name exceeds the max length 31 characters"}`. Abbreviate the verb (`"Blk"` for Block, `"Allw"` for Allow, `"Iso"` for Isolate) before truncating the app name — see Step 7 for the worked pattern. This counts **bytes**, not Unicode grapheme clusters; emoji and most accented characters in the name will consume more than one slot.
- **A recurring schedule was requested but no schedule details were provided.** Don't guess. Ask once for `start_time`, `end_time`, and `days_of_week`, then chain to `zia-manage-time-interval`.

Never improvise around a missing dependency — hand off or stop.

## How Cloud App Control differs from other rule types

| Question | Answer for Cloud App Control |
|---|---|
| What does the rule act on? | A specific cloud application (or set of apps in the same category). |
| Is the action applied to the connection or the operation? | The **operation**. The connection still flows, but specific operations (upload, share, edit, comment, post, attach) are allowed, blocked, or isolated. |
| Is the action set the same for every app in a category? | **Mostly, but not strictly.** Action vocabulary is *surfaced* at the category level (every `FILE_SHARE` app's discovery call returns the same enum list; every `AI_ML` app's discovery returns its own list; etc.), and the same action enum is rejected if used with the wrong category. **However**, the create endpoint validates per `(rule_type, app, action)` tuple — a category-level action may still be rejected when paired with one specific app in that category. This is why this skill creates one rule per app rather than combining apps in a single `cloud_applications` list (see "Multi-app handling"). |
| Can a rule cover multiple categories? | **No.** A single rule has exactly one `rule_type` (category). To cover two categories, create two rules. |
| Can a rule cover multiple apps? | **In theory yes** — `cloud_applications` accepts a list — but in practice ZIA frequently rejects multi-app rules with `INVALID_INPUT_ARGUMENT: "Invalid action provided for selected applications"` because per-app action validity varies. **Default to one rule per app.** See "Multi-app handling" below. |
| Does the rule require SSL decryption to take effect? | **Yes** for most actions. If the matching traffic is in a `DO_NOT_DECRYPT` SSL Inspection rule, action enforcement does not happen. |
| Does the rule require an `order`? | **Yes.** ZIA rejects create payloads without `order`. Default is 1 (top of policy table) when omitted. |

## Multi-app handling (one rule per cloud application)

**Pattern: when the admin's request names more than one cloud application — even apps in the same category — create one rule per app, not a single rule with all apps in `cloud_applications`.**

**Why.** Cloud App Control's action enums are surfaced at the *category* level, but the API validates **per `(rule_type, application, action)` tuple**. Two apps in the same category can each accept a slightly different subset of the category's action enums. A rule combining multiple apps with a shared action list frequently fails the create call with:

```json
{
    "code": "INVALID_INPUT_ARGUMENT",
    "message": "Invalid action provided for selected applications"
}
```

The error is total — the create fails for **all** apps in the call, not just the rejected one. There is no API surface that enumerates per-app action validity up front, so the only safe pattern is to split.

**Loop the workflow once per app.** Each iteration reuses the same scoping (users / groups / locations / schedule / device trust), the same `rule_type`, and the same admin intent — only `name`, `cloud_applications`, and `actions` change per iteration. Rule names must be unique **and ≤ 31 characters** (ZIA hard limit), so suffix each with the app's friendly name and abbreviate the verb if needed (e.g. `"Blk upload - Dropbox"`, `"Blk upload - GDrive"`, `"Blk upload - OneDrive"`). Step 7 has the full abbreviation pattern.

| Admin request | Resulting rules |
|---|---|
| "Block uploads on Dropbox, Google Drive, and OneDrive for Finance" | **3 rules** — one each for `cloud_applications=["DROPBOX"]`, `["GDRIVE"]`, `["ONEDRIVE"]`, every rule scoped to the Finance group. |
| "Allow viewing on SharePoint but block sharing" | 1 rule (single app). |
| "Block all file-sharing apps" | Enumerate category members via `zia_list_cloud_app_policy(app_class="FILE_SHARE", query="[*].app")`, then loop one rule per app. |

**Why not one rule per category instead?** Tempting, but every app added to `cloud_applications` re-runs the per-app validation on the server. The first incompatible (app, action) pair fails the entire create. One rule per app removes the ambiguity entirely and makes each rule individually auditable in the ZIA UI.

After all rules in the loop have been created, activate **once** at the end (Step 8) — a single activation flushes them all.

## Action vocabulary (a few illustrative examples)

The exact enums vary per category — **always** discover them via `zia_list_cloud_app_control_actions(cloud_app=<app>)` before creating a rule. For reference, here are typical patterns:

| Category | Sample apps | Sample actions |
|---|---|---|
| `FILE_SHARE` | `DROPBOX`, `BOX`, `ONEDRIVE`, `GOOGLE_DRIVE` | `ALLOW_FILE_SHARE_VIEW`, `ALLOW_FILE_SHARE_UPLOAD`, `ALLOW_FILE_SHARE_CREATE`, `ALLOW_FILE_SHARE_DELETE`, `ALLOW_FILE_SHARE_DOWNLOAD`,  `ALLOW_FILE_SHARE_EDIT`, `ALLOW_FILE_SHARE_FORM_SHARE`, `ALLOW_FILE_SHARE_RENAME`, `ALLOW_FILE_SHARE_SHARE`, `DENY_FILE_SHARE_CREATE`, `DENY_FILE_SHARE_DELETE`, `DENY_FILE_SHARE_EDIT`, `DENY_FILE_SHARE_FORM_SHARE`, `DENY_FILE_SHARE_RENAME`, `FILE_SHARE_CONDITIONAL_ACCESS`, `BLOCK_FILE_SHARE_UPLOAD`, `BLOCK_FILE_SHARE_DOWNLOAD`, `BLOCK_FILE_SHARE_SHARE`, `CAUTION_FILE_SHARE`, `DENY_FILE_SHARE_UPLOAD`, `DENY_FILE_SHARE_VIEW`, `FILE_SHARE_CONDITIONAL_ACCESS` |
| `WEBMAIL` | `GMAIL`, `GOOGLE_WEBMAIL`, `OUTLOOK_WEB_ACCESS`, `YAHOO_WEBMAIL` | `ALLOW_WEBMAIL_VIEW`, `ALLOW_WEBMAIL_ATTACHMENT_SEND`, `ALLOW_WEBMAIL_SEND`, `BLOCK_WEBMAIL_ATTACH`, `BLOCK_WEBMAIL_SEND`, `BLOCK_WEBMAIL_VIEW` `CAUTION_WEBMAIL`, `CAUTION_WEBMAIL_VIEW` |
| `AI_ML` | `CHATGPT_AI`, `GEMINI`, `ANTHROPIC_CLAUDE`, `MICROSOFT_COPILOT` | `ALLOW_AI_ML_WEB_USE`, `DENY_AI_ML_CHAT`, `DENY_AI_ML_WEB_USE`, `ISOLATE_AI_ML_WEB_USE`, `CAUTION_AI_ML_WEB_USE` |
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

- **Rule name** — **hard ZIA limit of 31 characters**; longer names are rejected with `{"code": "INVALID_INPUT_ARGUMENT", "message": "Name exceeds the max length 31 characters"}`. Plan for this *before* the create call, especially in multi-app loops where each rule needs a unique name (see Step 7 for the abbreviation pattern).
- **Target cloud application(s)** — the app or apps the admin wants to govern (e.g. "Dropbox", "ChatGPT", "GitHub", "YouTube", "personal cloud storage like Dropbox, Google Drive, and OneDrive"). Friendly names are OK; the resolver in Step 2 will translate them. **If the admin names multiple apps, the skill will create one rule per app — see "Multi-app handling" above.** When the admin describes a *kind* of app rather than naming individual ones ("all file-sharing apps", "every AI tool"), enumerate the apps in that category with `zia_list_cloud_app_policy(app_class=<category>, query="[*].app")` and confirm the list with the admin before continuing.
- **What operations to allow / block / isolate** — the admin's intent in plain language. Examples: "allow viewing but block uploads", "block any file sharing", "isolate the session", "let users chat but block file transfers".
- **`order`** — 1-based position in the evaluation sequence (`order=1` is the top, evaluated first; ZIA evaluates rules top-to-bottom and stops at the first match). The tool defaults to `1` when omitted, but **always pass `order` explicitly when the tenant already has Cloud App Control rules of the same `rule_type`** — derive the value from the safety checks in [Step 6: Rule placement and safety checks (mandatory)](#step-6-rule-placement-and-safety-checks-mandatory) instead of guessing.
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

### Step 2: Resolve each cloud application to a canonical enum

The admin will usually name app(s) in plain English (`"Dropbox"`, `"ChatGPT"`, `"Microsoft OneDrive"`, `"Google Drive"`). Cloud App Control needs the **canonical ZIA enum** for each one (`DROPBOX`, `CHATGPT_AI`, `ONEDRIVE`, `GDRIVE`).

**Resolve every app the admin named individually.** When the admin names N apps in one request, treat this as N independent resolutions (and, downstream, N independent rule creates — see "Multi-app handling" above).

For each named app:

1. Call `zia_list_cloud_app_policy(search="<app name>", query="[*].{app: app, name: appName, parent: parent}")`.
2. The policy catalog returns each entry as `{"app": "<canonical enum>", "appName": "<display name>", "parent": "<category>", "parentName": "<category display name>"}`. **Always use the `app` field** (the canonical enum, e.g. `GDRIVE`) as the value for the rule's `cloud_applications`. Never pass the display name (`appName`, e.g. `"Google Drive"`) — the create API rejects it.
3. Note the `parent` field — this is the category the app belongs to, and it becomes the rule's `rule_type` in Step 3.

If a search returns nothing, the app is not in the policy-engine catalog — stop and tell the admin. Do not fall back to Shadow IT analytics (`zia_list_shadow_it_apps`) — that's a different catalog and its IDs are not valid Cloud App Control inputs.

If a search returns multiple plausible matches (e.g. `"sharepoint"` → `SHAREPOINT_ONLINE` and `SHAREPOINT_FOR_BUSINESS`), ask the admin which one they want **before** moving on. Do not silently pick one.

The create/update tools also auto-resolve friendly names via the policy-engine catalog — but doing the resolution explicitly in this step keeps the audit trail clean, lets you confirm ambiguous matches, and gives you the `parent` value you need for Step 3.

For deeper canonical-name lookup help, chain to `zia-look-up-cloud-app-name`.

### Step 3: Discover the rule_type and the available actions for each app

**Call once per canonical enum from Step 2** (even when multiple apps share a category — the per-app call confirms the category mapping and the action vocabulary for that specific app's branch):

```text
zia_list_cloud_app_control_actions(cloud_app="<canonical enum>")
```

The response is a structured dict. The fields that matter for rule creation:

- `category` — pass this as `rule_type` on the create call (it should match the `parent` you noted in Step 2).
- `actions` — the **category's** action enum vocabulary. Pick the subset that matches the admin's stated intent for this app.
- `resolved_app` — confirms how the input was resolved.
- `actions_surfaced_via` — diagnostic; the app the API actually returned actions for (may differ from `resolved_app` because not every app in a category is a "representative" the API surfaces actions for — the tool walks the category until it finds one that does).

**Important caveat about the returned `actions` list.** It is the **category's full vocabulary**, not a per-app validity list. The ZIA API validates each `(action, app)` pair at create time, and an action returned here may still be rejected when paired with a *specific* app in the same category. There is no read-only call that enumerates per-app action validity — the create call is the only authoritative validator. If a create fails with `INVALID_INPUT_ARGUMENT: "Invalid action provided for selected applications"`, pare the `actions` list down to the subset the admin actually asked for and retry; see Step 7.

**Why you cannot skip this step:** action enum vocabulary varies per category. Hand-typing `BLOCK_DROPBOX_UPLOAD` will be silently rejected by ZIA — the real enum is `BLOCK_FILE_SHARE_UPLOAD` (and only valid because Dropbox is in `FILE_SHARE`).

If the admin's intent maps to multiple actions, pass them all (e.g. `actions=["ALLOW_FILE_SHARE_VIEW", "BLOCK_FILE_SHARE_UPLOAD", "BLOCK_FILE_SHARE_SHARE"]` for "view-only on Dropbox"). If the admin's intent doesn't map to any actions in the returned set, stop and ask — don't substitute.

### Step 4: Resolve shared operands (read-before-write)

For every user, group, department, location, location group, device, device group, label, or time interval the admin named, **delegate to `zia-look-up-rule-targets`** to get the IDs. That skill is the single source of truth for these lookups and enforces the project's hard rules (one call per rule target, empty list = does not exist, never invent IDs, never narrate). Cloud App Control accepts every shared rule-target field listed there **except** `url_categories` and `workload_groups` (CAC is operation-level inside an app — its scoping uses cloud applications, not URL categories or workload groups).

Stop and report if any lookup is empty — never invent IDs, never substitute.

### Step 5: Resolve the schedule (only if the admin asked for time-of-day scoping)

If the admin's request includes any time-of-day language ("during business hours", "after hours", "weekends only", "between 8am-5pm Mon-Fri", "block YouTube at lunch"), **chain to `zia-manage-time-interval`** to find or create the Time Interval and obtain its `interval_id`. That ID becomes the `time_windows=[<id>]` value on the rule.

If the admin did not mention a schedule, leave `time_windows` unset. Don't invent a default.

For a temporary rule (e.g. "block this during a 30-day audit window") use `enforce_time_validity=True` + `validity_start_time` + `validity_end_time` + `validity_time_zone_id` instead — that's an absolute date range, distinct from the recurring weekly window of `time_windows`.

Do **not** call `zia_activate_configuration()` from within `zia-manage-time-interval` when chaining — defer activation to the end of this skill so a single activation flushes both the new Time Interval and the new Cloud App Control rule.

### Step 6: Rule placement and safety checks (mandatory)

Before building the create call, run a short policy review. Cloud App Control rules sit in a single top-to-bottom evaluation table per `rule_type` — **first match wins**. Creating a rule blindly is the most common way to silently disable existing rules or duplicate work that's already in place.

**Evaluation model in one paragraph.** The policy table is evaluated top to bottom (`order=1` is the top, evaluated first); the first rule whose criteria match the traffic wins and no further rules are consulted for that connection. A more general rule placed above a more specific rule will **shadow** the specific one. Deny / Block actions must sit **above** any Allow rule that could match the same traffic — otherwise the Allow wins and the Deny never fires.

**Pull the current policy table once.** Use a single discovery call and reuse its result for all four checks below:

```text
zia_list_cloud_app_control_rules(
    rule_type=<category from Step 3>,
    query="[?enabled].{id: id, name: name, order: order, actions: actions, cloud_applications: cloud_applications}",
)
```

**Required checks — every create must pass all four:**

a. **Specificity.** The new rule must target a specific cloud application (or a small set of related apps in the same category) **and** at least one additional scoping dimension (users / groups / departments / locations / devices / time window / device trust / user-agent type). A rule with only `cloud_applications` and no other scoping is acceptable only when the admin explicitly asked for a tenant-wide policy ("everyone, everywhere"); confirm that intent before continuing.

b. **Shadowing.** For every existing enabled rule whose `order` is **above** the proposed position, ask: would it match the same traffic this new rule is meant to govern? If yes, the new rule will be **shadowed** (never reached). Either move the new rule above the conflicting rule(s), or ask the admin whether the conflicting rules should be narrowed. Never proceed silently with a shadowed rule.

c. **Duplicate purpose.** Scan the same result for any existing enabled rule whose `actions` + `cloud_applications` + key scoping (users / locations / device trust) effectively performs what the admin is asking for. If one is found, stop and report the matching rule (name + ID) to the admin — ask whether they want to **modify** the existing rule (`zia_update_cloud_app_control_rule`) rather than creating a parallel one. Creating a duplicate is almost always a configuration error.

d. **Deny supersedes Allow.** If the new rule uses a `BLOCK_*` or `DENY_*` action, scan the result for any enabled rule with an `ALLOW_*` action whose `cloud_applications` covers the same app(s) (or a superset). The new Deny rule must sit **above** every such Allow rule — compute the lowest `order` value among those Allow rules and set the new rule's `order` to a value strictly less than that. The Deny itself must also be specific (per check a) — it should not be broader than the operation the admin actually wants to block.

**Choosing the final `order` value.**

- If checks b–d produced a constraint (e.g. "must be above order 5"), pick a value that satisfies it. ZIA renumbers the table around the insertion.
- If no constraint was produced, default to `order=1` (top) for restrictive new rules and a higher number (near the bottom) for permissive baseline rules that should only catch traffic nothing else governed.
- Always pass `order` explicitly when the tenant already has Cloud App Control rules of the same `rule_type` — never rely on the tool default.

Surface the chosen `order` and the reason for it in the echo-back at the end (Step 9), so the admin can see the placement decision was deliberate.

### Step 7: Build and create the rule(s)

**Loop once per app from Step 2 — one create call per canonical enum.** Reuse the same scoping (users / groups / locations / schedule / device trust), same `rule_type`, same admin intent; only `name`, `cloud_applications`, and `actions` change per iteration:

```text
zia_create_cloud_app_control_rule(
    rule_type=<category from step 3, e.g. "FILE_SHARE">,
    name=<rule name (max 31 chars); make per-app names distinct — see below>,
    actions=[<one or more action enums from step 3>],
    cloud_applications=[<exactly one canonical enum from step 2>],
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

- **`rule_type` is required** and must match the `category` returned by `zia_list_cloud_app_control_actions` for the app — passing the wrong category for the chosen `actions` is the #1 way to get a 400 from this API.
- **`actions` is required** and must be a subset of the action list returned in step 3 for the same category.
- **`cloud_applications` should contain exactly one canonical enum** — see "Multi-app handling" at the top of this skill. The field maps internally to the SDK's `applications` kwarg; we surface it as `cloud_applications` to stay consistent with other ZIA rule tools (SSL Inspection, Web DLP, File Type Control). Friendly names are auto-resolved; if any name is auto-resolved, the response includes a `_cloud_applications_resolution` audit field — surface it when echoing back to the admin so they see exactly which canonical enum each input became.
- **`name` must be unique per app AND fit inside ZIA's 31-character hard limit.** ZIA rejects duplicate rule names; when looping for N apps, suffix the name with the app's friendly name. Exceeding 31 characters returns `{"code": "INVALID_INPUT_ARGUMENT", "message": "Name exceeds the max length 31 characters"}` — count the characters before submitting. Examples (all ≤ 31):

  | Intent | Bad (32+ chars) | Good (≤ 31 chars, plain ASCII) |
  |---|---|---|
  | Block uploads, multi-app loop | `"Block uploads — Microsoft OneDrive"` (35) | `"Blk upload - OneDrive"` (21), `"Blk upload - GDrive"` (19), `"Blk upload - Dropbox"` (20) |
  | View-only, single app | `"Dropbox view-only for Finance team"` (34) | `"DBX view-only - Finance"` (23) |
  | Isolate AI tools | `"Isolate ChatGPT for engineering"` (32) | `"Iso ChatGPT - Eng"` (17) |

  **Abbreviation pattern when you're tight:** shorten the verb first (`"Block"` → `"Blk"`, `"Allow"` → `"Allw"`, `"Isolate"` → `"Iso"`, `"Deny"` → `"Dny"`), then drop articles and prepositions, then trim the app name to its common short form (`"OneDrive"`, `"GDrive"`, `"DBX"`, `"ChatGPT"`). Keep the app suffix readable so the admin can still identify which rule is which in the ZIA UI. When you're at the edge of the limit, prefer plain ASCII separators (`-`) over typographic ones (`—`) — multi-byte characters can be counted differently by different parts of the ZIA stack, so plain ASCII is the safe default.
- Capture the returned `id` from each call.

**Error handling — `INVALID_INPUT_ARGUMENT: "Invalid action provided for selected applications"`.** ZIA validates each `(action, app)` pair at create time, and a category-level action may not be valid for a specific app in that category. If you hit this error:

1. Pare the `actions` list down to the minimal subset the admin actually asked for (drop any "while I'm here" extras).
2. Retry the create for that specific app.
3. If a single action still fails, the action genuinely doesn't apply to that app — confirm with the admin and either substitute a different action they're happy with, or skip that app from the loop and tell the admin which apps were skipped and why.

Do not silently change `cloud_applications` to a different app to make the action accept. Do not silently combine apps into a single rule to "save a call" — that's the exact pattern this error exists to prevent.

### Step 8: Activate the configuration

ZIA changes are staged until activation. After **all** the rules in your loop (Step 7) have been created — not after each individual create — run **one** activation:

```text
zia_activate_configuration()
```

A single activation flushes every staged change at once; activating per-rule is unnecessary and slower. Tell the admin: "<N> Cloud App Control rule(s) created (IDs `<id1>, <id2>, …`) and activated." If activation fails, surface the error — the rules exist but are not live.

### Step 9: Echo back what was applied

Confirm in plain language. For a single rule, one block. For a multi-app loop, one block **per rule**:

- The rule name.
- The cloud application it applies to (use the friendly display name, not the enum, when speaking to the admin).
- Each granular action that was applied, in human terms ("uploads blocked, viewing allowed, sharing blocked").
- Each scoping dimension that was applied (one bullet per — users, locations, schedule, device trust, etc.).
- The `rule_type` (category), so the admin knows where to find the rule in the ZIA UI.
- The chosen `order` and a one-line reason ("placed above the existing 'Allow Dropbox' rule so the new block fires first", or "placed at top — no existing rules in this category"), so the admin can see the placement was deliberate.
- The activation status (one line at the end, covers the whole batch).

For a multi-app loop, also list any apps that were **skipped** and why (e.g. "Box was skipped — the requested `BLOCK_FILE_SHARE_UPLOAD` action is not valid for `BOX` and no equivalent action exists in this tenant"). Never hide a partial outcome.

Don't restate operand IDs or internal field names that the admin doesn't need to see. Don't restate the `_cloud_applications_resolution` audit verbatim — paraphrase ("`'Dropbox'` → `DROPBOX`, `'OneDrive'` → `ONEDRIVE`").

## Quick Reference

**Tools used:**

- Discovery: `zia_list_cloud_app_policy(search=...)` — find the canonical app enum and its `parent` category.
- Discovery: `zia_list_cloud_app_control_actions(cloud_app=...)` — find the `category` (rule_type) and valid `actions` for the target app. **Always call this before create.**
- Read: `zia_list_cloud_app_control_rules(rule_type=..., search=...)` — **required** before every create to run the Step 6 safety checks (specificity, shadowing, duplicate purpose, Deny-above-Allow). `rule_type` is required by the SDK.
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
for each app the admin named:
    zia_list_cloud_app_policy(search="<app>")       (find canonical enum + parent category)
            ↓
    zia_list_cloud_app_control_actions(cloud_app=…) (find rule_type + valid actions)

zia-manage-time-interval                            (find or create the Time Interval, return its ID)
        ↓
zia_list_cloud_app_control_rules(rule_type=…)       (Step 6 safety checks: specificity, shadowing,
                                                     duplicate purpose, Deny-above-Allow)
        ↓
for each resolved app:
    zia_create_cloud_app_control_rule(…)            (one rule per app — see "Multi-app handling")
        ↓
zia_activate_configuration()                        (one activation flushes the whole batch)
```

**Pre-list the existing rules once, but stay scoped.** The Step 6 safety checks require one `zia_list_cloud_app_control_rules(rule_type=<category>)` call so the agent can reason about placement, shadowing, duplicate purpose, and Deny-above-Allow ordering. Reuse that single result for all four checks across every iteration of the create loop — don't fan out additional list calls per app, and don't list rules outside the target `rule_type`.
