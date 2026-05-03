---
name: zia-look-up-cloud-app-name
description: "Look up the canonical ZIA cloud-application name (e.g. ONEDRIVE, GOOGLE_DRIVE, SHAREPOINT_ONLINE, DROPBOX) given whatever the admin typed — friendly names like 'OneDrive', 'Google Drive', 'share point online', loose phrasings like 'sharepoint', or even numeric Shadow IT IDs. Cloud App Control, SSL Inspection, Web DLP, File Type Control, Bandwidth Classes, and Advanced Settings rules all require the canonical ZIA name in their `cloud_applications` field; passing the friendly name or a Shadow IT ID silently coerces to `NONE` and the rule does nothing. Use whenever an admin asks to add, remove, or filter on cloud applications in any policy rule, or asks 'what's the right name for X?'."
---

# ZIA: Look Up Cloud Application Name

## Keywords

canonical cloud application name, ssl inspection cloud_applications, sharepoint name, onedrive name, google drive name, dropbox name, web dlp cloud applications, cloud app control application name, application catalog, ZIA cloud app token, cloud_applications field, NONE response cloud applications

## Why this skill exists

ZIA exposes **two distinct cloud-application catalogs** that look the same but are not interchangeable:

| Catalog | Tool(s) | Identifier |
|---|---|---|
| Shadow IT analytics | `zia_list_shadow_it_apps`, `zia_list_shadow_it_custom_tags` | numeric `id` (e.g. `655377`), friendly `name` (e.g. `Sharepoint Online`) |
| Policy-engine catalog | `zia_list_cloud_app_policy`, `zia_list_cloud_app_ssl_policy` | canonical app name `app` (e.g. `SHAREPOINT_ONLINE`), display `app_name` |

Policy rules — SSL Inspection, Web DLP, Cloud App Control, File Type Control, Bandwidth Classes, Advanced Settings — accept **only** the canonical `app` value from the policy-engine catalog in their `cloud_applications` field. Passing a Shadow IT numeric ID, a friendly display name, or even a slightly mistyped value causes ZIA to silently coerce it to `NONE` instead of raising a validation error. That's the failure mode behind issue [#56](https://github.com/zscaler/zscaler-mcp-server/issues/56).

The SSL Inspection create/update tools (`zia_create_ssl_inspection_rule`, `zia_update_ssl_inspection_rule`) **already resolve friendly names automatically** via the in-process resolver. The agent's job in this skill is to:

1. Trust the auto-resolution when calling those two tools.
2. Manually call the policy-engine catalog tools when the admin asks to *look up* the canonical name (without modifying a rule), or when they're working with another rule type (Web DLP, Cloud App Control) where auto-resolution is not yet wired.

## Scope Boundaries

**Which rule types use the cloud-app catalog** (and therefore need this skill):

- ✅ **SSL Inspection** (`zia_create/update_ssl_inspection_rule`) — field is `cloud_applications`. Auto-resolves friendly names.
- ✅ **Web DLP** (`zia_create/update_web_dlp_rule`) — field is `cloud_applications`. Does **not** auto-resolve; look up the canonical name with this skill first, then pass it in.
- ✅ **File Type Control** (`zia_create/update_file_type_control_rule`) — field is `cloud_applications`. Auto-resolves friendly names.
- ✅ **Cloud App Control** (`zia_create/update_cloud_app_control_rule`) — field is `cloud_applications`. Auto-resolves friendly names.
- ✅ **Cloud Firewall DNS** (`zia_create/update_cloud_firewall_dns_rule`) — **field is named `applications`, not `cloud_applications`** (an inconsistency in the underlying ZIA API). Same catalog, same vocabulary, same auto-resolution. The DNS-related sub-categories (DNS tunnels, network apps, DoH providers like `CLOUDFLARE_DOH`) live inside this same catalog.

**Which rule types do NOT use the cloud-app catalog** (do not chain to this skill for them):

- ❌ Cloud Firewall Filtering — uses network services / IP groups, not cloud apps
- ❌ Cloud Firewall IPS — no cloud-app scoping
- ❌ Sandbox — file-hash and behaviour-class scoping, not cloud-app
- ❌ URL Filtering — matches on `url_categories`, not the cloud-app catalog

**Use these tools in this skill:**

- `zia_list_cloud_app_ssl_policy(search="...")` — primary tool for SSL Inspection scope
- `zia_list_cloud_app_policy(search="...")` — primary tool for DLP / Cloud App Control / File Type Control / DNS scope (single canonical catalog)
- `zia_list_shadow_it_apps(query="...")` — only when the admin is asking about Shadow IT analytics (sanction state, usage), NOT when they need a policy-engine app name
- The five rule create/update tools above — auto-resolve `cloud_applications` (or `applications`, on DNS) inputs, no extra step needed

**Do NOT call:**

- `zia_list_shadow_it_apps` to look up a policy-engine app name — wrong catalog
- Any non-cloud-app ZIA tool unless the admin explicitly asks to chain into another rule type

---

## Workflow

### Decision tree on admin intent

1. **"Add Google Drive and OneDrive to SSL inspection rule X"** — call `zia_update_ssl_inspection_rule` directly with `cloud_applications=["Google Drive", "OneDrive"]`. The tool auto-resolves friendly names. If the response includes `_cloud_applications_resolution`, echo the mapping back to the admin (so they see what was actually stored).
2. **"What's the canonical name for SharePoint Online?"** — call `zia_list_cloud_app_ssl_policy(search="sharepoint")` and return the `app` field of the matching entries. Do not modify any rule.
3. **"Show me all collaboration apps available for SSL inspection"** — call `zia_list_cloud_app_ssl_policy(app_class="ENTERPRISE_COLLABORATION", page_size=1000)` and project with `query="[*].{canonical: app, name: app_name}"`.
4. **"Add SharePoint to a Web DLP rule"** — Web DLP create/update does NOT yet auto-resolve. Call `zia_list_cloud_app_policy(search="sharepoint")` first, pick the canonical `app` value, then pass it explicitly into the DLP rule tool.
5. **Admin asks about Shadow IT (sanction state, custom tags, usage analytics)** — that's a different skill. Use `zia_list_shadow_it_apps`.

### Resolution pattern (fallback when auto-resolution is unavailable)

```python
# Step 1: search the policy-engine catalog server-side
candidates = zia_list_cloud_app_ssl_policy(search="onedrive")

# Step 2: project to {canonical, name} pairs
# Same call with a JMESPath query:
candidates = zia_list_cloud_app_ssl_policy(
    search="onedrive",
    query="[*].{canonical: app, name: app_name}",
)

# Step 3: confirm the exact canonical name the admin wants if multiple matches
# (e.g. ONEDRIVE vs ONEDRIVE_PERSONAL)

# Step 4: pass the canonical name(s) into the policy rule tool
zia_update_ssl_inspection_rule(
    rule_id="...",
    cloud_applications=["ONEDRIVE", "ONEDRIVE_PERSONAL"],
)
```

### Ambiguity & confirmation

- If an admin input substring matches **multiple** canonical names (e.g. `"sharepoint"` → `SHAREPOINT_ONLINE`, `SHAREPOINT_FOR_BUSINESS`), ask the admin which they intended **before** calling the rule tool. The auto-resolver will refuse ambiguous substrings with `strict=True`, so it's faster to disambiguate up front.
- If an admin input cannot be resolved at all, the auto-resolver raises a `ValueError` containing the closest matches. Surface those suggestions to the admin verbatim.

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

Echo the `resolved` mapping back to the admin so they always see which canonical name each friendly name became — e.g. *"I added `ONEDRIVE` (resolved from 'OneDrive') and `GOOGLE_DRIVE` (resolved from 'Google Drive') to rule SSL_1."*

## Common gotchas

- **`NONE` in the rule after a successful update** = the input was not a recognised canonical name, the API silently coerced it. Always rely on auto-resolution (or explicit lookup) — never let a literal admin string flow into `cloud_applications` unchanged.
- **Shadow IT IDs do not work** — `655377` is a Shadow IT analytics ID, not a policy-engine app name. The resolver will reject it.
- **Case matters at the API**, but not for our resolver — it accepts `"onedrive"`, `"OneDrive"`, `"ONEDRIVE"`, all map to `ONEDRIVE`.
- **`zia_create_ssl_inspection_rule` / `zia_update_ssl_inspection_rule`** silently activate the resolver. Set `resolve_cloud_apps=False` only if you've already validated the canonical name yourself.
- **Other rule types (Web DLP, Cloud App Control)** do not yet auto-resolve. Use `zia_list_cloud_app_policy` first to look up the canonical name, then pass it.
- **ZIA activation reminder** — after any SSL inspection / DLP / Cloud App Control rule change, call `zia_activate_configuration()`.
