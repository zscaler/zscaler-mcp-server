---
name: "zscaler"
displayName: "Zscaler Zero Trust"
description: "Manage your Zscaler Zero Trust Exchange platform — ZPA private access, ZIA internet security, ZDX digital experience, ZMS microsegmentation, and more. 360+ tools across 9 services, plus 41 guided skills."
keywords: ["zscaler", "zero-trust", "ztna", "zpa", "zia", "zdx", "zcc", "easm", "zms", "microsegmentation", "security", "firewall", "access-policy", "private-access", "url-filtering", "dlp", "ssl-inspection", "digital-experience", "attack-surface", "z-insights"]
author: "Zscaler"
---

# Zscaler Zero Trust Power

## Overview

The Zscaler Power provides AI-assisted management of the Zscaler Zero Trust Exchange platform. With 360+ tools across 9 services and 41 guided skills, you can query, explore, and manage your entire Zscaler environment through natural language.

**Key capabilities:**

- **ZPA (Zscaler Private Access)** — Application segments (standard / BA / PRA), access/forwarding/timeout/isolation policies, server groups, connectors, PRA portals/credentials, BA certificates, LSS (104 tools)
- **ZIA (Zscaler Internet Access)** — Cloud firewall, URL filtering, SSL inspection, DLP, locations, static IPs, VPN credentials, GRE tunnels, sandbox, ATP policy, Cloud App Control, file-type control (149 tools)
- **ZDX (Zscaler Digital Experience)** — Application scores, device health, alerts, deep traces, software inventory (31 tools)
- **Z-Insights (Business Analytics)** — Web traffic, cyber incidents, shadow IT, CASB, firewall analytics, IoT (16 tools, read-only)
- **ZCC (Zscaler Client Connector)** — Device enrollment, forwarding profiles, trusted networks, per-device OTP (4 tools, read-only)
- **ZTW (Workload Segmentation)** — IP groups, network services, cloud accounts, discovery (19 tools)
- **ZMS (Zscaler Microsegmentation)** — Agent-based east-west segmentation: agents, resource groups, segmentation policy rules, app zones, app catalog, tag classification (20 tools, read-only)
- **EASM (External Attack Surface Management)** — Findings, lookalike domains, scan evidence (7 tools, read-only)
- **ZIdentity** — Users, groups, identity management (10 tools, read-only)

**Authentication**: Requires Zscaler OneAPI credentials from your ZIdentity console (client ID, client secret, customer ID, vanity domain).

**Security Model:**

- **Read-only by default** — Safe for autonomous AI operations
- **Write operations require explicit opt-in** — `--enable-write-tools` + `--write-tools` allowlist
- **Destructive operations require confirmation** — Delete operations prompt for approval

## Available Steering Files

This power has the following steering files for on-demand context loading. Each per-service file also catalogs the **guided skills** available for that service so Kiro can autoload the right multi-step playbook when the user's intent matches.

- **zpa** — ZPA private access: dependency chains, application onboarding (standard / BA / PRA), access policy condition types, LSS, 11 guided skills, 104 tools
- **zia** — ZIA internet access: activation requirement, location onboarding, SSL/URL/DLP audit, ATP policy, Cloud App Control, 12 guided skills, 149 tools
- **zdx** — ZDX digital experience: score interpretation, filtering parameters, troubleshooting, mandatory `.docx` + `.html` reports, 6 guided skills, 31 tools
- **zins** — Z-Insights analytics: cyber incident investigation, shadow IT, firewall analytics, 4 guided skills, 16 tools (read-only)
- **zcc** — ZCC client connector: device inventory, forwarding profiles, OTP retrieval, 1 guided skill, 4 tools (read-only)
- **ztw** — ZTW workload segmentation: IP groups, network services, cloud discovery, 19 tools
- **zms** — ZMS microsegmentation: agent fleet, resource groups, segmentation policy rules, tag classification, GraphQL specifics, 5 guided skills, 20 tools (read-only)
- **easm** — EASM attack surface: finding investigation, lookalike domains, 1 guided skill, 7 tools (read-only)
- **zid** — ZIdentity: user/group management, cross-service correlation, 10 tools (read-only)
- **cross-product** — Cross-product troubleshooting: ZCC + ZDX + ZPA + ZIA correlation, 1 guided skill

Load a steering file when the user's request matches that service. For example, load **zpa** when the user mentions private access, application segments, or access policies. Load **cross-product** when the issue spans multiple services. Load **zms** when the request is about agent-based microsegmentation between workloads (distinct from ZTW, which is IP-group / network-service based).

## Skills (Guided Workflows)

**Skills are auto-activated** when the user's description matches a skill's frontmatter. The per-service steering files above include an "Available Skills" section enumerating every skill relevant to that service with a "When to use" cue. Before composing an ad-hoc workflow, **scan the relevant steering file's skills table first** — a guided skill is almost always more reliable than rebuilding the workflow from raw tool calls.

Skills live at `skills/<service>/<skill-name>/SKILL.md` in the repo. Currently shipped:

- **ZPA** (11): app segment onboarding (standard / BA / PRA), baseline audit, access / conditional access / forwarding / timeout / session-duration / server-group, connector troubleshooting
- **ZIA** (12): location onboarding, SSL bypass audit, user URL access check, rule creation (URL / firewall / SSL / cloud app control), sandbox & URL category investigation, cloud-app name lookup, rule-target lookup, time-interval management
- **ZDX** (6): user experience troubleshooting, application health, alert investigation, deep trace, software audit, location comparison
- **Z-Insights** (4): security incident, shadow IT, web traffic, network security
- **ZMS** (5): posture audit, workload protection, policy analysis, tag classification, agent troubleshooting
- **ZCC** (1): generate logout OTP
- **EASM** (1): attack surface review
- **Cross-product** (1): user connectivity troubleshooting (ZCC + ZDX + ZPA + ZIA)

## Available MCP Servers

### zscaler

**Package:** `zscaler-mcp` via uvx or Docker
**Connection:** Local STDIO or remote HTTP (streamable-http). For remote deployment (EC2, VM), see [Remote MCP Deployment](../../docs/deployment/authentication-and-deployment.md#remote-deployment-ec2-vm-etc).

**Tool naming convention:** All tools follow `{service}_{verb}_{resource}` — e.g., `zia_list_locations`, `zpa_create_access_policy_rule`, `zdx_get_application`. Use the service prefix to discover tools: `zia_`, `zpa_`, `zdx_`, `zcc_`, `zeasm_`, `zins_`, `zid_`, `ztw_`, `zms_`.

**Tool categories by service:**

| Service | Read Tools | Write Tools | Total |
|---------|-----------|-------------|-------|
| ZPA | 51 (list/get for segments + BA + PRA, groups, policies, certs, LSS) | 53 (create/update/delete) | 104 |
| ZIA | 76 (list/get for rules, categories, locations, sandbox, ATP, CAC) | 73 (create/update/delete + activate) | 149 |
| ZDX | 27 (list/get for apps, devices, alerts, software, deep traces) | 4 (start/delete deep trace, start/delete analysis) | 31 |
| Z-Insights | 16 (traffic, incidents, shadow IT, firewall, IoT) | 0 (read-only) | 16 |
| ZMS | 20 (agents, resources, resource groups, policies, app zones, tags) | 0 (read-only) | 20 |
| ZTW | 13 (IP groups, services, cloud, discovery) | 6 (create/delete) | 19 |
| ZIdentity | 10 (users, groups, search) | 0 (read-only) | 10 |
| EASM | 7 (organizations, findings, lookalike domains) | 0 (read-only) | 7 |
| ZCC | 4 (devices, trusted networks, forwarding profiles, OTP) | 0 (read-only) | 4 |

See the individual steering files for complete tool lists with parameters.

## Critical Gotchas

1. **ZIA requires activation.** After any ZIA create/update/delete, call `zia_activate_configuration()`. Changes are staged until activation. This is the #1 source of "my change didn't work."
2. **ZPA dependency chains.** App onboarding order: connector group → server group → segment group → app segment → access policy rule. Out-of-order creation causes 400 errors.
3. **ZIA location dependency chain.** Location onboarding: static IP → VPN credential → location → activate.
4. **ZDX is entirely read-only.** No create/update/delete operations exist (except deep traces).
5. **ZDX `since` parameter is in hours**, not timestamps. Default is 2 hours. Example: `since=24` means "last 24 hours."
6. **Policy rules are evaluated top-to-bottom.** Order matters for ZPA access policies and ZIA firewall/URL/SSL/DLP rules.
7. **IDs are strings**, even when they look numeric.
8. **OneAPI-only authentication.** Every tool authenticates via `zscaler.ZscalerClient` against ZIdentity using the unified `ZSCALER_CLIENT_ID` / `ZSCALER_CLIENT_SECRET` (or `ZSCALER_PRIVATE_KEY`) / `ZSCALER_VANITY_DOMAIN` / `ZSCALER_CUSTOMER_ID` (ZPA only) credentials.

## Common Workflows

**Prefer skills over hand-built workflows.** Each workflow below has a matching guided skill that auto-activates on description match — load the SKILL.md and follow it. The raw tool sequences here are reference material for cases where the request doesn't cleanly match a skill.

### Application Onboarding (ZPA)
```
Skill: skills/zpa/application_segment-onboard/SKILL.md (or -ba- / -pra- for typed segments)
Steering: zpa

1. zpa_list_app_connector_groups   → Check for existing connector group
2. zpa_create_app_connector_group  → Create if needed
3. zpa_create_server_group         → References connector group
4. zpa_create_segment_group        → Create or use existing
5. zpa_create_application_segment  → Domains, ports, server+segment group IDs
6. zpa_create_access_policy_rule   → Grant access with identity conditions
```

### Location Onboarding (ZIA)
```
Skill: skills/zia/onboard-location/SKILL.md
Steering: zia

1. zia_create_static_ip          → Register site's public IP
2. zia_create_vpn_credential     → Create VPN credential referencing static IP
3. zia_create_location           → Create location referencing VPN credential
4. zia_activate_configuration    → Push changes live
```

### User Troubleshooting (Cross-Product)
```
Skill: skills/cross-product/troubleshoot-user-connectivity/SKILL.md
Steering: cross-product

1. zcc_list_devices              → Check device enrollment
2. zdx_get_device                → Check device health
3. zdx_get_application_score_trend → Check app performance
4. zpa_list_access_policy_rules  → Verify access policies (private apps)
5. zia_list_url_filtering_rules  → Check URL policies (internet apps)
```

### Security Incident Investigation (Z-Insights)
```
Skill: skills/zins/investigate-security-incident/SKILL.md
Steering: zins

1. zins_get_cyber_incidents                  → Incident overview
2. zins_get_cyber_incidents_by_location      → Affected locations
3. zins_get_cyber_incidents_daily            → Timeline
4. zins_get_threat_super_categories          → Threat breakdown
```

### Attack Surface Review (EASM)
```
Skill: skills/easm/review-attack-surface/SKILL.md
Steering: easm

1. zeasm_list_findings           → Get all findings by severity
2. zeasm_get_finding_details     → Investigate specific finding
3. zeasm_list_lookalike_domains  → Check brand impersonation
```

### Microsegmentation Posture (ZMS)
```
Skill: skills/zms/audit-microsegmentation-posture/SKILL.md
Steering: zms

1. zms_list_agents + zms_get_agent_connection_status_statistics → Agent fleet health
2. zms_list_resources + zms_get_resource_protection_status      → Workload protection coverage
3. zms_list_resource_groups                                     → Managed vs Unmanaged group structure
4. zms_list_policy_rules + zms_list_default_policy_rules        → Segmentation policy footprint
5. zms_list_app_zones + zms_list_app_catalog                    → Policy scope + app inventory
```

## Best Practices

### Do:

- **Start with discovery** — Use `list_*` tools to understand current state before making changes
- **Confirm before modifying** — Always explain proposed changes and get user confirmation for write operations
- **Respect dependency chains** — See ZPA and ZIA steering files for required creation order
- **Activate ZIA changes** — Always call `zia_activate_configuration` after ZIA write operations
- **Use ZDX filtering** — Pass `location_id`, `department_id`, `geo_id`, `since` to narrow ZDX queries
- **Load steering files on demand** — Only load the steering file for the service being discussed

### Don't:

- **Skip activation** — ZIA changes are invisible until activated
- **Create ZPA resources out of order** — Causes cryptic 400 errors
- **Run broad ZDX queries on large tenants** — Always ask for scope first
- **Delete resources without checking dependencies** — App segments referenced by policy rules can't be deleted

## Troubleshooting

### Authentication Errors
- Verify `ZSCALER_CLIENT_ID` and `ZSCALER_CLIENT_SECRET` are correct
- Check `ZSCALER_VANITY_DOMAIN` and `ZSCALER_CUSTOMER_ID`
- Ensure API client has required scopes in ZIdentity console

### Permission Errors
- Write operations require `--enable-write-tools` flag when starting the server
- Specific tools must be in `--write-tools` allowlist

### 400 Bad Request (Dependency Errors)
- Usually means a ZPA/ZIA resource was created out of order
- Load the relevant steering file (zpa or zia) and follow the dependency chain

### "Changes didn't take effect"
- Check `zia_get_activation_status` — status is likely "PENDING"
- Call `zia_activate_configuration` to push changes live

## Configuration

**Authentication Required**: Zscaler OneAPI credentials from ZIdentity console

**Setup Steps:**

1. Log in to your ZIdentity console
2. Navigate to API Clients and create a new client
3. Copy: Client ID, Client Secret, Customer ID, Vanity Domain
4. Configure in Kiro when installing this power

**MCP Configuration:**

```json
{
  "mcpServers": {
    "zscaler": {
      "command": "uvx",
      "args": ["zscaler-mcp"],
      "env": {
        "ZSCALER_CLIENT_ID": "${ZSCALER_CLIENT_ID}",
        "ZSCALER_CLIENT_SECRET": "${ZSCALER_CLIENT_SECRET}",
        "ZSCALER_CUSTOMER_ID": "${ZSCALER_CUSTOMER_ID}",
        "ZSCALER_VANITY_DOMAIN": "${ZSCALER_VANITY_DOMAIN}"
      }
    }
  }
}
```

**Alternative (Docker):**

```json
{
  "mcpServers": {
    "zscaler": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/path/to/your/.env",
        "zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

## Tips

1. **Load steering files dynamically** — Only load the service-specific steering file when the user's request matches it
2. **ZDX is your diagnostic starting point** — ZDX scores tell you if something is wrong; ZPA/ZIA steering tells you why
3. **Use `zia_url_lookup` before making URL policy changes** — Understand the current classification first
4. **Cross-product issues are common** — When one service can't explain the issue, load the cross-product steering file
5. **ZPA condition types are complex** — Load the ZPA steering file for the full condition type reference before creating policy rules
6. **Always paginate** — List tools support `page` and `page_size` for large tenants
7. **Check existing resources first** — Use `list_*` before `create_*` to avoid duplicates

## Resources

- **Documentation**: https://zscaler-mcp-server.readthedocs.io/
- **GitHub**: https://github.com/zscaler/zscaler-mcp-server
- **PyPI**: https://pypi.org/project/zscaler-mcp/
- **Docker**: hhttps://hub.docker.com/r/zscaler/zscaler-mcp-server
- **AWS Marketplace**: Available on Amazon Bedrock AgentCore

## License and support

This power integrates with [Zscaler MCP Server](https://github.com/zscaler/zscaler-mcp-server) (MIT).
- [Privacy Policy](https://www.zscaler.com/privacy)
- [Support](https://help.zscaler.com/contact-support)
