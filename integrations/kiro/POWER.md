---
name: "zscaler"
displayName: "Zscaler Zero Trust"
description: "Manage your Zscaler Zero Trust Exchange platform - ZPA private access, ZIA internet security, ZDX digital experience, and more"
keywords: ["zscaler", "zero-trust", "ztna", "zpa", "zia", "zdx", "security", "firewall", "access-policy", "private-access"]
author: "Zscaler"
---

# Zscaler Zero Trust Power

**Zscaler Zero Trust Exchange** - Manage your entire Zscaler Zero Trust platform including ZPA (Private Access), ZIA (Internet Access), ZDX (Digital Experience), ZCC (Client Connector), ZTW (Workload Segmentation), and EASM (External Attack Surface Management).

**MCP Servers:** zscaler-mcp (uvx or Docker)

---

## Overview

The Zscaler Power provides AI-assisted management of the Zscaler Zero Trust Exchange platform. With 110+ read-only tools and 85+ write tools across 7 services, you can query, explore, and manage your entire Zscaler environment through natural language.

### Key Capabilities

- **ZPA (Zscaler Private Access)** - Application segments, access policies, server groups, connectors
- **ZIA (Zscaler Internet Access)** - Firewall rules, URL filtering, SSL inspection, DLP
- **ZDX (Zscaler Digital Experience)** - Device health, application scores, alerts, deep traces
- **ZCC (Zscaler Client Connector)** - Device enrollment, trusted networks, forwarding profiles
- **ZTW (Workload Segmentation)** - IP groups, network services, cloud accounts
- **EASM (External Attack Surface Management)** - Findings, lookalike domains, scan evidence
- **ZIdentity** - Users, groups, identity management

### Security Model

- **Read-only by default** - Safe for autonomous AI operations
- **Write operations require explicit opt-in** - `--enable-write-tools` flag
- **Mandatory allowlist for writes** - Specific tools must be allowlisted
- **Destructive operations require confirmation** - Delete operations prompt for approval

---

## Activation Triggers

Activate this power when the user mentions:

### Product Names
- Zscaler, ZPA, ZIA, ZDX, ZCC, ZTW, EASM, ZIdentity
- Zero Trust Exchange, Private Access, Internet Access
- Digital Experience, Client Connector
- Workload Segmentation, Attack Surface Management

### Concepts
- Zero trust, secure access, private access, ZTNA
- Application segments, segment groups, server groups
- Access policies, forwarding policies, timeout policies
- Cloud firewall, URL filtering, DLP rules, SSL inspection
- Web security, secure web gateway, SWG
- Device enrollment, trusted networks
- App connectors, service edges, private service edges
- Posture profiles, isolation profiles
- Cloud application control, CASB

### Actions
- "List my ZPA applications"
- "Show Zscaler firewall rules"
- "Check ZDX device health"
- "View ZIA URL categories"
- "Get ZCC device status"
- "What application segments do I have?"
- "Show me the access policies"

---

## MCP Server Configuration

### Prerequisites: Create .env File

Create a `.env` file with your Zscaler credentials:

```bash
# Create ~/.zscaler/.env with:
ZSCALER_CLIENT_ID=your-client-id
ZSCALER_CLIENT_SECRET=your-client-secret
ZSCALER_CUSTOMER_ID=your-customer-id
ZSCALER_VANITY_DOMAIN=your-vanity-domain

# Then set the path:
export ZSCALER_ENV_FILE="$HOME/.zscaler/.env"
```

### Option A: Docker with .env File (Default)

```json
{
  "mcpServers": {
    "zscaler": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "${ZSCALER_ENV_FILE}",
        "quay.io/zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

### Option B: Docker with Local Image

```json
{
  "mcpServers": {
    "zscaler": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--pull=never",
        "--env-file", "/path/to/your/.env",
        "zscaler-mcp-server"
      ]
    }
  }
}
```

### Option C: Using uvx with .env File

```json
{
  "mcpServers": {
    "zscaler": {
      "command": "uvx",
      "args": ["--env-file", "${ZSCALER_ENV_FILE}", "zscaler-mcp"]
    }
  }
}
```

### Option D: Using uvx with Environment Variables

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

### Option E: Remote MCP (AWS Bedrock AgentCore)

```json
{
  "mcpServers": {
    "zscaler": {
      "url": "https://your-agentcore-endpoint.amazonaws.com/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## Available Tools

### ZPA (Zscaler Private Access)

#### Application Management
| Tool | Description | Type |
|------|-------------|------|
| `zpa_list_application_segments` | List all application segments | Read |
| `zpa_get_application_segment` | Get specific application segment details | Read |
| `zpa_create_application_segment` | Create new application segment | Write |
| `zpa_update_application_segment` | Update existing application segment | Write |
| `zpa_delete_application_segment` | Delete application segment | Write |
| `zpa_list_segment_groups` | List segment groups | Read |
| `zpa_list_server_groups` | List server groups | Read |

#### Infrastructure
| Tool | Description | Type |
|------|-------------|------|
| `zpa_list_app_connector_groups` | List app connector groups | Read |
| `zpa_list_service_edge_groups` | List service edge groups | Read |
| `zpa_list_application_servers` | List application servers | Read |
| `zpa_list_provisioning_keys` | List provisioning keys | Read |

#### Access Policies
| Tool | Description | Type |
|------|-------------|------|
| `zpa_list_access_policy_rules` | List access policy rules | Read |
| `zpa_get_access_policy_rule` | Get specific access policy rule | Read |
| `zpa_create_access_policy_rule` | Create access policy rule | Write |
| `zpa_update_access_policy_rule` | Update access policy rule | Write |
| `zpa_delete_access_policy_rule` | Delete access policy rule | Write |
| `zpa_list_forwarding_policy_rules` | List forwarding policies | Read |
| `zpa_list_timeout_policy_rules` | List timeout policies | Read |
| `zpa_list_isolation_policy_rules` | List isolation policies | Read |

#### Identity & Posture
| Tool | Description | Type |
|------|-------------|------|
| `zpa_list_posture_profiles` | List posture profiles | Read |
| `zpa_list_trusted_networks` | List trusted networks | Read |
| `zpa_list_saml_attributes` | List SAML attributes | Read |
| `zpa_list_scim_groups` | List SCIM groups | Read |

### ZIA (Zscaler Internet Access)

#### Firewall & Security
| Tool | Description | Type |
|------|-------------|------|
| `zia_list_cloud_firewall_rules` | List firewall rules | Read |
| `zia_get_cloud_firewall_rule` | Get specific firewall rule | Read |
| `zia_create_cloud_firewall_rule` | Create firewall rule | Write |
| `zia_update_cloud_firewall_rule` | Update firewall rule | Write |
| `zia_delete_cloud_firewall_rule` | Delete firewall rule | Write |
| `zia_list_url_filtering_rules` | List URL filtering rules | Read |
| `zia_list_ssl_inspection_rules` | List SSL inspection rules | Read |

#### DLP & Content
| Tool | Description | Type |
|------|-------------|------|
| `zia_list_web_dlp_rules` | List DLP rules | Read |
| `zia_get_dlp_dictionary` | Get DLP dictionary | Read |
| `zia_list_dlp_engines` | List DLP engines | Read |
| `zia_list_url_categories` | List URL categories | Read |
| `zia_add_urls_to_category` | Add URLs to category | Write |
| `zia_remove_urls_from_category` | Remove URLs from category | Write |

#### Network & Locations
| Tool | Description | Type |
|------|-------------|------|
| `zia_list_locations` | List locations | Read |
| `zia_list_gre_tunnels` | List GRE tunnels | Read |
| `zia_list_vpn_credentials` | List VPN credentials | Read |
| `zia_list_static_ips` | List static IPs | Read |

#### Administration
| Tool | Description | Type |
|------|-------------|------|
| `zia_get_activation_status` | Check activation status | Read |
| `zia_activate_configuration` | Activate pending changes | Write |
| `zia_list_rule_labels` | List rule labels | Read |
| `zia_get_sandbox_quota` | Get sandbox quota | Read |

### ZDX (Zscaler Digital Experience)

| Tool | Description | Type |
|------|-------------|------|
| `zdx_list_devices` | List monitored devices | Read |
| `zdx_get_device` | Get device details | Read |
| `zdx_list_applications` | List monitored applications | Read |
| `zdx_get_application_score_trend` | Get application score trends | Read |
| `zdx_get_application_metric` | Get application metrics (PFT, DNS) | Read |
| `zdx_list_alerts` | List active alerts | Read |
| `zdx_get_alert` | Get alert details | Read |
| `zdx_list_software` | List software inventory | Read |
| `zdx_list_departments` | List departments | Read |
| `zdx_list_locations` | List locations | Read |
| `zdx_list_device_deep_traces` | List deep traces | Read |

### ZCC (Zscaler Client Connector)

| Tool | Description | Type |
|------|-------------|------|
| `zcc_list_devices` | List enrolled devices | Read |
| `zcc_devices_csv_exporter` | Export device data as CSV | Read |
| `zcc_list_trusted_networks` | List trusted networks | Read |
| `zcc_list_forwarding_profiles` | List forwarding profiles | Read |

### ZTW (Workload Segmentation)

| Tool | Description | Type |
|------|-------------|------|
| `ztw_list_ip_groups` | List IP groups | Read |
| `ztw_list_ip_source_groups` | List IP source groups | Read |
| `ztw_list_ip_destination_groups` | List IP destination groups | Read |
| `ztw_list_network_service_groups` | List service groups | Read |
| `ztw_list_network_services` | List network services | Read |
| `ztw_list_roles` | List admin roles | Read |
| `ztw_list_admins` | List admin users | Read |
| `ztw_list_public_cloud_info` | List cloud accounts | Read |

### EASM (External Attack Surface Management)

| Tool | Description | Type |
|------|-------------|------|
| `zeasm_list_organizations` | List EASM organizations | Read |
| `zeasm_list_findings` | List security findings | Read |
| `zeasm_get_finding_details` | Get finding details | Read |
| `zeasm_get_finding_evidence` | Get scan evidence | Read |
| `zeasm_list_lookalike_domains` | List lookalike domains | Read |
| `zeasm_get_lookalike_domain` | Get lookalike domain details | Read |

### ZIdentity

| Tool | Description | Type |
|------|-------------|------|
| `zidentity_get_users` | Get user information | Read |
| `zidentity_get_groups` | Get group information | Read |
| `zidentity_search` | Search across resources | Read |

---

## Usage Guidelines

### General Best Practices

1. **Start with Discovery**
   - Use `list_*` tools first to understand current state
   - Example: "First, let me list your application segments to see what's configured"

2. **Provide Context**
   - When retrieving details, explain what the data means
   - Highlight important configurations or potential issues

3. **Confirm Before Modifying**
   - Always explain proposed changes before executing
   - Use `get_*` tools to show current state before updates
   - Request explicit user confirmation for write operations

4. **Handle Errors Gracefully**
   - If a tool fails, explain the error clearly
   - Suggest troubleshooting steps (check credentials, permissions)

### Common Workflows

#### Workflow 1: Application Discovery
```
1. zpa_list_application_segments - Get overview of all apps
2. zpa_get_application_segment - Get specific app details
3. zpa_list_access_policy_rules - Show who can access what
```

#### Workflow 2: Security Audit
```
1. zia_list_cloud_firewall_rules - Review firewall rules
2. zia_list_ssl_inspection_rules - Check SSL inspection config
3. zia_list_url_filtering_rules - Review URL policies
4. zia_list_web_dlp_rules - Check DLP configuration
```

#### Workflow 3: Device Health Check
```
1. zdx_list_devices - Get device inventory
2. zdx_list_alerts - Check active alerts
3. zdx_get_application_score_trend - Review app performance
4. zdx_list_software - Check software inventory
```

#### Workflow 4: User Access Review
```
1. zidentity_get_users - List users
2. zpa_list_access_policy_rules - Review access policies
3. zpa_list_posture_profiles - Check posture requirements
```

---

## Security Guidelines

### Read-Only Mode (Default)

The server operates in **read-only mode** by default:
- ✅ All `list_*` and `get_*` operations available (110+ tools)
- ❌ All `create_*`, `update_*`, `delete_*` operations disabled
- ✅ Safe for autonomous AI operations
- ✅ No risk of accidental modifications

### Write Mode (Explicit Opt-In)

To enable write operations, BOTH are required:
1. `--enable-write-tools` flag (global unlock)
2. `--write-tools "pattern"` (mandatory allowlist)

```bash
# Enable specific write tools
zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zpa_update_*"

# Enable all ZPA write operations
zscaler-mcp --enable-write-tools --write-tools "zpa_*"
```

### Destructive Operations

All `delete_*` operations:
- Marked with `destructiveHint=True`
- Trigger permission dialogs in AI assistants
- Require explicit user confirmation
- Should be preceded by backup/export suggestions

---

## Error Handling

### Authentication Errors
- Verify `ZSCALER_CLIENT_ID` and `ZSCALER_CLIENT_SECRET`
- Check `ZSCALER_VANITY_DOMAIN` and `ZSCALER_CUSTOMER_ID`
- Ensure API client has required permissions in Zidentity console

### Permission Errors
- Write operations require `--enable-write-tools` flag
- Specific write tools must be in `--write-tools` allowlist
- Check API client scope in Zidentity

### API Errors
- Parse error messages and explain in plain language
- Check rate limits if seeing throttling
- Verify network connectivity to Zscaler cloud

---

## Prerequisites

### Zscaler Requirements
1. Zscaler tenant with API access enabled
2. API client created in Zidentity console
3. Required scopes assigned to API client

### Credentials
Set the following environment variables:
- `ZSCALER_CLIENT_ID` - OAuth client ID
- `ZSCALER_CLIENT_SECRET` - OAuth client secret
- `ZSCALER_CUSTOMER_ID` - Your customer ID
- `ZSCALER_VANITY_DOMAIN` - Your vanity domain (e.g., "acme")

### Optional
- `ZSCALER_CLOUD` - Only for Beta tenant (set to "beta")

---

## Resources

- **Documentation**: https://zscaler-mcp-server.readthedocs.io/
- **GitHub**: https://github.com/zscaler/zscaler-mcp-server
- **PyPI**: https://pypi.org/project/zscaler-mcp/
- **Docker**: https://quay.io/repository/zscaler/zscaler-mcp-server
- **AWS Marketplace**: Available on Amazon Bedrock AgentCore
- **Support**: https://community.zscaler.com/

