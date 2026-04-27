---
name: zia-resolve-cloud-app-enum
description: "Resolve user-supplied cloud-application names (e.g. 'OneDrive', 'Google Drive', 'share point online', or numeric Shadow IT IDs) to the canonical ZIA enum tokens (ONEDRIVE, GOOGLE_DRIVE, SHAREPOINT_ONLINE, etc.) required by SSL Inspection, Web DLP, Cloud App Control, File Type Control, Bandwidth Classes, and Advanced Settings rules. Use whenever a user asks to add, remove, or filter on cloud applications in any of those policy resources, or asks 'what's the right enum for X?'."
---

# ZIA: Resolve Cloud Application Enum

## Keywords

cloud application enum, ssl inspection cloud_applications, sharepoint enum, onedrive enum, google drive enum, dropbox enum, web dlp cloud applications, cloud app control enum, application catalog, ZIA cloud app token, cloud_applications field, NONE response cloud applications

## Why this skill exists

ZIA exposes **two distinct cloud-application catalogs** that look the same but are not interchangeable:

| Catalog | Tool(s) | Identifier |
|---|---|---|
| Shadow IT analytics | `zia_list_shadow_it_apps`, `zia_list_shadow_it_custom_tags` | numeric `id` (e.g. `655377`), friendly `name` (e.g. `Sharepoint Online`) |
| Policy-engine catalog | `zia_list_cloud_app_policy`, `zia_list_cloud_app_ssl_policy` | canonical enum string `app` (e.g. `SHAREPOINT_ONLINE`), display `app_name` |

Policy rules — SSL Inspection, Web DLP, Cloud App Control, File Type Control, Bandwidth Classes, Advanced Settings — accept **only** the canonical `app` enum from the policy-engine catalog in their `cloud_applications` field. Passing a Shadow IT numeric ID, a friendly display name, or even a slightly mistyped enum causes ZIA to silently coerce the value to `NONE` instead of raising a validation error. That's the failure mode behind issue [#56](https://github.com/zscaler/zscaler-mcp-server/issues/56).

The SSL Inspection create/update tools (`zia_create_ssl_inspection_rule`, `zia_update_ssl_inspection_rule`) **already resolve friendly names automatically** via the in-process resolver. The agent's job in this skill is to:

1. Trust the auto-resolution when calling those two tools.
2. Manually call the policy-engine catalog tools when the user asks to *look up* enums (without modifying a rule), or when they're working with another resource (Web DLP, Cloud App Control) where auto-resolution is not yet wired.

## Scope Boundaries

**Use these tools in this skill:**

- `zia_list_cloud_app_ssl_policy(search="...")` — primary tool for SSL Inspection scope
- `zia_list_cloud_app_policy(search="...")` — primary tool for DLP / Cloud App Control / File Type Control scope
- `zia_list_shadow_it_apps(query="...")` — only when the user is asking about Shadow IT analytics (sanction state, usage), NOT when they need a policy enum
- `zia_create_ssl_inspection_rule` / `zia_update_ssl_inspection_rule` — auto-resolve `cloud_applications` inputs, no extra step needed

**Do NOT call:**

- `zia_list_shadow_it_apps` to resolve a policy enum — wrong catalog
- Any non-cloud-app ZIA tool unless the user explicitly asks to chain into another rule type

---

## Workflow

### Decision tree on user intent

1. **"Add Google Drive and OneDrive to SSL inspection rule X"** — call `zia_update_ssl_inspection_rule` directly with `cloud_applications=["Google Drive", "OneDrive"]`. The tool auto-resolves friendly names. If the response includes `_cloud_applications_resolution`, echo the mapping to the user (so they see what was actually stored).
2. **"What's the enum for SharePoint Online?"** — call `zia_list_cloud_app_ssl_policy(search="sharepoint")` and return the `app` field of the matching entries. Do not modify any rule.
3. **"Show me all collaboration apps available for SSL inspection"** — call `zia_list_cloud_app_ssl_policy(app_class="ENTERPRISE_COLLABORATION", page_size=1000)` and project with `query="[*].{enum: app, name: app_name}"`.
4. **"Add SharePoint to a Web DLP rule"** — Web DLP create/update does NOT yet auto-resolve. Call `zia_list_cloud_app_policy(search="sharepoint")` first, pick the canonical `app` value, then pass it explicitly into the DLP rule tool.
5. **User asks about Shadow IT (sanction state, custom tags, usage analytics)** — that's a different skill. Use `zia_list_shadow_it_apps`.

### Resolution pattern (fallback when auto-resolution is unavailable)

```python
# Step 1: search the policy-engine catalog server-side
candidates = zia_list_cloud_app_ssl_policy(search="onedrive")

# Step 2: project to {enum, name} pairs
# Same call with a JMESPath query:
candidates = zia_list_cloud_app_ssl_policy(
    search="onedrive",
    query="[*].{enum: app, name: app_name}",
)

# Step 3: confirm the exact enum the user wants if multiple matches
# (e.g. ONEDRIVE vs ONEDRIVE_PERSONAL)

# Step 4: pass the canonical enum into the policy rule tool
zia_update_ssl_inspection_rule(
    rule_id="...",
    cloud_applications=["ONEDRIVE", "ONEDRIVE_PERSONAL"],
)
```

### Ambiguity & confirmation

- If a user input substring matches **multiple** canonical enums (e.g. `"sharepoint"` → `SHAREPOINT_ONLINE`, `SHAREPOINT_FOR_BUSINESS`), ask the user which they intended **before** calling the rule tool. The auto-resolver will refuse ambiguous substrings with `strict=True`, so it's faster to disambiguate up front.
- If a user input cannot be resolved at all, the auto-resolver raises a `ValueError` containing the closest matches. Surface those suggestions to the user verbatim.

### Reporting back

Whenever auto-resolution transformed any input, the response from the SSL inspection tool includes a `_cloud_applications_resolution` field, e.g.:

```json
{
  "id": 1324023,
  "name": "SSL_1",
  "cloud_applications": ["ONEDRIVE", "GOOGLE_DRIVE"],
  "_cloud_applications_resolution": {
    "resolved": {
      "OneDrive":     {"enums": ["ONEDRIVE"],     "match": "display_name"},
      "Google Drive": {"enums": ["GOOGLE_DRIVE"], "match": "display_name"}
    },
    "unresolved": [],
    "ambiguous": {}
  }
}
```

Echo the `resolved` mapping back to the user so they always see which canonical enum each friendly name became — e.g. *"I added `ONEDRIVE` (resolved from 'OneDrive') and `GOOGLE_DRIVE` (resolved from 'Google Drive') to rule SSL_1."*

## Common gotchas

- **`NONE` in the rule after a successful update** = the input was not a recognised enum, the API silently coerced it. Always rely on auto-resolution (or explicit lookup) — never let a literal user string flow into `cloud_applications` unchanged.
- **Shadow IT IDs do not work** — `655377` is a Shadow IT analytics ID, not a policy enum. The resolver will reject it.
- **Case matters at the API**, but not for our resolver — it accepts `"onedrive"`, `"OneDrive"`, `"ONEDRIVE"`, all map to `ONEDRIVE`.
- **`zia_create_ssl_inspection_rule` / `zia_update_ssl_inspection_rule`** silently activate the resolver. Set `resolve_cloud_apps=False` only if you've already validated the canonical enum yourself.
- **Other rule types (Web DLP, Cloud App Control)** do not yet auto-resolve. Use `zia_list_cloud_app_policy` first to look up the enum, then pass it.
- **ZIA activation reminder** — after any SSL inspection / DLP / Cloud App Control rule change, call `zia_activate_configuration()`.
