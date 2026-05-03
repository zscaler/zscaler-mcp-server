---
name: zia-create-firewall-filtering-rule
description: "Create a ZIA Cloud Firewall Filtering rule that controls network traffic by source/destination IP, country, network application, network service, device trust level, user/group/department, location, and optional time-of-day schedule (Time Interval). Supported actions: ALLOW, BLOCK_DROP, BLOCK_RESET, BLOCK_ICMP, EVAL_NWAPP. Use when an admin asks to 'create a firewall rule', 'block traffic to X', 'allow traffic from Y', 'block country Z', 'restrict access during business hours', or 'add a firewall exception'. This skill creates exactly one Cloud Firewall rule and chains to `zia-manage-time-interval` when the admin's request includes a recurring schedule."
---

# ZIA: Create Cloud Firewall Filtering Rule

## How to talk to the admin

- Don't narrate tool calls, search filters, or internal lookup logic. Just confirm what was created and which scoping was applied.
- Empty list responses are authoritative. If a `zia_list_*` lookup returns no match for an exact-name search, treat the resource as "does not exist." Do not retry with split keywords or unfiltered listings.
- Don't claim a tool doesn't exist without checking. If `zia_create_*` and `zia_get_*` are visible for a resource, the matching `zia_list_*` exists too.
- Don't narrate strategy pivots. If you have to retry quietly, retry quietly and report only the final outcome.
- After every successful create, **mention the activation step explicitly** — ZIA changes are staged until activated. The agent must call `zia_activate_configuration()` and tell the admin the change is now live.

## Scope of this skill

This skill creates **one** Cloud Firewall Filtering rule per invocation. Anything outside that scope is a hard stop:

- **It does not create** the auxiliary objects the rule references (IP source/destination groups, network service groups, network app groups, location groups, label IDs, group/department/user IDs). If those don't exist, this skill stops and points the admin at the right place to create them — it does not improvise.
- **It does not modify SSL Inspection, URL Filtering, DLP, or any other ZIA rule type.** Those are separate resource types and have their own skills (`zia-create-ssl-inspection-rule` for SSL Inspection).
- **It does not enforce DNS or IPS rules.** Cloud Firewall DNS rules and IPS rules are separate APIs (`cloud_firewall_dns_rules`, `cloud_firewall_ips_rules`) — not what this skill creates.

## Hard stop conditions

Stop and report plainly when:

- **The admin's stated IP groups, network services, network app groups, location names, or user/group IDs cannot be resolved.** Resolve once via the appropriate `zia_list_*` tool; if empty, say so and stop. Do not skip the field, do not invent IDs.
- **A recurring schedule was requested but no schedule details were provided.** Don't guess. Ask once for `start_time`, `end_time`, and `days_of_week`, then chain to `zia-manage-time-interval`.
- **An action was requested that doesn't exist on this rule type.** Valid actions are exactly: `ALLOW`, `BLOCK_DROP`, `BLOCK_RESET`, `BLOCK_ICMP`, `EVAL_NWAPP`. Plain `BLOCK` is not a valid value — pick one of the three block variants based on the desired client-visible behaviour. SSL-inspection-style actions (`DO_NOT_DECRYPT`, `DO_NOT_INSPECT`, `INSPECT`, `BYPASS`) belong to other rule types and are a hard stop here.
- **The admin is trying to modify the predefined Default Cloud IPS Rule** by name. Predefined/default rules cannot be deleted, and changes to them require admin rank 7. Confirm intent before proceeding.
- **The admin asked for a country-based rule but only gave a country name.** ZIA expects ISO 3166 Alpha-2 codes (`US`, `CA`, `BR`, etc.). Resolve common phrasings to the canonical code; if ambiguous, ask once.
- **`rank` is outside the inclusive range `0..7`.** ZIA's Cloud Firewall rank is a 0-7 integer; the tool will reject any other value before the API call. See [admin rank documentation](https://help.zscaler.com/zia/about-admin-rank).

Never improvise around a missing dependency — hand off or stop.

## Action types (what each does)

| Action | Effect on matched traffic | Common reasons to choose this |
|---|---|---|
| `ALLOW` | Permit the traffic. Other downstream policies (URL filtering, DLP, SSL inspection, etc.) may still apply. | Explicit allowlist for known-good destinations or services. |
| `BLOCK_DROP` | Silently drop the packet. The client gets no signal — the connection just times out. | Quietly block disallowed traffic without revealing that a firewall is in the path; reduces information leakage to attackers. |
| `BLOCK_RESET` | Drop the packet and send a TCP RST back to the source. The client's connection fails immediately with a reset. | Fast-fail block for end-user-facing traffic where a quick error is preferable to a hung connection. TCP only. |
| `BLOCK_ICMP` | Drop the packet and return an ICMP unreachable to the source. | Make the block visible at the network layer — useful for traceroutes and diagnostic tooling, or where applications expect a network-level error. Works for non-TCP protocols too. |
| `EVAL_NWAPP` | Defer the action: evaluate the connection against the Network Application rules instead of taking a final action here. | Use when the rule should hand off to `nw_applications` / `nw_application_groups` based filtering downstream. Pair this action with rules that have a populated network-application scope. |

**Picking between the three BLOCK variants:**

- Plain `BLOCK` does **not** exist on this API. Always pick the variant that matches the desired client-visible behaviour.
- Default to `BLOCK_DROP` unless the admin specifically wants the client to see a fast failure (`BLOCK_RESET`) or a network-level error (`BLOCK_ICMP`).
- `BLOCK_RESET` is TCP-only by definition (RST is a TCP flag). For UDP/ICMP, use `BLOCK_DROP` or `BLOCK_ICMP`.

## Workflow

### Step 1: Gather requirements from the admin

Required:

- **Rule name**
- **Action** — one of `ALLOW`, `BLOCK_DROP`, `BLOCK_RESET`, `BLOCK_ICMP`, `EVAL_NWAPP` (see the action table above for which variant to pick)
- **`order`** — 1-based position in the evaluation sequence. ZIA's Cloud Firewall API rejects create payloads without `order`. Pick the position deliberately based on the desired rule ordering (e.g. ALLOW above BLOCK when both target overlapping traffic). The tool defaults to `1` (top) when omitted, but the agent should set it explicitly whenever creating more than one rule in a session.
- **`rank`** — admin rank, integer in the inclusive range `0..7`. ZIA's Cloud Firewall API rejects create payloads without `rank`. The tool defaults to `7` (highest) when omitted; this matches ZIA's documented default. See [admin rank documentation](https://help.zscaler.com/zia/about-admin-rank) for what each level controls.

At least one matching criterion (otherwise the rule is too broad to be useful):

- Source IPs / source IP groups / source countries
- Destination addresses / destination IP groups / destination IPv6 groups / destination countries / destination IP categories
- Network applications / network application groups
- Network services / network service groups / app services / app service groups
- Users / groups / departments
- Locations / location groups
- Device trust levels
- Devices / device groups
- A time-of-day window (Time Interval)

Optional:

- Description, rank (1-7), order (defaults to bottom of list), `enable_full_logging`, `exclude_src_countries`

### Step 2: Resolve every named resource (read-before-write)

**Shared rule targets — delegate to `zia-look-up-rule-targets`.** For every user, group, department, location, location group, device, device group, workload group, label, or time interval the admin named, follow `zia-look-up-rule-targets` to get the IDs. Stop and report if any lookup is empty — never invent IDs, never substitute, never narrate the lookup. (Cloud Firewall accepts every shared rule-target field listed in that skill.)

**Firewall-specific fields — resolve here.** The fields below are unique to Cloud Firewall and not covered by `zia-look-up-rule-targets`. For each one the admin named, run **one** lookup using the knob below. Empty result = does not exist. Don't retry with broader filters.

| Admin named | Resolution tool | Lookup knob | Returns |
|---|---|---|---|
| Network service name | `zia_list_network_services` | **`name="<literal>"`** (case-insensitive substring; client-side) | network service ID |
| Source IP group name | `zia_list_ip_source_groups` | `search="<exact>"` | source group ID |
| Destination IP group name | `zia_list_ip_destination_groups` | `search="<exact>"` | destination group ID |
| Network service group name | `zia_list_network_services_group` | `search="<exact>"` | network service group ID |
| Network app group name | `zia_list_network_app_groups` | `search="<exact>"` | network app group ID |
| Network app name | `zia_list_network_apps` | `search="<exact>"` | network app token |
| Country name (free-text) | look up ISO 3166 Alpha-2 silently (e.g. "United States" → `US`) | (offline) | country code |

Do not skip a field that the admin named because lookup failed — the skill stops, the admin fixes the naming or creates the missing object first.

**Why `name=` and not `search=` for network services:** ZIA's canonical names are uppercase enums (`HTTP`, `FTP`, `DNS`, ...). Server-side `search="http"` does NOT match `HTTP`. The tool's `name=` parameter normalizes casing client-side, so `name="http"` reliably finds the predefined `HTTP` service. (The same caveat applies to user groups; `zia-look-up-rule-targets` documents it for that field.)

### Step 3: Resolve the schedule (only if the admin asked for time-of-day scoping)

If the admin's request includes any time-of-day language ("during business hours", "after hours", "weekends only", "between 8am-5pm Mon-Fri", "block this country at night", etc.), **chain to `zia-manage-time-interval`** to find or create the Time Interval and obtain its `interval_id`. That ID becomes the `time_windows=[<id>]` value on the firewall rule.

If the admin did not mention a schedule, leave `time_windows` unset. Don't invent a default.

Do **not** call `zia_activate_configuration()` from within `zia-manage-time-interval` when chaining — defer activation to the end of this skill so a single activation flushes both the new Time Interval and the new firewall rule.

### Step 4: Build the payload

Map admin language to canonical fields:

- "block country X" → `dest_countries=["XX"]` with `rule_action="BLOCK_DROP"` (or `BLOCK_RESET` / `BLOCK_ICMP` if the admin wants a visible error)
- "block traffic FROM country X" → `source_countries=["XX"]` with a block action
- "exception for these source countries" → `source_countries=[...]` plus `exclude_src_countries=True`
- "block IP range A.B.C.D/24" → `src_ips=["A.B.C.D/24"]` (raw CIDR, no group needed) or `source_ip_groups=[<id>]` if a named group is preferred
- "block traffic to bad-IP-list-1" → `dest_ip_groups=[<id>]` after resolving the group name
- "block but make sure clients see a fast failure" → `rule_action="BLOCK_RESET"` (TCP only)
- "block silently / fail closed without telling the client" → `rule_action="BLOCK_DROP"`
- "block but return a network-layer error" → `rule_action="BLOCK_ICMP"`
- "evaluate against the network-app rules" / "let the nw-app catalog decide" → `rule_action="EVAL_NWAPP"`
- "log everything" → `enable_full_logging=True`

### Step 5: Create the rule

Call:

```text
zia_create_cloud_firewall_rule(
    name=<name>,
    rule_action="ALLOW" | "BLOCK_DROP" | "BLOCK_RESET" | "BLOCK_ICMP" | "EVAL_NWAPP",
    description=<optional>,
    enabled=True,
    rank=<0-7, default 7>,                     # always send; tool defaults to 7
    order=<1-based position, default 1>,       # always send; tool defaults to 1 (top)
    src_ips=[...],
    dest_addresses=[...],
    source_countries=[...],          # ISO 3166 Alpha-2 codes
    dest_countries=[...],
    exclude_src_countries=<bool>,
    dest_ip_categories=[...],
    device_trust_levels=[...],
    nw_applications=[...],
    enable_full_logging=<bool>,
    app_services=[...],
    app_service_groups=[...],
    departments=[...],
    dest_ip_groups=[...],
    dest_ipv6_groups=[...],
    devices=[...],
    device_groups=[...],
    groups=[...],
    labels=[...],
    locations=[...],
    location_groups=[...],
    nw_application_groups=[...],
    nw_services=[...],
    nw_service_groups=[...],
    time_windows=[<interval_id>],    # only if schedule was requested
    users=[...],
)
```

Capture the returned `id`.

### Step 6: Activate the configuration

ZIA changes are staged until activation. After every successful create, run:

```text
zia_activate_configuration()
```

Tell the admin: "Firewall rule created (ID `<id>`) and activated." If activation fails, surface the error — the rule exists but is not live.

### Step 7: Echo back what was applied

Confirm in plain language:

- The rule name and action
- Each scoping dimension that was applied (one bullet per — sources, destinations, services, users, schedule, etc.)
- The interval ID if a schedule was attached, with the schedule in human form ("08:00-17:00 Mon-Fri")
- The activation status

Don't restate operand IDs or internal field names that the admin doesn't need to see.

## Quick Reference

**Tools used:**

- Read: `zia_list_cloud_firewall_rules(search=...)` — only on explicit admin request for ordering / duplicate checks
- Write: `zia_create_cloud_firewall_rule(name, rule_action, ...)`
- Activation: `zia_activate_configuration()`

**Schedule sub-skill:**

- `zia-manage-time-interval` — chain whenever the admin's request mentions time-of-day or day-of-week.

**Related ID-resolution tools:**

- **Shared rule targets** (users, groups, departments, locations, location groups, devices, device groups, workload groups, labels, time windows): handled by `zia-look-up-rule-targets`.
- **Firewall-specific operands** (IP groups, network services, network apps, etc.): `zia_list_ip_source_groups`, `zia_list_ip_destination_groups`, `zia_list_network_services`, `zia_list_network_services_group`, `zia_list_network_app_groups`, `zia_list_network_apps`.

### Related skills

- `zia-look-up-rule-targets` — shared name-to-ID lookups for users, groups, departments, locations, location groups, URL categories, devices, device groups, workload groups, labels, and time windows. Chain to it from Step 2.
- `zia-manage-time-interval` — find-or-create helper for schedule scoping (see Step 3).
- `zia-onboard-location` — upstream dependency when locations referenced by the rule don't exist yet.

**Different ZIA rule types — do not chain through this skill:**

- `zia-create-ssl-inspection-rule` — SSL Inspection is a separate resource type. Even if the admin wants both a Cloud Firewall rule *and* an SSL Inspection rule with the same scope, treat them as two independent requests; this skill creates only the firewall rule.
- DLP / URL Filtering / Sandbox / Cloud Firewall DNS / Cloud Firewall IPS rules — also separate resource types.

**Typical chain when a schedule is requested:**

```text
zia-manage-time-interval           (find or create the Time Interval, return its ID)
        ↓
zia-create-firewall-filtering-rule (this skill — attach the interval ID and create the rule)
        ↓
zia_activate_configuration()       (one activation flushes both)
```

**Don't pre-list rules before creating.** Skip `zia_list_cloud_firewall_rules` unless the admin explicitly asks about ordering or wants to inspect existing rules — direct create + activate is the default flow.
