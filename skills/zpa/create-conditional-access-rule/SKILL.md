---
name: zpa-create-conditional-access-rule
description: "Create a ZPA Access Policy rule that gates access to a private application on multiple combined checks: identity (SCIM group / SAML), one or more named device posture profiles (associated by UDID; ZPA does not introspect what each profile checks), platform reported by ZCC, country, and risk-score level. Use when an admin asks for 'conditional access', 'multi-check access rule', 'attach posture profile X and risk level low to this rule', or 'allow only if posture passes and risk is low' for a private application. For session-duration / re-auth requirements, see `zpa-create-session-duration-rule` (separate ZPA resource type)."
---

# ZPA: Create Conditional Access Rule (Multi-Check)

## Keywords

conditional access, multi-check access rule, layered access rule, identity + posture + platform + risk, attach posture profile to rule, attach risk score to rule, secure remote access SSH, internal app conditional access

## How to talk to the admin (read this before you respond)

The admin is asking a **business question** — *"can you build this access rule?"*. Tool plumbing is internal optimization the admin does not care about.

- **Plain language only.** Translate tool output into the answer the admin wanted. Don't paste back JMESPath expressions, `search` keys, projections, validation errors, Pydantic messages, or SDK tuple shapes.
- **Empty is authoritative — do not fan out retries.** A `zpa_list_*` call with `search="<exact name>"` is a server-side substring match on the resource's `name` field. **An empty result means the resource does not exist by that name. Stop.** Do NOT then re-call the same tool with split keywords, broader JMESPath projections, larger `page_size`, or no filter "to double-check". Each of those costs a round trip and adds zero information. The single allowed follow-up is asking the admin to clarify the name (see Hard Stops below).
  - ❌ Five calls: `search="DataCenter Switches SSH"` → empty → `query="[?contains(name,'DataCenter') || contains(name,'SSH')]"` → `query="[*].{id,name}", page_size=200` → unfiltered list → "let me drop the projection in case it's too aggressive".
  - ✅ One call: `search="DataCenter Switches SSH"` → empty → *"I can't find an application segment named `DataCenter Switches SSH`. Want me to use a different name?"*
- **Don't narrate strategy pivots.** If you do retry (only when allowed), do it quietly. Report only the final answer.
  - ❌ *"The `search` filter came back empty. The tool's `search` may not be a substring match. Let me list without the filter and apply JMESPath instead so I'm not relying on server-side fuzzy matching."*
  - ✅ *"I didn't find an application segment named `Example100`. Want me to use a different name, or list the segments that do exist?"*
- **Don't claim a tool doesn't exist without checking.** If a `zpa_get_*` / `zpa_create_*` is visible, the matching `zpa_list_*` almost certainly exists too. Examples that have been wrongly mis-claimed missing: `zpa_list_app_connector_groups`, `zpa_list_segment_groups`, `zpa_list_application_segments`.
- **Don't enumerate gaps the admin didn't ask about.** Mention a limitation only when it's about to block what the admin actually requested.

## Overview

This is the opinionated skill for the **conditional-access** scenario:
**identity + posture (often multiple) + platform + risk + country, all
AND-ed together**, gating access to a single internal application or
app segment.

It is **narrower and more opinionated** than the general-purpose
`zpa-create-access-policy-rule` skill. Use this skill when the request
explicitly combines several of: SCIM group / SAML attribute, device
posture profile(s), platform restriction, country restriction, and
risk-score level.

For arbitrary or simpler ZPA access rules, use `zpa-create-access-policy-rule`.

---

## What this skill supports

The agent does **not** introspect or verify what any of these operands
actually check on the device. ZPA Access Policy attaches operand
references (UDIDs, attribute IDs, OS names, country codes, score
levels) and trusts the truth value the ZCC client reports back when
the rule is evaluated. Re-authentication is **not** an Access Policy
concern — it is a separate ZPA Timeout Policy feature.

| Requirement | Operand | What the agent does |
|---|---|---|
| User in a specific SCIM group | `SCIM_GROUP` | Resolves the group name via `get_zpa_scim_group` (returns `idp_id` + group id) and attaches both. |
| User matches a SAML attribute | `SAML` | Resolves the attribute ID via `get_zpa_saml_attribute` and attaches with the value to match. |
| Associate a named device posture profile (e.g. "Enterprise PKI Certificate", "CrowdStrike EDR Active") | `POSTURE` (one block per profile when AND-ing — see note below) | Resolves the profile UDID by name via `get_zpa_posture_profile` and attaches `lhs=<udid>`, `rhs="true"`. The agent does **not** describe or validate what the profile checks — that lives entirely inside ZCC and is opaque to ZPA. |
| Operating system reported by the ZCC client | `PLATFORM` | Single operand: `lhs` ∈ {`windows`, `mac`, `linux`, `ios`, `android`}, `rhs="true"`. ZPA does not inspect anything else about the OS — no version, no patch level. |
| Country restriction | `COUNTRY_CODE` | ISO 3166 Alpha-2 codes; one entry per country. ZPA derives country from source IP. |
| Associate one or more risk-score levels with the rule | `RISK_FACTOR_TYPE` | `lhs="ZIA"`, `rhs` ∈ {`UNKNOWN`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`}. The score itself is computed elsewhere by Zscaler; the rule simply lists which levels are accepted. |
| Application = a specific private app segment | `APP` or `APP_GROUP` | Resolved via `zpa_list_application_segments` / `zpa_list_segment_groups` *by name*. |

### AND vs OR — get this right or the rule will be wrong

ZPA condition semantics:

- **Multiple condition blocks at the top level → ANDed.**
- **Multiple `entry_values` (or `values`) inside one block → ORed.**

This matters most for **POSTURE**. To require *"posture profile A
passes **AND** posture profile B passes"*, the agent **must create two
separate POSTURE condition blocks** — one per profile — not two
entries inside a single block. A single block with both entries means
"**either** A **or** B", which is almost never what the admin wants.

For COUNTRY_CODE (allow US **or** CA) or PLATFORM (Windows **or** Mac),
multiple entries in one block is correct, because OR is the desired
semantics there.

---

## Workflow

### Step 1: Confirm the admin's inputs

- **Application** — the name of the existing app segment (or segment
  group) the rule protects.
- **Identity scope** — SCIM group(s) or SAML attribute(s).
- **Posture profile names** required — list every profile that must
  pass. Each becomes its own `POSTURE` condition block.
- **Platform restriction** — which operating systems are allowed.
- **Country restriction** — ISO 3166 Alpha-2 codes (optional).
- **Risk-score levels** allowed — typical: `UNKNOWN` and `LOW`.
- **Action** — almost always `ALLOW` for this pattern.

---

### Step 2: Resolve IDs (read-before-write)

**One call per resource, with a `search` parameter set to the admin's
exact name. Empty result = resource does not exist; jump to the Hard
Stops below. Do not retry with broader filters or no filter.**

Run these in parallel where possible:

```text
get_zpa_scim_group(search="<group_name>")
get_zpa_posture_profile(search="<posture_profile_name>")  # repeat per profile
zpa_list_application_segments(search="<app_segment_name>")  # or zpa_list_segment_groups(search="<segment_group_name>")
```

If the admin gave a SAML email/attribute instead of a SCIM group, also
run `get_zpa_saml_attribute(search=<name>)`.

**Hard stop conditions** — if any of these fire, do NOT proceed to
write. Stop, ask the admin in **plain language**, do not narrate which
filter / search / projection you tried:

- The named application segment was not found. **Do not improvise a
  segment inline from this skill.** App segments depend on a chain
  (App Connector Group → Server Group → Segment Group → App Segment),
  and that chain is owned by the `zpa-onboard-application` skill. Two
  valid paths:
  1. *"I can't find an application segment named `<name>`. Want me to
     use a different existing segment?"* — and proceed when the admin
     names one that does exist.
  2. *"I can't find an application segment named `<name>`. To create
     it, I'll hand off to the `zpa-onboard-application` skill first
     (it walks the connector-group → server-group → segment-group →
     app-segment chain), then come back here to attach the
     conditional-access rule. Want me to proceed?"* — and on yes,
     trigger `zpa-onboard-application`, then resume Step 3 of this
     skill with the new app segment ID.
- The named SCIM group was not found. SCIM groups are provisioned from
  the IdP, not via MCP. Phrase it as: *"I can't find a SCIM group
  named `<name>`. Should I check a different IdP / spelling?"*
- A named posture profile was not found in ZCC. Posture profiles can
  only be created in the ZCC portal — there is no API and no MCP tool
  for that. Phrase it as: *"The posture profile `<name>` doesn't exist
  in this tenant. It needs to be created in the ZCC admin portal first."*

**Never improvise around a missing dependency.** If the admin insists
"just create it inline anyway," still hand off to the right skill —
that skill enforces the dependency chain and the per-resource business
rules (e.g. `dynamic_discovery=False ⇒ server_ids required` on server
groups, `enrollment_cert_id` resolution on connector groups). Doing it
inline from this skill bypasses those guards.

---

### Step 3: Build the conditions payload

Apply the AND-vs-OR rules above. The conditional-access pattern almost
always wants:

- **AND** across operand types (identity AND posture AND platform AND risk AND country)
- **AND** across multiple posture profiles (one POSTURE block per profile)
- **OR** within a single operand block (Windows OR Mac; US OR CA; LOW OR UNKNOWN risk levels)

Reference template (replace placeholders; drop any block the admin did
not request):

```json
[
  {
    "operator": "OR",
    "operands": [
      { "object_type": "APP", "values": ["<app_segment_id>"] }
    ]
  },
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "SCIM_GROUP",
        "entry_values": [
          { "lhs": "<idp_id>", "rhs": "<scim_group_id>" }
        ]
      }
    ]
  },
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "POSTURE",
        "entry_values": [
          { "lhs": "<posture_udid_A>", "rhs": "true" }
        ]
      }
    ]
  },
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "POSTURE",
        "entry_values": [
          { "lhs": "<posture_udid_B>", "rhs": "true" }
        ]
      }
    ]
  },
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "PLATFORM",
        "entry_values": [
          { "lhs": "windows", "rhs": "true" }
        ]
      }
    ]
  },
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "COUNTRY_CODE",
        "entry_values": [
          { "lhs": "US", "rhs": "true" },
          { "lhs": "CA", "rhs": "true" }
        ]
      }
    ]
  },
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "RISK_FACTOR_TYPE",
        "entry_values": [
          { "lhs": "ZIA", "rhs": "UNKNOWN" },
          { "lhs": "ZIA", "rhs": "LOW" }
        ]
      }
    ]
  }
]
```

Note the **two separate POSTURE blocks** above. Putting both posture
UDIDs into a single block would mean *"A **or** B"*, not *"A **and**
B"* — a silent logic bug that lets in devices missing one of the
required profiles.

---

### Step 4: Create and verify

Go straight to create. Do **not** pre-list existing rules — new ZPA
access rules are appended at the end of the policy by default, and
listing every existing rule before every create adds round trips,
gives no useful information for the typical case, and invites
fan-out retries when the list comes back empty on a fresh tenant.

```text
zpa_create_access_policy_rule(
  name="<rule_name>",
  action_type="ALLOW",
  description="<short description>",
  conditions=<conditions_payload from Step 3>
)

zpa_get_access_policy_rule(rule_id="<returned_rule_id>")
```

In the response, echo back which conditions were applied (one bullet
per condition block) using the operand names and values, not narrative
claims about what the operands do on the device.

If the admin's request also mentioned a re-authentication interval,
session expiry, or idle timeout, that requirement belongs to ZPA
**Timeout Policy** — a separate resource type from Access Policy. Do
not add it through this skill. Mention the boundary plainly and point
the admin at `zpa-create-timeout-policy-rule` (or its session-duration
variant `zpa-create-session-duration-rule`).

**Optional ordering check (only if the admin explicitly asks).** If
the admin wants the rule placed somewhere other than the end of the
policy, *then* run `zpa_list_access_policy_rules()` once and reorder
afterward. Otherwise, accept the default append-at-end placement and
move on.

---

## Quick reference

### Tools used

- `get_zpa_scim_group(search)` — identity lookup (returns `idp_id` + `scim_group_id`)
- `get_zpa_saml_attribute(search)` — SAML attribute lookup (alternative to SCIM)
- `get_zpa_posture_profile(search)` — posture UDID lookup (run once per profile)
- `zpa_list_application_segments(search="<name>")` / `zpa_list_segment_groups(search="<name>")` — application scope
- `zpa_create_access_policy_rule(name, action_type, conditions, ...)` — write (no pre-flight needed)
- `zpa_get_access_policy_rule(rule_id)` — verify
- `zpa_list_access_policy_rules()` — **only** when the admin explicitly asks about rule ordering

### Related skills (chain these, don't reinvent them)

- `zpa-onboard-application` — **upstream dependency.** Owns the full
  chain: App Connector Group → Server Group → Segment Group → App
  Segment. Trigger this *first* if the named app segment does not yet
  exist; resume this skill afterward with the new segment ID.
- `zpa-create-server-group` — narrower than onboarding; covers just
  the server-group + connector-group prerequisites if everything else
  already exists.
- `zpa-create-access-policy-rule` — general-purpose access-rule skill;
  use that for arbitrary access rules that don't follow the multi-check
  conditional-access pattern.

**Different ZPA resource types — do not chain through this skill:**

- `zpa-create-timeout-policy-rule` / `zpa-create-session-duration-rule`
  — ZPA **Timeout Policy** is a separate resource type from Access
  Policy. Re-authentication intervals, session expiry, and idle
  timeouts live there, not here. If the admin asked for both an access
  rule and a session timeout, treat them as two independent requests
  and route the timeout half to the appropriate timeout-policy skill.

**Typical end-to-end chain for a new application + conditional access:**

```text
zpa-onboard-application       (creates connector group, server group,
                               segment group, app segment, base access rule)
        ↓
zpa-create-conditional-access-rule  (this skill — adds identity + posture +
                                     platform + risk + country gating)
```
