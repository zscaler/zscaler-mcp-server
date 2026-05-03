---
name: zia-look-up-rule-targets
description: "Look up the shared 'who/where/when/what-device' fields that every ZIA rule resource scopes by — users, groups, departments, locations, location_groups, url_categories, devices, device_groups, workload_groups, labels, and time_windows — and return the IDs (or canonical strings) the rule API expects. Use this skill from inside any ZIA rule create/update workflow (Cloud Firewall, DNS, IPS, URL Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox, Cloud App Control) when the admin names a user, group, location, label, etc. by display name and you need the ID before building the rule payload. Centralises the read-before-write lookup convention so individual rule skills stay short and accurate. The skill enforces the project's hard rules: empty list = does not exist, never invent IDs, never silently substitute, never fan-out retries."
---

# ZIA: Look Up Rule Targets

## Why this skill exists

Every ZIA rule resource (Cloud Firewall, DNS, IPS, URL Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox, Cloud App Control) scopes by the same set of "who/where/when/what-device" target fields:

- `users`, `groups`, `departments` — who the rule applies to
- `locations`, `location_groups` — where the user is connecting from
- `url_categories` — which URL category the request hits
- `devices`, `device_groups` — which managed device the user is on
- `workload_groups` — which workload (cloud-asset) the connection is to/from
- `labels` — admin-assigned tags for organisation/reporting
- `time_windows` — which time-of-day schedule the rule honours

Every one of those fields takes **IDs** (or, for `url_categories`, **canonical UPPER_SNAKE strings**), not display names. The admin will almost always name them by display name. This skill is the single source of truth for "given a name, find the ID."

Centralising it here means every rule skill (`zia-create-firewall-filtering-rule`, `zia-create-cloud-app-control-rule`, etc.) can chain to this one instead of repeating — and re-decaying — the same lookup table.

## Hard rules (apply to every lookup)

These rules are non-negotiable and override anything a rule skill might say in passing:

1. **Read-before-write.** For every rule target the admin names, run **one** lookup with the appropriate `zia_list_*` tool before assembling the rule payload.
2. **Empty list is authoritative.** If the list call returns no match for an exact-name lookup, the named target **does not exist**. Stop the rule create. Tell the admin plainly. Do not retry with split keywords, broader filters, larger `page_size`, unfiltered listings, or "let me also try without the filter to double-check." One call, one answer.
3. **Never invent IDs.** If a lookup returns nothing, never substitute a similar-looking ID, never skip the field that the admin named, never silently drop it from the payload. The rule payload must reflect the admin's intent verbatim or the workflow stops.
4. **Never narrate the lookup.** Don't tell the admin "I'm searching for the user group `Engineering`…" — just resolve, build the payload, and report what was applied. If you have to retry quietly (e.g. one retry with a different known-good knob, see the `name=` vs `search=` notes), retry quietly and report only the final outcome.
5. **Don't pre-list targets the admin didn't name.** If the admin says "create a rule for users in `Engineering`," resolve only `Engineering`. Don't dump the full user-group list as context, don't enumerate departments, don't list time intervals "in case they want one."
6. **One target kind per call.** Don't try to bundle a user lookup and a location lookup into one tool call.

## Rule-target catalogue

The table below is **the** authoritative mapping for ZIA rule-target fields. Each row gives:

- the canonical field name on the rule payload
- the type the rule expects (list of `int` IDs, or list of `str` UPPER_SNAKE)
- the lookup tool to use, with the **correct** tool name (the project has a few legacy multiplexed tools — those are called out)
- which rule resources accept the field
- known quirks worth remembering at lookup time

| Rule-target field | Payload type | Lookup tool (with knob) | Accepted by which rule types | Notes |
|---|---|---|---|---|
| `users` | `list[int]` IDs | `zia_users_manager(action="read", search="<name>")` | every rule type | Multiplexed legacy tool — `action="read"` is the only supported action via this entrypoint; pagination via `page` + `page_size`. |
| `groups` (= user groups) | `list[int]` IDs | `zia_user_group_manager(action="read", name="<literal>")` | every rule type | Multiplexed legacy tool. **Use `name=`, not `search=`** — server-side `search` is unreliable on this endpoint (sometimes matches user login IDs); the tool's `name=` is a case-insensitive substring match resolved client-side after pulling a wide page. So `name="A000"` reliably finds `A000`, `a000`, `Group_A000`. |
| `departments` (= user departments) | `list[int]` IDs | `zia_user_department_manager(action="read", search="<name>")` | every rule type **except IPS** | Multiplexed legacy tool. Cloud Firewall IPS rules do not expose `departments` on the create payload. |
| `locations` | `list[int]` IDs | `zia_list_locations(query_params={"search": "<name>"})` | every rule type | The `query_params` knob forwards to the SDK; pass `{"search": "<name>"}` for substring match against location name. |
| `location_groups` | `list[int]` IDs | `zia_list_location_groups(name="<exact>", search="<substring>", group_type="Static" \| "Dynamic")` | every rule type | Read-only — the public ZIA API does **not** expose location group create/update/delete. If the admin's named group doesn't exist, the only options are: pick an existing group, or have the admin create one in the ZIA UI first. Group types: `Static` (manually-curated) or `Dynamic` (driven by location attributes). |
| `url_categories` | **`list[str]`** UPPER_SNAKE on most rule types; **`list[int]`** IDs on Web DLP only | `zia_list_url_categories(search="<name>")` for discovery; `zia_get_url_category_predefined(name=...)` for built-in lookups by ID or display name | URL Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox; **not** on Cloud Firewall / DNS / IPS / Cloud App Control | **Two distinct shapes** — Web DLP accepts numeric IDs, every other rule accepts the canonical UPPER_SNAKE category string (e.g. `OTHER_ADULT_MATERIAL`). The list tool returns both fields on every entry; pick the right one for the rule type. **Predefined vs custom matters.** ZIA ships hundreds of curated categories (`FINANCE`, `NEWS_AND_MEDIA`, `OTHER_ADULT_MATERIAL`, etc.) plus any custom categories the admin has created — they share the same API surface but have different lifecycle rules. See "Creating URL categories on the fly" below for the full decision tree, including when to chain to the predefined-only mutation tools. |
| `devices` | `list[int]` IDs | `zia_list_devices(name="<name>")` (or `zia_list_devices_lite` for ID-only payloads) | Cloud Firewall, DNS, IPS, URL Filtering, SSL Inspection, File Type Control, Cloud App Control; **not** Sandbox / Web DLP | These are the same devices ZCC manages. Disabling the `zcc` service does NOT remove the ZIA device tools — they're an intentional cross-service overlap. Use `_lite` when you only need IDs (faster on large tenants). |
| `device_groups` | `list[int]` IDs | `zia_list_device_groups(search="<name>")` | same as `devices` | Same cross-service-overlap caveat as `devices`. |
| `workload_groups` | `list[int]` IDs | `zia_list_workload_groups(query="[?name=='<exact>']")` | **only Cloud Firewall, URL Filtering, SSL Inspection, Web DLP** | Read-only via this server. The ZIA list endpoint does **not** support a server-side `name` filter — use a JMESPath `query` to filter client-side (e.g. `query="[?name=='WG-AWS-Prod']"`). Workload group authoring (with its expression DSL) is intentionally left to the ZIA UI. |
| `labels` | `list[int]` IDs | `zia_list_rule_labels(search="<name>")` | every rule type | Labels are the project's own organisational tagging — separate from URL categories or any other classification. Has full CRUD if the admin asks to create one. |
| `time_windows` (= time intervals) | `list[int]` IDs | **chain to `zia-manage-time-interval`** (sub-skill) | every rule type **except SSL Inspection** | SSL Inspection has no `time_windows` field on the API — time-of-day enforcement on encrypted traffic must be done on a different rule type. The sub-skill handles find-or-create; never create the time interval inline. |

## Lookup pattern (apply to every row)

For every rule target the admin names:

1. Pick the row from the table above.
2. Make exactly one call to the listed tool, with the listed knob, using the admin's literal name.
3. Examine the response:
   - **One match** → take its `id` (or, for `url_categories`, take its `id` field for Web DLP / its canonical string field for everything else). Move on to the next target.
   - **Multiple matches** → ask the admin once which one they meant. Do not auto-pick.
   - **No match** → stop the rule create. Report which target could not be resolved. Suggest either correcting the name or creating the missing resource first (with the appropriate sub-skill if one exists — e.g. `zia-onboard-location` for new locations, `zia-manage-time-interval` for new time intervals).

After all named targets are resolved, hand the IDs back to the calling rule skill so it can build the rule payload.

## Creating URL categories on the fly

`url_categories` is the one rule-target field where create-on-demand is part of the normal flow. ZIA exposes two flavours of URL categories that share the same API surface but have very different lifecycle rules:

- **Predefined (Zscaler-curated)** — `FINANCE`, `NEWS_AND_MEDIA`, `OTHER_ADULT_MATERIAL`, `SHAREWARE_DOWNLOAD`, etc. Cannot be created or deleted. Can be modified in two narrow ways: incremental URL/IP add/remove (preserves Zscaler's curated list) or full PUT of the keyword/IP fields.
- **Custom (admin-owned)** — created by the admin. Full CRUD lifecycle. Used when the rule scope is "block these specific 12 domains" rather than "block this whole category."

The toolset cleanly separates the two:

| Action | Custom category | Predefined category |
|---|---|---|
| Discover by partial name | `zia_list_url_categories(search="...")` (returns both flavours; check `custom_category` field) | same tool — `custom_category=False` indicates predefined |
| Get by exact ID/name | `zia_get_url_category(category_id=...)` | `zia_get_url_category_predefined(name=...)` — accepts `FINANCE` *or* `Finance`, case-insensitive |
| Create | `zia_create_url_category(...)` | **N/A** — predefined categories cannot be created. |
| Full-replace update | `zia_update_url_category(...)` | `zia_update_url_category_predefined(name=..., ...)` — same field surface |
| Add URLs (incremental, safe on predefined) | `zia_add_urls_to_category(category_id=..., urls=[...])` | same tool — works on both flavours |
| Remove URLs (incremental, safe on predefined) | `zia_remove_urls_from_category(category_id=..., urls=[...])` | same tool — works on both flavours |
| Delete | `zia_delete_url_category(...)` | **N/A** — predefined categories cannot be deleted. |

The custom-only tools (`zia_update_url_category`, `zia_delete_url_category`) refuse predefined IDs at the safety-guard layer — calling them against `FINANCE` raises a `ValueError` pointing at the right predefined-flavoured tool. Trust those guards; do not work around them.

Decision tree when the admin names a URL category in a rule scope:

1. **The admin named a built-in category by canonical name** (e.g. "block `OTHER_ADULT_MATERIAL`"). Use it as-is in the rule payload — no lookup needed beyond verifying it exists via `zia_list_url_categories(search=...)` or `zia_get_url_category_predefined(name=...)`.
2. **The admin named a category by a recognisable description** (e.g. "block adult material"). Run `zia_list_url_categories(search="<keyword>")` and confirm the canonical string with the admin if more than one matches. Pick from results where `custom_category` matches the admin's intent.
3. **The admin named a custom category that already exists**. `zia_list_url_categories(search="<name>")` will return it with `custom_category=True`. Use its `id` (Web DLP) or canonical string (every other rule type).
4. **The admin named a custom category that doesn't exist** *and* gave you URLs ("create a rule that blocks these URLs: example.com, foo.com"). Treat this as a custom URL category create. Call `zia_create_url_category(configured_name=..., super_category=..., urls=[...])` first, then use the returned ID/canonical string in the rule payload.
5. **The admin named a custom category that doesn't exist and gave no URLs**. Stop. Ask for the URL list (or which existing category they meant). Don't substitute a similarly-named built-in category.
6. **The admin asked to add/remove URLs on a predefined category** ("add `bad-site.com` to `FINANCE`"). This is a separate workflow from rule creation — call `zia_add_urls_to_category(category_id="FINANCE", urls=[...])` (or `zia_remove_urls_from_category` with HMAC confirmation). Both work transparently on predefined IDs because they use the SDK's `?action=ADD_TO_LIST` / `?action=REMOVE_FROM_LIST` endpoints, which preserve Zscaler's curated list.
7. **The admin asked to fully replace fields on a predefined category** (e.g. "set the keywords on `FINANCE` to exactly these 5"). Use `zia_update_url_category_predefined(name="FINANCE", keywords=[...])`. Calling `zia_update_url_category` against a predefined ID is rejected by the safety guard — that's intentional, because a full-PUT against a predefined category would obliterate Zscaler's curated URL list.

Important: Web DLP is the only rule type whose `url_categories` field takes numeric IDs. Every other rule type takes the canonical UPPER_SNAKE string. The list/get/create tools return both fields on each entry — pick the right one based on which rule you're building.

## Rule-target × Rule-type coverage matrix

This is the same table as above, restated as a coverage matrix so the calling rule skill can quickly check which rule-target fields its rule type supports.

| Rule-target field | CFW | DNS | IPS | URL | SSL | DLP | FTC | SBX | CAC |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `users` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `groups` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `departments` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `locations` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `location_groups` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `url_categories` (str) | ❌ | ❌ | ❌ | ✅ | ✅ | n/a | ✅ | ✅ | ❌ |
| `url_categories` (int IDs) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Cloud-app catalog field (chain to `zia-look-up-cloud-app-name`) — named `cloud_applications` everywhere except DNS, where it's named `applications` | ❌ | ✅ (`applications`) | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `devices` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| `device_groups` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| `workload_groups` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `labels` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `time_windows` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |

Legend: CFW = Cloud Firewall, DNS = Cloud Firewall DNS, IPS = Cloud Firewall IPS, URL = URL Filtering, SSL = SSL Inspection, DLP = Web DLP, FTC = File Type Control, SBX = Sandbox, CAC = Cloud App Control.

If the admin names a rule-target field that the rule type doesn't support (e.g. `time_windows` on SSL Inspection, `departments` on IPS, `url_categories` on Cloud Firewall), stop and explain — do not silently drop the field. Suggest the correct rule type if it's a clear mismatch.

## Naming-knob cheat sheet

A few of the lookup tools have non-obvious knob preferences. The defaults below match what the tool descriptions document.

| Tool | Preferred knob | Reason |
|---|---|---|
| `zia_user_group_manager(action="read", ...)` | **`name=`** (not `search=`) | Server-side `search` on the `/groups` endpoint is unreliable — it has been observed matching user login IDs instead of group names. The tool's `name=` parameter pulls a wide page and does case-insensitive substring matching client-side. |
| `zia_list_network_services(...)` (used by firewall, not by other rule types) | **`name=`** | ZIA's canonical network-service names are uppercase enums (`HTTP`, `FTP`, `DNS`); server-side `search="http"` does NOT match `HTTP`. The tool's `name=` normalises casing client-side. |
| `zia_list_locations(...)` | `query_params={"search": "<name>"}` | Direct forward to the SDK. |
| `zia_list_location_groups(...)` | `name=` for exact match, `search=` for substring | The list endpoint exposes both knobs server-side. |
| `zia_list_workload_groups(...)` | JMESPath `query="[?name=='<exact>']"` | The list endpoint has no server-side name filter at all — JMESPath is the only path. |
| Everything else | `search=` | Standard substring forward. |

## What this skill does NOT cover

This skill is intentionally narrow. The following lookups are **rule-type-specific** and are handled inside their respective rule skills, not here:

- **The cloud-app catalog field** (canonical ZIA app names like `DROPBOX`, `ONEDRIVE`, `SHAREPOINT_ONLINE`, `CLOUDFLARE_DOH`). Exposed as **`cloud_applications`** on **SSL Inspection, Web DLP, File Type Control, and Cloud App Control**, and as **`applications`** on **Cloud Firewall DNS** rules — same catalog, different field name (an inconsistency in the underlying ZIA API). *Not* used by Cloud Firewall (non-DNS), IPS, or Sandbox. → always chain to **`zia-look-up-cloud-app-name`** to translate friendly names to canonical names. SSL Inspection, File Type Control, Cloud App Control, and DNS auto-resolve friendly names in their tools; Web DLP does not yet.
- **Cloud App Control's `actions` and `rule_type` fields** (the category-scoped action enum set and the category itself). → `zia-create-cloud-app-control-rule` plus `zia_list_cloud_app_control_actions` for action discovery.
- **Cloud Firewall-specific fields**: `src_ips`, `dest_addresses`, `source_countries`, `dest_countries`, `dest_ip_categories`, `dest_ip_groups`, `dest_ipv6_groups`, `device_trust_levels`, `nw_applications`, `nw_application_groups`, `nw_services`, `nw_service_groups`, `app_services`, `app_service_groups`. → `zia-create-firewall-filtering-rule`.
- **SSL Inspection-specific fields**: ZPA app segments, platforms, the `action` dict (with sub-actions). → `zia-create-ssl-inspection-rule`.
- **DLP-specific fields**: DLP engines, DLP dictionaries, ICAP server, notification template, auditor, file types, content scopes. → handled inside the Web DLP rule skill (when written) or directly in `zscaler_mcp/tools/zia/web_dlp_rules.py`.
- **Sandbox-specific fields**: file types, ba_rule_action, ba_policy_categories. → `zia-create-sandbox-rule` (if/when written).
- **The Time Interval object itself.** Finding or creating a `time_windows` ID is delegated to `zia-manage-time-interval`. This skill just tells you that `time_windows` is the field name and that you should chain.

## How a rule skill chains to this one

In practice, every rule skill's "Step 2: Resolve every named resource (read-before-write)" should look like this — and nothing more for the shared rule-target fields:

> **Step 2 — Look up shared rule targets.** For every user, group, department, location, location group, URL category, device, device group, workload group, label, or time interval the admin named, follow `zia-look-up-rule-targets` to get the IDs (or canonical strings, for `url_categories`). Stop and report if any lookup is empty — never invent IDs, never substitute. Then resolve any rule-type-specific fields (listed below) before assembling the payload.

The rule-type-specific lookups (e.g. firewall's IP source/destination/network-service-group resolution, SSL's cloud-app + URL-category resolution, CAC's app-enum + actions discovery) stay in the rule skill itself, because they don't apply to other rule types.

## Quick Reference

**Read-only lookup tools (in the order of the rule-target table):**

- `zia_users_manager(action="read", search=...)`
- `zia_user_group_manager(action="read", name=...)`
- `zia_user_department_manager(action="read", search=...)`
- `zia_list_locations(query_params={"search": ...})`
- `zia_list_location_groups(name=..., search=..., group_type=...)`
- `zia_list_url_categories(search=...)` — discovery for both flavours
- Custom-category lifecycle: `zia_get_url_category` / `zia_create_url_category` / `zia_update_url_category` (full PUT, custom only) / `zia_delete_url_category` (custom only, HMAC)
- Predefined-category lifecycle: `zia_get_url_category_predefined(name=...)` / `zia_update_url_category_predefined(name=..., ...)` (full PUT, predefined only)
- Incremental URL/IP edits (work transparently on both flavours): `zia_add_urls_to_category(category_id=..., urls=[...])` / `zia_remove_urls_from_category(category_id=..., urls=[...])`
- `zia_list_devices(name=...)` / `zia_list_devices_lite` / `zia_list_device_groups(search=...)`
- `zia_list_workload_groups(query="[?name=='...']")`
- `zia_list_rule_labels(search=...)`
- `zia-manage-time-interval` (sub-skill, not a tool)

**Sub-skills referenced from here:**

- `zia-manage-time-interval` — find-or-create a Time Interval and return its ID for the `time_windows` field.
- `zia-onboard-location` — create a new location (with its static IP / VPN credential prerequisites) when the admin named one that doesn't exist.

**Skills that chain INTO this one:**

- `zia-create-firewall-filtering-rule`
- `zia-create-cloud-app-control-rule`
- `zia-create-ssl-inspection-rule`
- `zia-create-url-filtering-rule`
- (and any future ZIA rule create/update skill — DLP, sandbox, file type control, DNS, IPS)

Each of those skills delegates the shared rule-target lookups to this skill and keeps only the rule-type-specific logic locally.
