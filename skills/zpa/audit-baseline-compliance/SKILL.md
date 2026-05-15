---
name: zpa-audit-baseline-compliance
description: "Read-only audit of a ZPA tenant against the Zscaler ZPA Baseline Recommendations v1.0 document. Inventories app connector groups, server groups, application segments, access policy rules, forwarding policy rules, timeout policy rules, and (when available) LSS configs, then scores ~26 configuration-only checks across 7 categories and renders an interactive Zscaler-styled web report (single-file HTML, plus an optional .jsx component) — searchable, filterable by category, severity, and security framework (NIST SP 800-53 Rev. 5 and CIS Critical Security Controls v8), with per-finding evidence, remediation, and framework citations suitable as supporting evidence for SOC 2, FedRAMP, ISO 27001, and NIST CSF assessments, and printable to PDF from the browser. Use when an administrator asks to audit ZPA against best practices, run a baseline-compliance review, get a ZPA health check, gather compliance evidence, or see how their tenant compares to the recommended baseline. NEVER mutates the tenant — read-only."
---

# ZPA: Audit Baseline Compliance

## Keywords

zpa audit, zpa best practices, zpa baseline, zpa health check, zpa compliance review, baseline recommendations, zpa configuration audit, zpa policy audit, connector group audit, zpa hardening, zpa review, security baseline check, ZPA Baseline Recommendations v1.0

## Overview

Audit a ZPA tenant's configuration against the **Zscaler ZPA Baseline Recommendations v1.0** document. This skill is **fully read-only** — it inventories the tenant via existing list/get MCP tools, scores each finding against the baseline doc, and renders the result as a **standalone Zscaler-styled web report** (a single self-contained HTML file). A matching React component (`ZpaAuditReport.jsx`) is also generated for teams that want to embed the same view in an existing portal.

**Use this skill when:** An administrator asks to audit their ZPA tenant against best practices, run a baseline-compliance review, get a "ZPA health check", or see how their configuration compares to the recommended baseline.

---

## Hard constraints — what this skill does not do

1. **No writes.** Only `zpa_list_*` and `zpa_get_*` tools. Never call `zpa_create_*`, `zpa_update_*`, or `zpa_delete_*`.
2. **No telemetry checks.** ZPA does not expose live connector CPU/memory/throughput, app probe results, session counts, or LSS log delivery health. Checks that require runtime data are **not silently skipped** — they are listed in the report's "Cannot Audit" section so the user knows what's missing and can request new APIs later.
3. **Configuration-only.** Every check evaluates a field on a resource the API returns. Heuristic checks (e.g. naming-pattern matches for "sensitive" / "lss" / "discovery") are clearly marked as heuristic in the report.
4. **No external network calls from the report at view time.** The HTML file embeds all findings inline; the only runtime external loads are the Tailwind/React/Babel CDN scripts needed to render it. (For air-gapped environments, see "Offline mode" in Step 4.)

---

## Workflow

### Step 1: Confirm scope

Before running anything, confirm with the administrator:

- **Scope:** full audit (all categories) or a single category (Connectors, Server Groups, Segments, Access Policy, Forwarding Policy, Timeout Policy, LSS).
- **Microtenant:** if the tenant uses microtenants, ask which one to inventory (default: the parent tenant). This is an inventory-scope decision only; it is not stored in the audit JSON or shown on the report.

If the user asked a generic "audit my ZPA tenant" question, default to **full audit, parent tenant** and proceed without further questions.

> **The skill does not record a tenant identifier in the report.** The vanity domain, customer ID, and cloud realm live in the Zscaler MCP server's authentication context (env vars / config at server startup) and are not returned by any `zpa_list_*` / `zpa_get_*` tool — and rather than inviting the agent to guess (or compose strings from email addresses, file names, or `zscaler_check_connectivity` output), the report header simply omits tenant identity. The audit timestamp and inventory line are enough to identify a given run.

---

### Step 2: Inventory the tenant (read-only)

**Claude Desktop pre-step (deferred tool loading).** Claude Desktop lazy-loads MCP tool schemas via `tool_search` and refuses to invoke a tool whose schema isn't cached yet (you'll see *"`<tool>` has not been loaded yet. Call tool_search first"*). Before the inventory, prime the cache with a single search so all the read tools below are loaded in one shot:

```text
tool_search(query="zpa list connectors server groups segments policy rules lss")
```

If you skip this and call `zpa_list_lss_configs` (or any other tool) directly, the first call will fail with the *"not loaded yet"* error, you'll have to retry, and one inventory tool may end up silently skipped. This pre-step is a no-op on Cursor and Gemini CLI but is required on Claude Desktop / Cowork.

Then call these tools in parallel where possible. Capture the full result of each:

```text
zpa_list_app_connector_groups()
zpa_list_app_connectors()
zpa_list_server_groups()
zpa_list_segment_groups()
zpa_list_application_segments()
zpa_list_access_policy_rules()
zpa_list_forwarding_policy_rules()
zpa_list_timeout_policy_rules()
zpa_list_lss_configs()
zpa_list_lss_log_types()      # used to verify baseline log-feed coverage
```

**Pagination:** if any list returns the maximum page size (typically 500), paginate with `page_size=500, page=N` until exhausted. The audit is incomplete on a partial inventory.

**Errors:** if a tool returns an error (e.g. service disabled, missing scope, or the *"not loaded yet"* deferred-loading error), record the category as "Cannot Audit — API error" with the error message and continue with the rest. **Do not abort the whole audit.** For *"not loaded yet"*, retry the same tool once after running the `tool_search` pre-step above; if it still fails, mark the category as "Cannot Audit" and move on.

**Inventory transparency:** the inventory string you build here gets embedded into the report as a one-line summary so the admin can see which categories were actually fetched. Build it like:

> *Inventoried: 4 connector groups, 12 server groups, 30 application segments, 1 access rule, 0 forwarding rules, 2 timeout rules, 0 LSS configs.*

**LSS specifics:** the LSS API is **configuration-only** (returns LSS config records and the metadata catalogs). It cannot tell you whether logs are actually flowing to the SIEM, dropping, or arriving late — that's an out-of-band, SIEM-side observation. The audit can only verify configuration shape; live delivery health is in the "Cannot Audit" section.

---

### Step 3: Score the findings

Apply each check below to the inventory. Each finding has:

- **`id`** — short stable identifier (e.g. `acg-n-plus-one`)
- **`category`** — one of: `Connectors`, `ServerGroups`, `Segments`, `AccessPolicy`, `ForwardingPolicy`, `TimeoutPolicy`, `LSS`, `CannotAudit`
- **`severity`** — `critical`, `warning`, `info`, or `cannotAudit`
- **`title`** — one-line human summary
- **`evidence`** — short list of resource names / IDs that triggered the finding (max 10; truncate longer lists with `…and N more`)
- **`docRef`** — page or section in the baseline doc (e.g. `§Health Reporting Recommendations, page 23`)
- **`remediation`** — one or two sentences pointing the user at the right fix (often: "use the `zpa/<other-skill>` skill")
- **`heuristic`** — `true` if the check relies on naming patterns rather than a definitive field
- **`frameworks`** — optional object with `nist80053r5` and `cisV8` arrays of control identifiers. **Use the lookup table in [Step 3a — Framework mapping](#step-3a--framework-mapping) verbatim**; do not invent or generalize citations. Omit the field entirely (or both arrays empty) if the check has no high-confidence mapping — `acg-geo-coords` is the only check intentionally left unmapped.

> **Important:** every finding the report emits must be one of the IDs below. Do not invent new IDs; if a check does not apply, omit the finding entirely (the report only shows triggered findings — no "passes" section).

#### App Connector Group checks

| ID | Severity | Check |
|---|---|---|
| `acg-n-plus-one` | warning | Each AC group has ≥ 2 connectors (N+1 minimum). Flag groups with 0 or 1. |
| `acg-geo-coords` | info | AC groups have non-empty `latitude` / `longitude` for geo-routing. |
| `acg-version-drift` | warning | Each connector's `current_version` matches `expected_version`. |
| `acg-cert-expiring` | warning | Connector enrollment certificates expiring in <30 days. Use `enrollment_cert.valid_to_in_epoch_sec` if exposed. |
| `acg-enclave-isolation` | warning (heuristic) | AC groups whose name matches `*sensitive*`, `*enclave*`, `*pci*`, `*hr*`, `*finance*` are referenced by **only** "enclave-style" server groups (no broad SGs). |
| `acg-lss-isolation` | warning (heuristic) | AC group whose name matches `*lss*` or `*log*` is **not** bound to any application segment via a server group. |

#### Server Group checks

| ID | Severity | Check |
|---|---|---|
| `sg-dynamic-discovery` | info | `dynamic_discovery == True`. Flag any SG with it disabled and recommend re-enabling unless strict per-server segmentation is documented. |
| `sg-no-ac-group` | critical | SG has at least one `app_connector_group` bound. Zero = broken SG. |
| `sg-overly-broad` | warning (heuristic) | Non-Discovery / non-Global SGs that bind **all** AC groups in the tenant. Identify Discovery / Global SGs by name match (`*discover*`, `*global*`). |

#### Application Segment checks

| ID | Severity | Check |
|---|---|---|
| `seg-health-discovery` | warning | Discovery wildcard segments (domain contains `*`) have `health_reporting != "NONE"`. Should be `NONE` per doc page 23. |
| `seg-health-default` | info | Standard segments (single FQDN, single SG) use `health_reporting == "ON_ACCESS"`. |
| `seg-double-wildcard` | critical | No segment uses `*.*` or any single `*` as a domain (overly broad). |
| `seg-ip-only` | info | Segments using only IPs / CIDRs (no FQDNs). Recommend FQDN migration. |
| `seg-no-server-group` | critical | Segment has at least one `server_group` bound. |

#### Access Policy checks

| ID | Severity | Check |
|---|---|---|
| `ap-block-all-bottom` | critical | The **last** access-policy rule is an explicit `DENY` matching all (no scoped conditions). Doc class H. |
| `ap-posture-per-os` | critical | If any rule includes `POSTURE` failed-with-`PLATFORM`, **all five OSes** (Windows, macOS, iOS, Android, Linux) are covered. Missing OSes = silent allow on those platforms. Doc page 30. |
| `ap-contractor-pair` | warning (heuristic) | If any rule scopes to a SCIM group whose name matches `*contractor*`, `*vendor*`, `*partner*`, there is a paired `DENY` rule for the same group (block-rest pattern). Doc class C/C'. |
| `ap-discovery-bottom` | warning (heuristic) | Rules referencing wildcard discovery segments (segment name matches `*discovery*` or domain contains `*`) are at the **bottom** of the policy (above only the Block-All rule). Doc class G. |
| `ap-crown-jewel-hardening` | warning (heuristic) | `ALLOW` rules referencing crown-jewel app segments (name matches `*finance*`, `*hr*`, `*admin*`, `*pci*`, `*sap*`, `*workday*`) include both `CLIENT_TYPE` and `POSTURE` conditions. Doc class E. |
| `ap-deception-present` | info | A deception-style rule exists (auto-provisioned when Deception is licensed — informational only, do not modify). Doc class A. |

#### Forwarding Policy checks

| ID | Severity | Check |
|---|---|---|
| `fp-no-double-wildcard` | critical | No `INTERCEPT` rule uses `*.*` or a CIDR ≥ /16 (e.g. `10.0.0.0/8`). Doc page 36. |
| `fp-bypass-coverage` | warning | Canonical bypass list covered: Microsoft (`*.microsoft.com`, `login.microsoftonline.com`, `*.windowsupdate.microsoft.com`), Apple (`*.apple.com`, `*.icloud.com`), CRL/OCSP (`crl.*`, `ocsp.*`). |
| `fp-scim-scoped` | warning (heuristic) | `INTERCEPT` rules include a `SCIM_GROUP` operand (avoids leaking the full app list to every ZCC). |

#### Timeout Policy checks

| ID | Severity | Check |
|---|---|---|
| `tp-auth-range` | warning | `reauth_timeout` between 24 hours and 7 days. Flag values outside that window. Doc page 38. |
| `tp-idle-floor` | warning | `reauth_idle_timeout` ≥ 10 minutes (or `Never` for service-account rules). Doc page 38. |
| `tp-sensitive-tight` | info (heuristic) | Rules scoped to sensitive segments (name match `*finance*`, `*hr*`, `*pci*`, `*sap*`) have `reauth_idle_timeout` ≤ 15 minutes. |

#### LSS checks

The ZPA LSS API is **configuration-only**: it exposes LSS config records and the metadata catalogs (log types, status codes, client types, log formats). It does **not** stream or query log content; that ships from the LSS Connector to the SIEM out-of-band. So everything below is a config check; live delivery health belongs in the "Cannot Audit" section.

The shape of an LSS config record (from `zpa_get_lss_config`): `config.name`, `config.source_log_type` (ZPA internal code like `zpn_trans_log`), `config.lss_host`, `config.lss_port`, `config.use_tls`, `config.filter` (status code allowlist), and `connector_groups[].id`. Source log type internal codes:

| Baseline feed | Internal code | Human name (from `zpa_list_lss_log_types`) |
|---|---|---|
| User Activity | `zpn_trans_log` | `user_activity` |
| User Status | `zpn_auth_log` | `user_status` |
| Audit Logs | `zpn_audit_log` | `audit_logs` |
| App Connector Status | `zpn_ast_auth_log` | `app_connector_status` |
| App Connector Metrics | `zpn_ast_comprehensive_stats` | `app_connector_metrics` |
| Browser Access | `zpn_http_trans_log` | `browser_access` |
| Web Inspection | `zpn_waf_http_exchanges_log` | `web_inspection` |
| Private Service Edge Status | `zpn_sys_auth_log` | `private_svc_edge_status` |

| ID | Severity | Check |
|---|---|---|
| `lss-any-config` | critical | At least one LSS config exists. Zero configs = the tenant is not exporting any logs to a SIEM — major audit/incident-response blind spot. |
| `lss-dedicated-ac-group` | warning (heuristic) | The AC groups referenced by LSS configs (in `connector_groups`) are **not** also referenced by any server group / application segment. Co-mingling LSS with data-plane traffic is the doc's #1 LSS placement anti-pattern (page 35). Confirm via `zpa_list_server_groups` — no SG should bind any AC group that an LSS config also binds. |
| `lss-baseline-feeds` | warning | LSS configs exist covering each baseline feed: `zpn_trans_log` (User Activity), `zpn_auth_log` (User Status), `zpn_audit_log` (Audit), `zpn_ast_auth_log` (AC Status), `zpn_ast_comprehensive_stats` (AC Metrics). Flag each missing feed by name. Doc page 39. |
| `lss-tls-enabled` | warning | Each LSS config has `config.use_tls == true`. Plain TCP log streams over the LSS Connector hop are not recommended outside of fully isolated networks. |
| `lss-filter-applied` | info | Each LSS config has a non-empty `config.filter` (status-code allowlist). Catch-all streaming inflates SIEM ingest costs without improving signal. |
| `lss-disabled-config` | info | LSS configs with `config.enabled == false` — surface as a heads-up so the user can re-enable or delete stale records. |

#### Cannot Audit (always rendered, always the same)

These are baseline recommendations that depend on data ZPA does not expose. **Always include these five findings in the output**, with `category: "CannotAudit"` and `severity: "cannotAudit"`, so the user knows what's missing.

| ID | Title | Doc reference | Why we cannot check it via API |
|---|---|---|---|
| `ca-connector-cpu` | Per-connector CPU / memory / throughput | §App Connectors Redundancy and Scaling, page 11 | No telemetry API. Use hypervisor / cloud-provider metrics out-of-band. |
| `ca-app-probes` | App probe results / per-target reachability | §Health Reporting Recommendations, page 19 | No health API. The audit can only verify the configured `health_reporting` mode. |
| `ca-lss-delivery` | LSS log delivery / drops / SIEM ingestion health | §Log Streaming Service Recommendations, page 39 | LSS API is configuration-only. Monitor delivery from the SIEM side. |
| `ca-bandwidth` | AC group bandwidth utilization (live N+1 sizing) | §App Connectors Redundancy and Scaling, page 11 | No traffic-stats API. The N+1 check above counts connectors only, not load. |
| `ca-sessions` | Active session counts per app segment (idle-timeout sizing) | §Timeout Policies Recommendations, page 38 | No session-stats API. Idle-timeout sizing is informed by app class only. |

---

### Step 3a — Framework mapping

Each finding may carry an optional `frameworks` object that cites the **NIST SP 800-53 Rev. 5** controls and **CIS Critical Security Controls v8** safeguards the check evidences. The mapping was reviewed against:

- NIST SP 800-53 Rev. 5 (final, September 2020, with the 2023 patch release). Families AC, AU, CA, CM, CP, IA, SC, SI.
- CIS Critical Security Controls v8 (released May 2021, current revision v8.1, May 2024). Controls 1, 2, 3, 4, 6, 7, 8, 11, 12, 13.

**Disclaimer (also rendered in the report header):** *Framework mappings are guidance, not certified compliance attestations. Confirm with your auditor before citing in a SOC 2, FedRAMP, ISO 27001, or NIST CSF assessment.*

**Quality bar — when in doubt, omit.** A weak citation (mapping `acg-geo-coords` to "AC-something" because it touches access) is worse than no citation. The tables below cover 36 of the 37 check IDs; `acg-geo-coords` is intentionally unmapped (geo-routing is performance, not a security control).

**Frameworks intentionally NOT mapped:**

- **CIS Foundations Benchmarks** — these are platform-specific hardening guides (AWS / Azure / GCP / Kubernetes / Windows / RHEL etc.). No CIS Foundations Benchmark exists for ZPA, Zscaler, or any ZTNA product, so any citation would be incorrect and would be caught by an assessor familiar with the catalog.
- **NIST SP 800-207 Zero Trust Architecture** — architectural document, not a control catalog. Mapping is qualitative and applies at the product level, not per-finding. The disclaimer line above is enough.
- **NIST CSF 2.0** — outcomes-based abstraction layer that points back at 800-53. Adding it as a third column duplicates information that's already in the 800-53 column.

#### Lookup table

When a check fires, attach the row's `frameworks` object verbatim. Use the column heading order — `nist80053r5` first, `cisV8` second.

##### App Connector Group checks

| Check ID | `nist80053r5` | `cisV8` |
|---|---|---|
| `acg-n-plus-one` | `["CP-2", "CP-7", "SC-5"]` | `["11.1", "11.2"]` |
| `acg-geo-coords` | *(unmapped — performance, not security)* | *(unmapped)* |
| `acg-version-drift` | `["SI-2", "CM-8"]` | `["7.3", "2.1"]` |
| `acg-cert-expiring` | `["SC-12", "SC-17"]` | `["3.11", "12.6"]` |
| `acg-enclave-isolation` | `["SC-7", "SC-32", "AC-4"]` | `["12.1", "12.2"]` |
| `acg-lss-isolation` | `["SC-7", "AU-9"]` | `["8.5", "12.1"]` |

##### Server Group checks

| Check ID | `nist80053r5` | `cisV8` |
|---|---|---|
| `sg-dynamic-discovery` | `["CM-7"]` | `["4.1"]` |
| `sg-no-ac-group` | `["CM-6", "CM-2"]` | `["4.1"]` |
| `sg-overly-broad` | `["AC-4", "SC-7"]` | `["4.1", "12.2"]` |

##### Application Segment checks

| Check ID | `nist80053r5` | `cisV8` |
|---|---|---|
| `seg-health-discovery` | `["CM-7", "AU-12"]` | `["8.2"]` |
| `seg-health-default` | `["AU-12", "SI-4"]` | `["8.2", "8.5"]` |
| `seg-double-wildcard` | `["AC-4", "AC-6", "SC-7"]` | `["4.1", "12.2"]` |
| `seg-ip-only` | `["CM-8"]` | `["2.1"]` |
| `seg-no-server-group` | `["CM-6", "AC-3"]` | `["4.1"]` |

##### Access Policy checks

| Check ID | `nist80053r5` | `cisV8` |
|---|---|---|
| `ap-block-all-bottom` | `["AC-3", "AC-6", "AC-4"]` | `["6.7", "4.1"]` |
| `ap-posture-per-os` | `["IA-3", "CM-6", "AC-3"]` | `["4.7", "13.1"]` |
| `ap-contractor-pair` | `["AC-2", "AC-3", "AC-6"]` | `["6.1", "6.2"]` |
| `ap-discovery-bottom` | `["AC-4", "CM-7"]` | `["4.1"]` |
| `ap-crown-jewel-hardening` | `["AC-6", "AC-3", "IA-3", "IA-5"]` | `["6.4", "6.7"]` |
| `ap-deception-present` | `["SC-26", "SI-4"]` | `["13.6"]` |

##### Forwarding Policy checks

| Check ID | `nist80053r5` | `cisV8` |
|---|---|---|
| `fp-no-double-wildcard` | `["AC-4", "CA-3", "SC-7"]` | `["12.2"]` |
| `fp-bypass-coverage` | `["SC-7", "CA-3"]` | `["12.2"]` |
| `fp-scim-scoped` | `["AC-3", "AC-6", "AC-4"]` | `["6.1", "6.2", "6.7"]` |

##### Timeout Policy checks

| Check ID | `nist80053r5` | `cisV8` |
|---|---|---|
| `tp-auth-range` | `["AC-12", "IA-11"]` | `["6.4"]` |
| `tp-idle-floor` | `["AC-11", "AC-12"]` | `["6.4"]` |
| `tp-sensitive-tight` | `["AC-11", "AC-12", "AC-6"]` | `["6.4", "6.7"]` |

##### Log Streaming Service checks

| Check ID | `nist80053r5` | `cisV8` |
|---|---|---|
| `lss-any-config` | `["AU-2", "AU-6", "AU-12"]` | `["8.2", "8.5", "8.9"]` |
| `lss-dedicated-ac-group` | `["SC-7", "AU-9"]` | `["8.5", "12.1"]` |
| `lss-baseline-feeds` | `["AU-2", "AU-3", "AU-12"]` | `["8.2", "8.5"]` |
| `lss-tls-enabled` | `["SC-8", "SC-13"]` | `["3.10"]` |
| `lss-filter-applied` | `["AU-4"]` | `["8.3"]` |
| `lss-disabled-config` | `["AU-12", "CM-6"]` | `["4.1"]` |

##### Cannot Audit findings (gap-area mapping)

The `ca-*` findings are observability gaps — the check can't be measured today, but the *control area* it would have evidenced is still real. The mapping below tells the auditor *which control coverage is currently uncertain*.

| Check ID | `nist80053r5` (gap area) | `cisV8` (gap area) |
|---|---|---|
| `ca-connector-cpu` | `["SI-4", "AU-12"]` | `["8.11"]` |
| `ca-app-probes` | `["SI-4", "CP-2"]` | `["11.1"]` |
| `ca-lss-delivery` | `["AU-5", "AU-9"]` | `["8.2", "8.5"]` |
| `ca-bandwidth` | `["SC-5", "CP-2"]` | `["11.1"]` |
| `ca-sessions` | `["AC-12", "SI-4"]` | `["6.4"]` |

#### Maintenance

This table should be reviewed when either (a) the check list in Step 3 changes, or (b) a major framework revision drops (NIST 800-53 Rev. 6, CIS Controls v9). Keep mappings conservative: omitting weak citations is always preferable to inflating the column.

---

### Step 4: Build the audit JSON

Once scoring is complete, assemble the audit data object that the report consumes:

```json
{
  "audited_at": "<ISO 8601 timestamp, e.g. 2026-05-07T14:32:00Z>",
  "inventory": "4 connector groups, 12 server groups, 30 application segments, 1 access rule, 0 forwarding rules, 2 timeout rules, 0 LSS configs.",
  "findings": [
    {
      "id": "sg-no-ac-group",
      "category": "ServerGroups",
      "severity": "critical",
      "title": "Server group has no app connector group bound",
      "evidence": ["sg-finance-prod (id 12345)"],
      "docRef": "§Server Groups, page 14",
      "remediation": "Bind at least one app connector group to this server group. Use the `zpa/update-server-group` skill.",
      "heuristic": false,
      "frameworks": {
        "nist80053r5": ["CM-6", "CM-2"],
        "cisV8": ["4.1"]
      }
    }
  ]
}
```

**Validation rules for the JSON:**

- Every `id` must come from the tables in Step 3. Do not invent new IDs.
- `severity` must be one of `critical | warning | info | cannotAudit`.
- `category` must be one of `Connectors | ServerGroups | Segments | AccessPolicy | ForwardingPolicy | TimeoutPolicy | LSS | CannotAudit`.
- The five `ca-*` findings are mandatory and always present.
- Truncate `evidence` lists to 10 entries (final entry: `"…and N more"`).
- Heuristic checks must set `heuristic: true`.
- `frameworks` must come from the lookup table in [Step 3a](#step-3a--framework-mapping) verbatim. Use the same casing (e.g. `AC-3`, not `ac-3`; `6.7`, not `6.07`). Omit the field entirely for `acg-geo-coords`. Do not add framework families beyond `nist80053r5` and `cisV8`.

---

### Step 5: Confirm delivery preference

**Ask the admin once, before writing any files**, how they want the report delivered. Phrase it as a single short question:

> Where should I save the report? You can either (a) **download** — I'll generate the file and present it for you to save anywhere, or (b) **specify a path** — give me an absolute or workspace-relative directory and I'll write it there.

Pick the right tool for asking on the active surface:

| Surface | How to ask |
|---|---|
| Cowork mode | `AskUserQuestion` with two options: *Download the report* / *Save to a specific path* (and "Other" lets them paste a path). |
| Claude Desktop / Claude Code | Plain question; wait for the user's reply. |
| Cursor / CLI | Plain question; wait for the user's reply. |

If the user picks **download** (or doesn't specify a path), default to the agent's standard outputs/working directory:

- **Cowork:** save under the session's outputs folder, then present with `present_files` (or the equivalent download surface) so the user gets a clickable file.
- **Claude Code / Desktop:** save to the current working directory under `./reports/`.
- **Cursor:** save to the workspace root under `./reports/`.

If the user specifies a path, validate it (must be a writable directory) and use it verbatim.

**File naming:** `zpa-baseline-audit-<YYYYMMDD-HHMMSS>.html` (and the matching `.jsx` next to it). Timestamp only — no tenant slug, since the report no longer carries tenant identity.

---

### Step 6: Render the report

Two artifacts are written every run, side by side:

1. **`zpa-baseline-audit-<slug>-<ts>.html`** — the standalone Zscaler-styled web report. Open in any browser. No build step.
2. **`ZpaAuditReport-<slug>-<ts>.jsx`** — the same view as a React component for embedding in an existing app. Optional — write only if the user asked for the JSX too, or by default if the surface supports both (Cowork: write both).

#### 6a. Build the HTML

Read the template at `templates/report.html.template` (sibling of this SKILL.md). It contains a placeholder string `__FINDINGS_DATA__`. Replace that placeholder **once** with the JSON-stringified audit object from Step 4 (use stable `JSON.stringify(data)` — no pretty printing inside the script tag). Save the result to the chosen path.

Critical replacement rules:

- The replacement is a literal string substitution into a `<script type="application/json">` block — escape any `</script>` substring inside evidence/remediation strings (replace with `<\/script>`).
- Do not re-encode HTML entities. The data is read via `JSON.parse(textContent)`, not as HTML.
- Do not modify any other part of the template. The CSS, React component, and Tailwind/CDN imports are calibrated together.

#### 6b. Build the JSX (when requested)

Read `templates/ZpaAuditReport.jsx.template` and write it to the chosen directory unchanged. The component takes `{ data }` as a prop, so the consumer also needs the audit JSON — write it next to the JSX as `audit-<slug>-<ts>.json`:

```jsx
import ZpaAuditReport from './ZpaAuditReport-<slug>-<ts>.jsx';
import auditData from './audit-<slug>-<ts>.json';
export default function Page() { return <ZpaAuditReport data={auditData} />; }
```

#### 6c. What the report contains (visual contract)

The HTML/JSX template enforces the following layout — do not try to override it from the audit data:

- **Sticky header** — `zscaler` wordmark in cyan→blue→purple gradient, followed by "ZPA Baseline Compliance Audit". Right side: Expand all / Collapse all / Print-or-save-PDF buttons (the print button calls `window.print()` and the print stylesheet swaps to a clean white-paper look).
- **Title block** — `<h1>` "ZPA Baseline Compliance Audit" with the same gradient. Below: audit timestamp, doc reference, and the read-only disclaimer. (No tenant identifier — see Step 1.)
- **Framework disclaimer banner** — a single italicized line directly under the title block: *"Framework mappings are guidance, not certified compliance attestations. Confirm with your auditor before citing in a SOC 2, FedRAMP, ISO 27001, or NIST CSF assessment."*
- **Stat strip** — four cards: Critical, Warning, Info, Cannot Audit. Numbers colored by severity.
- **Inventory line** — the one-line summary string from Step 2.
- **Filter bar** — search input (matches title, ID, evidence, doc ref, remediation, *and framework citations*), category chip row (with counts), severity chip row (with counts), framework chip row (All / NIST 800-53r5 / CIS v8 — with counts of how many findings carry that family).
- **Findings list** — one card per finding, sorted Critical → Warning → Info → Cannot Audit then alphabetical by title. Each card shows severity pill, category pill, heuristic pill (if applicable), the finding ID, and the title in the collapsed state. When expanded, the body shows: doc reference, evidence, remediation, and (if `frameworks` is present) a "Frameworks" row of small pills — NIST controls in a neutral pill, CIS safeguards in a blue pill. Critical cards default to expanded; everything else defaults to collapsed. Click anywhere on a card to toggle.
- **Empty state** — when filters yield zero findings, a centered "No findings match the current filters." card.
- **Footer** — "Generated by the `zpa-audit-baseline-compliance` skill via the Zscaler MCP server." plus the doc reference.

#### 6d. Print / Save PDF

The print button just calls `window.print()`. The template ships a `@media print` block that:

- Switches background to white, text to dark navy, removes the gradient on the wordmark/title.
- Hides the filter bar, expand/collapse buttons, and the print button itself (`.no-print`).
- Forces every finding card to render expanded (`[data-content] { display: block !important }`).
- Disables `page-break-inside` on cards so each finding stays whole on one page.
- Recolors the severity pills with a light, print-friendly palette (red-50/amber-50/cyan-50 backgrounds with darker text).

The user prints to PDF via the browser (Cmd/Ctrl-P → "Save as PDF"). No html2pdf or external library — keeps the file truly standalone.

#### 6e. Offline mode (optional)

For air-gapped deployments, the user can convert the report to fully offline by:

1. Downloading the three CDN scripts (Tailwind, React UMD, ReactDOM UMD, Babel standalone) and the Inter font into a sibling `vendor/` directory.
2. Replacing the `<script src="https://…">` and `<link href="https://fonts…">` lines with relative paths.

Mention this only if the user asks about offline / air-gapped use.

---

### Step 7: Tell the user

State the totals, name any inventory failures, and point at the deliverable. Keep it short — the report is the deliverable, not the chat message.

> "I audited your ZPA tenant against the Baseline Recommendations v1.0. Found **X critical**, **Y warning**, **Z info** items across N categories, plus 5 observability gaps the API can't check. Saved to **`<path>`** — open it in your browser to filter, search, and print to PDF."

Never restate the full findings list in chat. The HTML report is the deliverable.

---

## Common Pitfalls

- **Do not write findings to a markdown table in chat.** The HTML report is the deliverable. A markdown table for 25+ findings is unreadable.
- **Do not invent evidence.** If a check requires a field the API didn't return (older SDK, missing scope), score it as `cannotAudit` with a note rather than guessing.
- **Do not call write tools.** This skill is read-only by design.
- **Do not run telemetry checks.** Anything the doc says about CPU / memory / throughput / probe results / log delivery is `cannotAudit`. Period.
- **Heuristic checks must be flagged.** Naming-pattern matches (`*sensitive*`, `*lss*`, `*contractor*`) are heuristic — set `heuristic: true` so the report shows the "Heuristic" pill and the user knows to verify.
- **Pagination matters.** A partial inventory produces wrong findings. If a list returned the max page size, keep paging.
- **Do not modify the templates inline.** If the template needs to change, edit `templates/report.html.template` or `templates/ZpaAuditReport.jsx.template` and commit; do not patch the rendered HTML on the fly.
- **Escape `</script>` in evidence text.** Rare but possible — if any finding's evidence/remediation contains the literal sequence `</script>`, replace it with `<\/script>` before substituting into the HTML template, otherwise the data block closes prematurely.
- **Do not invent framework citations.** Use the lookup table in [Step 3a](#step-3a--framework-mapping) verbatim. If a finding has no row in the table (only `acg-geo-coords`), omit the `frameworks` field entirely. Do not extrapolate from a similar check, do not generalize a sub-control to its parent (e.g. `AC-3` vs. `AC`), and do not add CIS Foundations Benchmarks (no ZPA benchmark exists). A weak citation is worse than no citation.

---

## When NOT to Use This Skill

- Single-rule creation (use `zpa/create-access-policy-rule`, etc.).
- Application onboarding (use `zpa/application_segment-onboard`).
- Reactive connector troubleshooting (use `zpa/troubleshoot-app-connector`).
- Writing changes — this skill never mutates the tenant.

---

## Quick Reference

**Inventory tools (read-only):**

- `zpa_list_app_connector_groups`, `zpa_list_app_connectors`
- `zpa_list_server_groups`, `zpa_list_segment_groups`, `zpa_list_application_segments`
- `zpa_list_access_policy_rules`, `zpa_list_forwarding_policy_rules`, `zpa_list_timeout_policy_rules`
- `zpa_list_lss_configs`, `zpa_get_lss_config`, `zpa_list_lss_log_types`, `zpa_list_lss_status_codes`, `zpa_list_lss_client_types`, `zpa_get_lss_log_format`

**Templates (in this skill's `templates/` directory):**

- `report.html.template` — single-file HTML report. Replace `__FINDINGS_DATA__` with the audit JSON; save as `.html`.
- `ZpaAuditReport.jsx.template` — React component that consumes the same audit JSON via a `data` prop. Save as `.jsx`.

**Doc reference:** Zscaler ZPA Baseline Recommendations v1.0 (April 2026), 41 pages. Cite the relevant page or section in each finding's `docRef`.

**Visual style (don't override):** Dark navy background (`#050912`), Zscaler cyan→blue→purple gradient on the wordmark and h1, severity colors red/amber/cyan/gray, Inter font, rounded 12px cards, sticky header, print stylesheet for clean PDF export.
