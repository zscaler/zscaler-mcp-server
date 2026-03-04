# Zscaler MCP Server

150+ tools for managing the Zscaler Zero Trust Exchange. Services: ZPA, ZIA, ZDX, ZCC, EASM, Z-Insights, ZIdentity, ZTW (Zscaler Terraform Workspaces).

## Tool Naming & Discovery

All tools follow `{service}_{verb}_{resource}` naming: `zia_list_locations`, `zpa_create_access_policy_rule`, `zdx_get_application`. Service prefixes: `zia_`, `zpa_`, `zdx_`, `zcc_`, `easm_`, `zinsights_`, `zidentity_`, `ztw_`. Use the prefix to discover tools for a given service.

## Critical Gotchas

- **ZIA requires activation.** After any ZIA create/update/delete, call `zia_activate_configuration()`. Changes are staged until activation. Forgetting this is the #1 source of "my change didn't work" issues.
- **`use_legacy` parameter.** Every tool has a `use_legacy` parameter that defaults to `False`. Do NOT change it unless the user explicitly asks for legacy API behavior.
- **ZDX is read-only.** ZDX tools only query data. There are no create/update/delete operations except for deep traces (`zdx_start_deep_trace`).
- **ZDX `since` parameter is in hours**, not timestamps. Default is 2 hours. Example: `since=24` means "last 24 hours."
- **IDs are strings**, even when they look numeric. Always pass IDs as strings.
- **ZPA dependency chain matters.** To onboard an application: create app connector group -> create server group (references connector group) -> create segment group -> create application segment (references server and segment groups) -> create access policy rule. Skipping dependencies causes cryptic 400 errors.
- **ZIA dependency chain for locations.** To onboard a location: create static IP -> create VPN credential (references static IP) -> create location (references VPN credential and static IP). The location won't work without the traffic forwarding prerequisites.

## Write Operations — Safety Rules

1. **Always confirm before mutating.** Read operations are safe. Create/update/delete operations modify the live Zscaler environment. Ask the user before executing write operations.
2. **Always list/get first** to understand current state before creating or modifying resources.
3. **Pagination:** List tools support `page` and `page_size` parameters. For large tenants, paginate rather than fetching everything.
4. **ZPA policy rule ordering:** New rules are appended at the end by default. Policy rules are evaluated top-to-bottom — order matters for access control.

## ZDX Filtering

ZDX query tools accept optional filters that significantly improve result quality:
- `location_id`: Filter by office/site location
- `department_id`: Filter by department
- `geo_id`: Filter by geolocation
- `since`: Hours to look back (default 2)

Always ask the user for scope before running broad ZDX queries on large tenants.

## Environment

Required env vars (set in `.env`):
- `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_VANITY_DOMAIN` — OneAPI credentials from ZIdentity console
- Optional legacy credentials: `ZIA_USERNAME`, `ZIA_PASSWORD`, `ZIA_API_KEY`, `ZIA_CLOUD`, `ZPA_CLIENT_ID`, `ZPA_CLIENT_SECRET`, `ZPA_CUSTOMER_ID`, `ZPA_CLOUD`

## Development

- Package manager: `uv` (not pip, not poetry)
- Install: `make install-dev` or `uv pip install -e .`
- Dependencies: `make sync-dev-deps`
- Run locally: `uvx zscaler-mcp` (requires `.env` in working directory)
- Docker: `make docker-build && make docker-run` (stdio) or `make docker-run-http` (HTTP + auth)
- Clean: `make clean`

## Skills

19 guided skills in `skills/` for multi-step workflows. Skills are auto-activated by description match. Organized by service: `skills/zpa/` (6), `skills/zia/` (5), `skills/zdx/` (5), `skills/easm/` (1), `skills/z-insights/` (1), `skills/cross-product/` (1). Each skill has a `SKILL.md` with frontmatter (`name`, `description`) and step-by-step instructions referencing specific tool names.
