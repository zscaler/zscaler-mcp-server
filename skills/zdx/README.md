# ZDX Skills — Zscaler Digital Experience playbooks for skill-capable agents

Seven pre-packaged ZDX investigation and reporting playbooks, each shipped as a
single `.zip` you can upload directly into your skill-capable AI agent (Claude
Desktop / Claude.ai Projects, etc.). When the agent invokes a skill it runs the
matching Zscaler MCP tools, then renders the result as a Zscaler-branded,
single-file interactive HTML report with light/dark mode, multi-language UI
(EN / ES / PT / FR / JA), KPI cards, sortable color-coded tables, CSV export,
and a print/save-PDF action.

> **Prerequisite — Zscaler MCP server.** Every skill calls Zscaler ZDX tools
> (`zdx_list_alerts`, `zdx_get_deeptrace_*`, etc.). Your agent needs the
> [Zscaler MCP server](../../README.md) configured and connected first. The
> ZDX service is read-only except for `zdx_start_deeptrace`, which is a write
> tool — see the per-skill SKILL.md for which steps need write-tools enabled.

## The seven skills at a glance

| # | Skill | Use it when… | Invoke explicitly with |
|---|---|---|---|
| 1 | **analyze-application-health** | You want an org-wide app health snapshot. *"How healthy are my SaaS apps?"* | `/zdx-analyze-application-health` |
| 2 | **audit-software-inventory** | You need a software / compliance audit across the device fleet. | `/zdx-audit-software-inventory` |
| 3 | **compare-location-experience** | You want to rank offices / departments / geos. *"Which office is the worst?"* | `/zdx-compare-location-experience` |
| 4 | **diagnose-deeptrace** | You already have (or just started) a deep trace and need a full breakdown. | `/zdx-diagnose-deeptrace` |
| 5 | **investigate-alerts** | You're triaging one or more active ZDX alerts. *"Show me ongoing alerts."* | `/zdx-investigate-alerts` |
| 6 | **investigate-multi-app-outage** | Several apps are failing at the **same office**. *"Columbus users can't reach Salesforce and ServiceNow."* | `/zdx-investigate-multi-app-outage` |
| 7 | **troubleshoot-user-experience** | One specific user complains an app is slow. | `/zdx-troubleshoot-user-experience` |

The slash names match the frontmatter `name:` in each skill's `SKILL.md`
verbatim — this is what your agent's skill registry exposes.

## What's in each skill folder

```text
skills/zdx/
├── README.md                              ← this file
├── analyze-application-health/
│   ├── SKILL.md                           ← skill definition: trigger phrases + step-by-step workflow
│   ├── analyze-application-health.zip     ← upload THIS into your agent
│   ├── templates/
│   │   └── report.html.template           ← agent fills __ZDX_DATA__ with the run's JSON
│   └── example/
│       ├── report.example.html            ← preview populated with sample data
│       └── preview-dark.png               ← rendered screenshot (dark mode)
├── audit-software-inventory/              (same layout)
├── compare-location-experience/           (same layout)
├── diagnose-deeptrace/                    (same layout — 4 tables)
├── investigate-alerts/                    (same layout)
├── investigate-multi-app-outage/          (same layout — 2 tables, dynamic columns)
└── troubleshoot-user-experience/          (same layout)
```

Per-file purpose:

- **`<skill>.zip`** — the deployable artifact. Self-contained: includes the
  `SKILL.md` instructions and the `templates/` directory the agent reads at
  runtime. **This is what you upload.**
- **`SKILL.md`** — human-readable source for the skill. Read this if you want
  to understand or modify the playbook before re-zipping. Same content the
  agent sees inside the zip.
- **`templates/report.html.template`** — the HTML report shell with a
  `__ZDX_DATA__` placeholder the agent populates with the run's data.
- **`example/`** — a pre-rendered example so you can preview the look and
  feel before installing the skill. Open `report.example.html` in any
  browser; nothing else is required.

## Installing a skill into your agent

The exact steps differ slightly per host. The principle is the same: **upload
the `.zip`**.

### Claude.ai Projects (web)

1. Open the Project that already has the Zscaler MCP connector wired in.
2. **Settings → Skills → Add skill** (or *"+ Skill"* depending on plan tier).
3. Choose **Upload .zip** and select the skill's `.zip` from this directory.
4. Confirm. The skill name (e.g. `zdx-investigate-multi-app-outage`) appears
   in the project's skill list.

### Claude Desktop

1. **Settings → Skills → Manage skills**.
2. **Import → From .zip** and pick the file.
3. The skill becomes available to every chat in that profile.

### Other skill-capable agents

If your agent supports the `mcp-skills` / SEP-1865 packaging convention,
upload the `.zip` through whichever UI it exposes for skill management.
The contract is just: one `.zip` that contains a `SKILL.md` at its root
plus a `templates/` directory.

### Upload all seven at once

You can install just the skills you care about, or upload all seven for the
full ZDX toolkit. Each skill is independent — installing one does not
require installing the others.

## Invoking a skill

Once installed, there are two ways to trigger a skill.

### Option A — natural-language auto-activation (default)

Describe what you want to investigate in plain language. The agent matches
your request against every installed skill's `description` field and picks
the best fit. Examples that auto-activate the right skill:

| You say… | Agent picks |
|---|---|
| *"A ZDX alert shows users in Columbus can't reach Salesforce and ServiceNow."* | `zdx-investigate-multi-app-outage` |
| *"How healthy are our SaaS apps right now?"* | `zdx-analyze-application-health` |
| *"User jane.doe@acme.com says Salesforce is slow."* | `zdx-troubleshoot-user-experience` |
| *"Which office has the worst experience?"* | `zdx-compare-location-experience` |
| *"Show me the ongoing alerts from the last 24 hours."* | `zdx-investigate-alerts` |

Auto-activation is the path most admins use day to day. It only goes wrong
when two skills could plausibly handle the request — that's when you switch
to Option B.

### Option B — explicit by slash command (best practice when you know which playbook you want)

Prefix your message with `/` and the skill's exact `name`. Examples:

```text
/zdx-investigate-multi-app-outage Columbus office, Salesforce and ServiceNow, last 24h.
```

```text
/zdx-diagnose-deeptrace device_id=155462842 trace_id=7473160764821179371
```

When to prefer this over auto-activation:

- **Multiple skills could match** your request (e.g. "users are slow" could
  trigger user-experience or alerts or app-health). Slash removes ambiguity.
- You're **running the same playbook repeatedly** (incident response, weekly
  audits) and want to skip the matching step.
- You want a **reproducible** invocation in a runbook or ticket. The slash
  command makes the playbook explicit.
- You **already know the IDs / inputs** (device_id, location_id, app_id) and
  want the agent to skip clarifying questions and dive straight in.

> **Note on the slash prefix.** The skill's `name` already starts with the
> `zdx-` service prefix (`zdx-investigate-multi-app-outage`). Some agent UIs
> let you drop the prefix in the slash menu (showing just
> `/investigate-multi-app-outage`), but the registered name is always the
> full one. When in doubt, use the full slash name shown in the table at the
> top of this README — it always works.

## What happens after the skill is invoked

Every ZDX skill follows the same three-phase shape:

1. **Discover & query** — the skill runs the appropriate Zscaler MCP tools
   (`zdx_list_applications`, `zdx_list_alerts`, `zdx_get_deeptrace_*`, etc.)
   to gather the raw data described in the skill's workflow steps.
2. **Aggregate** — the data is shaped into a single JSON object matching the
   skill's data contract (see "Per-skill data contracts" below). Severity
   classifications are applied per row (critical / warning / good).
3. **Render** — the agent reads `templates/report.html.template` (bundled
   in the zip), substitutes the JSON into the `__ZDX_DATA__` placeholder,
   and writes the result to disk as `<skill>_report_<YYYYMMDD-HHMMSS>.html`.
   The HTML file opens directly in any browser — Tailwind / React / Babel
   are loaded from public CDNs, no build step.

Most skills also produce a Word doc (`.docx`) alongside the HTML for sharing
with stakeholders who prefer a static document.

## Trying a skill before you install it

Each `example/report.example.html` is a fully-rendered preview using sample
data. Open it directly in a browser and:

- click the moon/sun icon (top right) to toggle dark/light
- click the globe + language code to switch language
- type in the **Search** box or click filter chips
- click any column header to sort
- click **Export CSV** for the per-table dump
- click **Print / Save PDF** for the print-ready view

This is the same look and feel you'll get from a real run.

## Per-skill data contracts (for developers / debugging)

The JSON the agent injects into `__ZDX_DATA__` has the same outer shape for
every skill:

```json
{
  "generated_at": "2026-05-18T10:30:00Z",
  "scope_en": "Free-form description in English",
  "scope_es": "...in Spanish (optional, falls back to scope_en)",
  "scope_pt": "...in Portuguese (optional)",
  "scope_fr": "...in French (optional)",
  "scope_ja": "...in Japanese (optional)",
  "kpis": {
    "<kpi_key>": "<value>"        // keys match the skill's KPI list
  },
  "tables": {
    "<table_id>": [
      {
        "severity": "critical | warning | good | info | neutral",
        "<column_key>": "<cell_value>"
      }
    ]
  }
}
```

The `severity` field on each row drives the colored row background (red for
critical, yellow for warning, green for good).

### analyze-application-health

- `kpis`: `total`, `good`, `okay`, `poor`, `mostImpacted`
- `tables.apps`: `name`, `score`, `status`, `pft`, `dns`, `availability`, `impactedUsers`, `bottleneck`

### audit-software-inventory

- `kpis`: `totalSoftware`, `totalDevices`, `compliancePct`, `criticalCount`
- `tables.software`: `name`, `version`, `vendor`, `group`, `devices`, `users`, `status`, `risk`

### compare-location-experience

- `kpis`: `totalLocations`, `bestLocation`, `worstLocation`, `avgScore`, `alertCount`
- `tables.locations`: `rank`, `location`, `score`, `pft`, `dns`, `availability`, `poorUsers`, `activeAlerts`, plus a `tier` field (`Top | Borderline | Poor`) for filter matching

### diagnose-deeptrace

- `kpis`: `user`, `device`, `session`, `status`, `duration`, `rootCause`
- `tables.probe`: `metric`, `value`, `threshold`, `status`
- `tables.path`: `hop`, `node`, `latency`, `loss`, `jitter`, `status`
- `tables.health`: `metric`, `value`, `status`
- `tables.processes`: `process`, `cpu`, `memory`

### investigate-alerts

- `kpis`: `total`, `high`, `medium`, `low`, `mostAffected`, `impactedDevices`
- `tables.alerts`: `priority`, `alertName`, `application`, `duration`, `affectedDevices`, `locations`, `bottleneck`, `status`

### investigate-multi-app-outage

- `kpis`: `location`, `appsAffected`, `affectedDevices`, `sharedHop`, `duration`
- `tables.devices`: `device`, `user`, `os`, `zccVersion`, `lastSeen`, `appsFailing`, plus `scope` (`Critical | Degraded`) for filter matching
- `tables.hops`: `hop`, `address`, `app1Latency`, `app1Loss`, `app2Latency`, `app2Loss`, `verdict` (`SHARED | Degraded | OK`)
- **Required**: `columnOverrides.hops` — a map renaming the four `app1*` / `app2*` columns to the actual application names for the run (e.g. `{"app1Latency": "Salesforce Latency", "app1Loss": "Salesforce Loss", "app2Latency": "ServiceNow Latency", "app2Loss": "ServiceNow Loss"}`)

### troubleshoot-user-experience

- `kpis`: `user`, `device`, `score`, `bottleneck`, `alerts`
- `tables.metrics`: `metric`, `value`, `normal`, `category`, `status`, `impact`

## Updating / re-packaging a skill

If you edit a skill's `SKILL.md` or `templates/report.html.template`, repack
the zip before redistributing:

```bash
cd skills/zdx/<skill-name>
zip -r <skill-name>.zip SKILL.md templates/
```

Then upload the refreshed zip into your agent, replacing the previous
version. The agent re-reads the bundled `SKILL.md` on every invocation, so
edits take effect immediately after the upload.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Skill never auto-activates from natural language | The `description` in `SKILL.md` doesn't include phrasing close to what the admin types. Either re-prompt with one of the trigger phrases in the table at the top of this README, or invoke explicitly with the slash command. |
| Agent runs the skill but produces no HTML report | The agent couldn't read the bundled `templates/report.html.template` (zip was incomplete) or has no write access in the current working directory. Re-upload the zip; check the agent's working-directory permissions. |
| Tables are empty / KPIs are all "—" | The Zscaler MCP server isn't connected, or the OneAPI credentials aren't entitled to ZDX. Test with a simple `zdx_list_alerts()` call before re-running the skill. |
| `zdx_start_deeptrace` step fails with a permissions error | Write tools aren't enabled on the MCP server. Restart the server with `--write-tools "zdx_start_deeptrace"` (or a wider allowlist like `--write-tools "zdx_*"`). |
| Slash command not recognised | The skill isn't installed in this conversation's project / profile, or you typed the wrong name. Check the agent's skill list and use the exact `name` from the table above. |
