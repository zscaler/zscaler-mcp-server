---
name: zia-create-ssl-inspection-rule
description: "Create a ZIA SSL Inspection rule that controls how Zscaler handles SSL/TLS encrypted traffic — BLOCK (drop the SSL connection), DECRYPT (decrypt and inspect), or DO_NOT_DECRYPT (pass through without decryption). Scopes the rule by cloud applications, URL categories, users, groups, departments, locations, device trust levels, platforms, source/destination IP groups, and ZPA application segments. SSL Inspection rules do NOT support a recurring time-of-day schedule — for time-of-day enforcement, use a different rule type (Cloud Firewall Filtering, URL Filtering, etc.). Use when an admin asks to 'create an SSL inspection rule', 'do not decrypt traffic to X', 'decrypt SSL for Y', 'block SSL for Z', or 'add an SSL bypass exception'. For pure auditing of existing SSL bypass posture, see `zia-audit-ssl-inspection-bypass` (read-only)."
---

# ZIA: Create SSL Inspection Rule

## How to talk to the admin

- Don't narrate tool calls, JMESPath filters, search keys, or internal lookup logic. Just confirm what was created and which scoping was applied.
- Empty list responses are authoritative. If a `zia_list_*` lookup returns no match for an exact-name search, treat the resource as "does not exist." Do not retry with split keywords or unfiltered listings.
- Don't claim a tool doesn't exist without checking. If `zia_create_*` and `zia_get_*` are visible for a resource, the matching `zia_list_*` exists too.
- Don't narrate strategy pivots. If you have to retry quietly, retry quietly and report only the final outcome.
- After every successful create, **mention the activation step explicitly** — ZIA changes are staged until activated. The agent must call `zia_activate_configuration()` and tell the admin the change is now live.

## Scope of this skill

This skill creates **one** SSL Inspection rule per invocation. Anything outside that scope is a hard stop:

- **It does not create** the auxiliary objects the rule references (URL categories, IP groups, label IDs, group/department/user IDs, ZPA app segments, location groups). If those don't exist, this skill stops and points the admin at the right place to create them — it does not improvise.
- **It does not modify Cloud Firewall, URL Filtering, DLP, or any other ZIA rule type.** Those are separate resource types and have their own skills (`zia-create-firewall-filtering-rule` for firewall, `zia-create-url-filtering-rule` for URL filtering).
- **It does not deal with timeouts, session expiry, or re-authentication.** SSL Inspection is a per-connection decryption decision. ZPA-style timeouts are unrelated.
- **It does not support a recurring time-of-day schedule.** SSL Inspection rules have no `time_windows` attribute on the API. If the admin needs time-of-day scoping, the policy decision belongs on a different rule type (see "When the admin asks for a schedule" below).

## Hard stop conditions

Stop and report plainly when:

- **The admin's stated cloud apps, URL categories, IP groups, or label/group IDs cannot be resolved.** Resolve once via the appropriate `zia_list_*` tool; if empty, say so and stop. Do not skip the field, do not invent IDs.
- **An action was requested that doesn't exist on this rule type.** Valid actions are exactly: `BLOCK`, `DECRYPT`, `DO_NOT_DECRYPT`. Anything else (`INSPECT`, `DO_NOT_INSPECT`, `ALLOW`, `BYPASS`, etc.) belongs to other rule types or is simply not a valid SSL Inspection action.
- **The admin asked for a recurring time-of-day SSL Inspection rule.** SSL Inspection does not support `time_windows`. Stop and explain — see "When the admin asks for a schedule" below.
- **The admin is trying to modify the predefined Default Cloud SSL Inspection Rule** by name. Predefined/default rules cannot be deleted, and changes to them require admin rank 7. Confirm intent before proceeding; do not silently elevate.

Never improvise around a missing dependency — hand off or stop.

## Action types (what each does)

| Action | Effect on matched SSL/TLS traffic | Common reasons to choose this |
|---|---|---|
| `BLOCK` | The SSL/TLS connection is blocked outright. | Block known-malicious destinations or traffic that should never be allowed regardless of payload. |
| `DECRYPT` | The connection is decrypted and inspected. Downstream URL Filtering, DLP, Sandbox, ATP, etc. policies see the full HTTP payload. | Default for general web browsing where security policy needs full content visibility. |
| `DO_NOT_DECRYPT` | The connection is **not decrypted**. It still flows, and SNI-based policies (URL category, IP, etc.) still apply, but the payload remains opaque. | Privacy-sensitive destinations (banking, healthcare), pinned or non-decryptable apps, regulatory carve-outs. |

The `action` payload is a dict with a `type` field plus optional sub-action settings:

```python
# Simple forms
{"type": "BLOCK"}
{"type": "DECRYPT"}

# Richer DO_NOT_DECRYPT with sub-actions
{
  "type": "DO_NOT_DECRYPT",
  "do_not_decrypt_sub_actions": {
    "bypass_other_policies": True,
    "block_ssl_traffic_with_no_sni_enabled": True,
    "min_tls_version": "SERVER_TLS_1_2"
  }
}
```

## When the admin asks for a schedule

SSL Inspection rules have **no time-of-day attribute**. There is no `time_windows` field on this API. If the admin says "decrypt SSL only during business hours" or "do not decrypt this app after hours", offer one of these alternatives instead of trying to attach a Time Interval:

- **Move the schedule to a Cloud Firewall Filtering rule** that allows/blocks the underlying traffic on a recurring window — the SSL Inspection rule then governs only what's inspected when the firewall lets it through.
- **Move the schedule to a URL Filtering rule** that blocks/cautions/isolates the URL category on a recurring window — the SSL Inspection rule still controls decryption for traffic the URL Filtering layer permits.
- **Use two SSL Inspection rules with different scopes** — e.g. one `DECRYPT` rule scoped to corporate users and one `DO_NOT_DECRYPT` rule scoped to a specific group used during off-hours, with the gating done by group/department membership rather than time.

If the admin insists on a time-of-day SSL Inspection rule, stop and explain the constraint. Do not silently drop the time field and create a 24/7 rule the admin didn't ask for.

## Workflow

### Step 1: Gather requirements from the admin

Required:

- **Rule name** (max 31 characters)
- **Action** — one of `BLOCK`, `DECRYPT`, `DO_NOT_DECRYPT`

At least one matching criterion (otherwise the rule matches nothing useful):

- Cloud applications (e.g. `["ONEDRIVE", "GITHUB"]`)
- URL categories
- Users / groups / departments
- Locations / location groups
- Device trust levels / platforms / user agent types
- Source IP groups / destination IP groups
- ZPA application segments

Optional:

- Description, rank (1-7), order (defaults to bottom of list)

### Step 2: Resolve every named resource (read-before-write)

**Shared rule targets — delegate to `zia-look-up-rule-targets`.** For every user, group, department, location, location group, URL category, device, device group, workload group, or label the admin named, follow `zia-look-up-rule-targets` to get the IDs (or canonical UPPER_SNAKE strings, for `url_categories` — SSL Inspection takes the string form, not numeric IDs). Stop and report if any lookup is empty — never invent IDs, never substitute. (SSL Inspection does **not** support `time_windows` — see "When the admin asks for a schedule" below.)

**SSL-specific fields — resolve here.** The fields below are unique to SSL Inspection and not covered by `zia-look-up-rule-targets`. For each one the admin named, run **one** lookup using the knob below.

| Admin named | Resolution tool | Lookup knob | Returns |
|---|---|---|---|
| Cloud app friendly name (e.g. "OneDrive") | `zia-look-up-cloud-app-name` (skill) | (skill) | canonical names like `ONEDRIVE` |
| Source/Dest IP group name | `zia_list_ip_source_groups` / `zia_list_ip_destination_groups` | `search="<exact>"` | IP group ID |
| ZPA application segment | (resolve via the ZPA tools — `zpa_list_application_segments(search=...)`) | `search="<exact>"` | segment ID |

For cloud applications, the agent has a choice: pass canonical enum tokens (`ONEDRIVE`, `SHAREPOINT_ONLINE`) directly, or pass friendly names ("OneDrive", "share point online") and let the SSL inspection tool auto-resolve via the policy-engine catalog (`resolve_cloud_apps=True` is the default). Prefer canonical enums when the admin already knows them; otherwise let the auto-resolver do the work and surface the resolution audit back to the admin.

### Step 3: Build the action payload

Confirm the admin's action choice (`BLOCK` / `DECRYPT` / `DO_NOT_DECRYPT`) and any sub-action settings (TLS minimum version, SNI handling, bypass behaviour) before issuing the create. The action payload is an explicit dict, not a string:

```python
action = {"type": "DO_NOT_DECRYPT",
          "do_not_decrypt_sub_actions": {
              "bypass_other_policies": True,
              "block_ssl_traffic_with_no_sni_enabled": True,
              "min_tls_version": "SERVER_TLS_1_2",
          }}
```

### Step 4: Create the rule

Call:

```text
zia_create_ssl_inspection_rule(
    name=<name>,
    action=<action dict>,
    description=<optional>,
    enabled=True,
    rank=<1-7, optional>,
    order=<optional, defaults to bottom>,
    cloud_applications=[...],          # canonical enums or friendly names
    url_categories=[...],
    groups=[...],
    users=[...],
    locations=[...],
    location_groups=[...],
    source_ip_groups=[...],
    dest_ip_groups=[...],
    device_trust_levels=[...],
    platforms=[...],
    user_agent_types=[...],
    labels=[...],
    zpa_app_segments=[...],            # only for Source IP Anchoring
)
```

Note: the SSL Inspection tool does **not** accept a `time_windows` parameter — it is not part of this rule type.

Capture the returned `id`.

### Step 5: Activate the configuration

ZIA changes are staged until activation. After every successful create, run:

```text
zia_activate_configuration()
```

Tell the admin: "Rule created (ID `<id>`) and activated." If activation fails, surface the error — the rule exists but is not live.

### Step 6: Echo back what was applied

Confirm in plain language:

- The rule name and action type (`BLOCK` / `DECRYPT` / `DO_NOT_DECRYPT`)
- Each scoping dimension that was applied (one bullet per — apps, categories, users, locations, etc.)
- Any sub-action settings on `DO_NOT_DECRYPT` (TLS min version, SNI handling)
- The activation status

Don't restate operand IDs or internal field names that the admin doesn't need to see.

## Quick Reference

**Tools used:**

- Read: `zia_list_ssl_inspection_rules(search=...)` — only on explicit admin request for ordering / duplicate checks
- Write: `zia_create_ssl_inspection_rule(name, action, ...)`
- Activation: `zia_activate_configuration()`

**Related ID-resolution tools (one call per resource, exact name):**

- `zia_list_url_categories`, `zia_list_user_groups`, `zia_list_user_departments`, `zia_list_users`, `zia_list_locations`, `zia_list_ip_source_groups`, `zia_list_ip_destination_groups`, `zia_list_rule_labels`

### Related skills

- `zia-audit-ssl-inspection-bypass` — read-only audit of existing SSL Inspection rules. Use when the admin asks "show me what's bypassing SSL inspection" rather than "create a new SSL Inspection rule".
- `zia-look-up-cloud-app-name` — used silently when friendly cloud-app names are passed in. Pre-resolves "OneDrive" → `ONEDRIVE`.

**Different ZIA rule types — do not chain through this skill:**

- `zia-create-firewall-filtering-rule` — Cloud Firewall is a separate resource type. If the admin wants schedule-based filtering, this is a likely destination for the schedule.
- `zia-create-url-filtering-rule` — URL Filtering is a separate resource type. Supports `time_windows` natively, so it's the right place when the admin wants time-of-day URL category enforcement.
- DLP / Sandbox / Cloud App Control / File Type Control — also separate resource types.

**No schedule support on this rule type.** SSL Inspection has no `time_windows` attribute. If the admin asks for time-of-day enforcement, redirect the schedule to Cloud Firewall Filtering or URL Filtering rather than attempting to attach a Time Interval here.

**Don't pre-list rules before creating.** Skip `zia_list_ssl_inspection_rules` unless the admin explicitly asks about ordering or wants to inspect existing rules — direct create + activate is the default flow.
