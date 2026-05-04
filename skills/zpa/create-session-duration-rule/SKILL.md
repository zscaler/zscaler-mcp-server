---
name: zpa-create-session-duration-rule
description: "Create a ZPA Timeout Policy rule that enforces session duration — i.e. forces re-authentication after N minutes/hours/days, optionally with an idle-timeout. Use this skill when an admin asks for 'session duration', 'auto-revoke', 're-authentication interval', 'force re-auth after X hours', or 'session must expire after a workday' for ZPA. Scopes by SCIM group, SAML attribute, application segment, platform, and posture. ZPA Timeout Policy is a separate resource type from Access Policy; this skill creates timeout rules only and does not modify or pair with access rules."
---

# ZPA: Create Session-Duration Rule (Timeout Policy)

## Keywords

session duration, session timeout, force re-authentication, re-auth interval, auto-revoke session, session expiry, idle timeout, refresh posture, refresh risk

## How to talk to the admin (read this before you respond)

The admin is asking a **business question** — *"force re-auth after N hours"*. Tool plumbing is internal optimization the admin does not care about.

- **Plain language only.** Translate tool output into the admin's terms ("session expires after 4 hours; idle sessions disconnect after 15 minutes"). Don't paste back JMESPath expressions, `search` keys, projections, validation errors, or SDK tuple shapes.
- **Empty is authoritative — do not fan out retries.** A `zpa_list_*` call with `search="<exact name>"` is a server-side substring match on the resource's `name` field. **An empty result means the resource does not exist by that name. Stop.** Do NOT then re-call the same tool with split keywords, broader JMESPath projections, larger `page_size`, or no filter "to double-check". The single allowed follow-up is asking the admin to clarify the name (see Hard Stops).
  - ❌ Five calls (search → split keywords → projection → unfiltered → "drop the projection in case it's too aggressive").
  - ✅ One call → empty → *"I can't find an application segment named `<name>`. Want me to use a different name?"*
- **Don't narrate strategy pivots.** If you do retry (only when allowed), do it quietly and report only the final answer.
- **Don't claim a tool doesn't exist without checking.** If `zpa_get_*` / `zpa_create_*` for a resource is visible, the matching `zpa_list_*` almost certainly exists too.
- **Don't invent a recurring schedule.** ZPA Timeout Policy is a session-length policy, not a clock-based schedule. If the admin asks for "block access after 6pm" or "only on weekdays", say so plainly and stop — that requirement belongs to a different product surface.

## Overview

Use this skill when the admin needs ZPA to force re-authentication
after a set period — phrased as "session must expire after N hours",
"auto-revoke after a workday", "force re-auth every 4 hours", or any
similar **session-length** ask.

ZPA models this as a **Timeout Policy** rule. Timeout Policy is a
separate resource type from Access Policy: this skill creates only
the timeout rule and **does not** create, modify, or depend on any
access rule. If the admin also asked for identity / posture / platform
gating on the same app, that is a separate Access Policy request and
must be handled independently (see `zpa-create-conditional-access-rule`
or `zpa-create-access-policy-rule`).

This skill is **narrower and more opinionated** than the
general-purpose `zpa-create-timeout-policy-rule` skill — it focuses on
the common session-duration shape (single SCIM group / SAML attribute,
single app segment, optional posture and platform). For arbitrary
timeout rules outside that shape, use `zpa-create-timeout-policy-rule`.

---

## What "session duration" means in ZPA

ZPA Timeout Policy gates **how long a session lives** before the user
must re-authenticate. When re-auth happens, ZPA re-evaluates every
applicable Access Policy rule against the user's session — there is
no "paired" access rule; the Access and Timeout policies are
independent rule sets that just happen to apply to the same session.
A 4-hour timeout therefore means *every applicable access rule is
re-evaluated at most every 4 hours*, even for an already-connected
user.

This is a **session-length** policy, not a clock-based schedule.
Once a user authenticates they stay connected for N units regardless
of clock time.

---

## Parameters

### `reauth_timeout` (session length)

Forces re-auth after the specified period regardless of activity.

| Format | Examples |
|---|---|
| `"<N> Minutes"` | `"30 Minutes"`, `"60 Minutes"` |
| `"<N> Hours"` | `"4 Hours"`, `"8 Hours"` |
| `"<N> Days"` | `"1 Days"`, `"10 Days"`, `"30 Days"` |
| `"Never"` | sessions never expire |

Minimum: 10 minutes.

### `reauth_idle_timeout` (idle timeout)

Terminates an inactive session after the specified period.

| Format | Examples |
|---|---|
| `"<N> Minutes"` | `"10 Minutes"`, `"30 Minutes"` |
| `"<N> Hours"` | `"1 Hours"`, `"2 Hours"` |
| `"<N> Days"` | `"1 Days"` |
| `"Never"` | idle never disconnects |

Minimum: 10 minutes.

### Action

Always `RE_AUTH` (the only supported action).

---

## Workflow

### Step 1: Confirm scope (mirror the access rule)

The timeout rule should **scope to the same identity + application** as
the access rule it pairs with so re-auth is enforced for the same
population.

- **Application** — same app segment / segment group as the access rule.
- **Identity scope** — same SCIM group / SAML attribute as the access rule.
- **Session length** — `reauth_timeout` (e.g. `"4 Hours"`).
- **Idle timeout** — `reauth_idle_timeout` (e.g. `"15 Minutes"`).

If the admin scoped the access rule on **POSTURE** or **PLATFORM** as
well, you may scope the timeout rule on the same — both are valid
operands here too.

---

### Step 2: Resolve IDs (read-before-write)

If any IDs (SCIM group, SAML attribute, app segment, posture profile)
were already looked up earlier in the same session — for example by an
unrelated Access Policy skill the admin ran first — reuse those IDs
to avoid redundant calls. Otherwise:

**One call per resource, with a `search` parameter set to the admin's
exact name. Empty result = resource does not exist; jump to the Hard
Stops below. Do not retry with broader filters or no filter.**

```text
get_zpa_scim_group(search="<group_name>")
zpa_list_application_segments(search="<app_segment_name>")  # or zpa_list_segment_groups(search="<segment_group_name>")
get_zpa_posture_profile(search="<posture_profile_name>")  # if scoping on posture
```

**Hard stop conditions** — if the named application segment, SCIM
group, or posture profile cannot be found, do NOT proceed. Stop, ask
the admin in **plain language**, do not narrate which filter / search
/ projection you tried:

- The named application segment was not found. **Do not improvise a
  segment inline from this skill.** Two valid paths:
  1. *"I can't find an application segment named `<name>`. Want me to
     use a different existing segment?"*
  2. *"I can't find an application segment named `<name>`. To create
     it I'll hand off to `zpa-onboard-application` first (it walks
     the connector-group → server-group → segment-group → app-segment
     chain), then come back here for the timeout rule. Want me to
     proceed?"*
- *"I can't find a SCIM group named `<name>`. Should I check a
  different IdP / spelling?"*
- *"The posture profile `<name>` doesn't exist in this tenant. It
  needs to be created in the ZCC admin portal first."*

**Never improvise around a missing dependency.** Hand off to the
correct skill so its own dependency-chain and per-resource business
rules are enforced (e.g. `dynamic_discovery=False ⇒ server_ids
required`).

---

### Step 3: Build the conditions payload

Mirror the access rule's identity + app blocks. The typical shape is:

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
  }
]
```

Add `PLATFORM` and/or `POSTURE` blocks if the admin wants the tight
re-auth cadence to apply only to a subset.

---

### Step 4: Create and verify

Go straight to create. Do **not** pre-list existing timeout rules —
new ZPA timeout rules are appended at the end of the policy by default,
and listing every existing rule before every create adds round trips,
gives no useful information for the typical case, and invites fan-out
retries when the list comes back empty.

```text
zpa_create_timeout_policy_rule(
  name="<rule_name>",
  action_type="RE_AUTH",
  reauth_timeout="<session length, e.g. '4 Hours'>",
  reauth_idle_timeout="<idle timeout, e.g. '15 Minutes'>",
  description="<short description>",
  conditions=<conditions_payload from step 3>
)

zpa_get_timeout_policy_rule(rule_id="<returned_rule_id>")
```

**Naming convention.** Make it obvious which access rule this pairs
with. Suggested: `<access_rule_name> — Session Duration`.

In the response, state the `reauth_timeout` and `reauth_idle_timeout`
in plain words ("Session expires after 4 hours; idle sessions
disconnect after 15 minutes") and which scope the rule applies to.

**Optional ordering check (only if the admin explicitly asks).** If
the admin wants the rule placed somewhere other than the end of the
policy, *then* run `zpa_list_timeout_policy_rules()` once and reorder
afterward. Otherwise, accept the default append-at-end placement.

---

## Quick reference

### Tools used

- `get_zpa_scim_group(search)` — identity lookup
- `zpa_list_application_segments(search="<name>")` / `zpa_list_segment_groups(search="<name>")` — app scope
- `get_zpa_posture_profile(search)` — optional posture scope
- `zpa_create_timeout_policy_rule(name, action_type, reauth_timeout, reauth_idle_timeout, conditions, ...)` — write (no pre-flight needed)
- `zpa_get_timeout_policy_rule(rule_id)` — verify
- `zpa_list_timeout_policy_rules()` — **only** when the admin explicitly asks about rule ordering

### Related skills (chain these, don't reinvent them)

- `zpa-onboard-application` — **upstream dependency.** Owns the full
  chain: App Connector Group → Server Group → Segment Group → App
  Segment. Trigger this *first* if the named app segment does not yet
  exist; resume this skill afterward with the new segment ID.
- `zpa-create-timeout-policy-rule` — general-purpose timeout-rule
  skill; use that for arbitrary timeout rules outside the
  session-duration shape this skill specializes in.

**Different ZPA resource types — do not chain through this skill:**

- `zpa-create-conditional-access-rule` / `zpa-create-access-policy-rule`
  — ZPA **Access Policy** is a separate resource type from Timeout
  Policy. Identity, posture, platform, country, and risk gating live
  there, not here. If the admin asked for both a session timeout and
  an access-control rule, treat them as two independent requests and
  route the access half to the appropriate access-policy skill.

**Typical chain when the app segment doesn't exist yet:**

```text
zpa-onboard-application       (only if the app segment doesn't exist)
        ↓
zpa-create-session-duration-rule  (this skill — Timeout Policy rule)
```
