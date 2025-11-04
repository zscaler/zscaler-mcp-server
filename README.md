![Zscaler MCP](https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/docs/media/zscaler.svg)

[![PyPI version](https://badge.fury.io/py/zscaler-mcp.svg)](https://badge.fury.io/py/zscaler-mcp)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zscaler-mcp)](https://pypi.org/project/zscaler-mcp/)
[![Documentation Status](https://readthedocs.org/projects/zscaler-mcp-server/badge/?version=latest)](https://zscaler-mcp-server.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/github/license/zscaler/zscaler-mcp-server.svg)](https://github.com/zscaler/zscaler-mcp-server)
[![Zscaler Community](https://img.shields.io/badge/zscaler-community-blue)](https://community.zscaler.com/)

**zscaler-mcp-server** is a Model Context Protocol (MCP) server that connects AI agents with the Zscaler Zero Trust Exchange platform. **By default, the server operates in read-only mode** for security, requiring explicit opt-in to enable write operations.

## Support Disclaimer

-> **Disclaimer:** Please refer to our [General Support Statement](https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/support.md) before proceeding with the use of this provider. You can also refer to our [troubleshooting guide](https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/TROUBLESHOOTING.md) for guidance on typical problems.

> [!IMPORTANT]
> **🚧 Public Preview**: This project is currently in public preview and under active development. Features and functionality may change before the stable 1.0 release. While we encourage exploration and testing, please avoid production deployments. We welcome your feedback through [GitHub Issues](https://github.com/zscaler/zscaler-mcp-server/issues) to help shape the final release.

## 📄 Table of contents

- [📺 Overview](#overview)
- [🔒 Security & Permissions](#security-permissions)
- [Supported Tools](#supported-tools)
  - [ZCC Features](#zcc-features)
  - [ZDX Features](#zdx-features)
  - [ZIdentity Features](#zidentity-features)
  - [ZIA Features](#zia-features)
  - [ZPA Features](#zpa-features)
  - [ZTW Features](#ztw-features)
- [Installation & Setup](#installation-setup)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Installation](#installation)
- [Usage](#usage)
  - [Command Line](#command-line)
  - [Service Configuration](#service-configuration)
  - [Additional Command Line Options](#additional-command-line-options)
- [Zscaler API Credentials & Authentication](#zscaler-api-credentials-authentication)
  - [Zscaler OneAPI Authentication](#zscaler-oneapi-authentication)
  - [Using Legacy Mode with Environment Variable](#using-legacy-mode-with-environment-variable)
  - [Zscaler Legacy API Login](#zscaler-legacy-api-login)
    - [ZIA Legacy Authentication](#zia-legacy-authentication)
    - [ZPA Legacy Authentication](#zpa-legacy-authentication)
    - [ZCC Legacy Authentication](#zcc-legacy-authentication)
    - [ZDX Legacy Authentication](#zdx-legacy-authentication)
- [Internal Environment Variables](#internal-environment-variables)
  - [MCP Server Configuration](#mcp-server-configuration)
  - [OneAPI Authentication](#oneapi-authentication)
  - [Legacy Authentication](#legacy-authentication-when-zscaler-use-legacy-true)
- [As a Library](#as-a-library)
- [Container Usage](#container-usage)
  - [Using Pre-built Image (Recommended)](#using-pre-built-image-recommended)
  - [Building Locally (Development)](#building-locally-development)
- [Editor/Assistant Integration](#editor-assistant-integration)
  - [Using `uvx` (recommended)](#using-uvx-recommended)
  - [With Service Selection](#with-service-selection)
  - [Using Individual Environment Variables](#using-individual-environment-variables)
  - [Docker Version](#docker-version)
- [Additional Deployment Options](#additional-deployment-options)
  - [Amazon Bedrock AgentCore](#amazon-bedrock-agentcore)
- [Using the MCP Server with Agents](#using-the-mcp-server-with-agents)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [Visual Studio Code + GitHub Copilot](#visual-studio-code-github-copilot)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
  - [Getting Started for Contributors](#getting-started-for-contributors)
  - [Running Tests](#running-tests)
- [License](#license)

## 📺 Overview

The Zscaler Integrations MCP Server brings context to your agents. Try prompts like:

- "List my ZPA Application segments"
- "List my ZPA Segment Groups"
- "List my ZIA Rule Labels"

> [!WARNING]
> **🔒 READ-ONLY BY DEFAULT**: For security, this MCP server operates in **read-only mode** by default. Only `list_*` and `get_*` operations are available. To enable tools that can **CREATE, UPDATE, or DELETE** Zscaler resources, you must explicitly enable write mode using the `--enable-write-tools` flag or by setting `ZSCALER_MCP_WRITE_ENABLED=true`. See the [Security & Permissions](#-security--permissions) section for details.

## 🔒 Security & Permissions

The Zscaler MCP Server implements a **security-first design** with granular permission controls and safe defaults:

### Read-Only Mode (Default - Always Available)

By default, the server operates in **read-only mode**, exposing only tools that list or retrieve information:

- ✅ **ALWAYS AVAILABLE** - Read-only tools are registered by the server
- ✅ Safe to use with AI agents autonomously
- ✅ No risk of accidental resource modification or deletion
- ✅ All `list_*` and `get_*` operations are available (110+ read-only tools)
- ❌ All `create_*`, `update_*`, and `delete_*` operations are disabled by default
- 💡 Note: You may need to enable read-only tools in your AI agent's UI settings

```bash
# Read-only mode (default - safe)
zscaler-mcp
```

When the server starts in read-only mode, you'll see:

```text
🔒 Server running in READ-ONLY mode (safe default)
   Only list and get operations are available
   To enable write operations, use --enable-write-tools AND --write-tools flags
```

> **💡 Read-only tools are ALWAYS registered** by the server regardless of any flags. You never need to enable them server-side. Note: Your AI agent UI (like Claude Desktop) may require you to enable individual tools before use.

### Write Mode (Explicit Opt-In - Allowlist REQUIRED)

To enable tools that can create, modify, or delete Zscaler resources, you must provide **BOTH** flags:

1. ✅ `--enable-write-tools` - Global unlock for write operations
2. ✅ `--write-tools "pattern"` - **MANDATORY** explicit allowlist

> **🔐 SECURITY: Allowlist is MANDATORY** - If you set `--enable-write-tools` without `--write-tools`, **0 write tools will be registered**. This ensures you consciously choose which write operations to enable.

```bash
# ❌ WRONG: This will NOT enable any write tools (allowlist missing)
zscaler-mcp --enable-write-tools

# ✅ CORRECT: Explicit allowlist required
zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zpa_delete_*"
```

When you try to enable write mode without an allowlist:

```text
⚠️  WRITE TOOLS MODE ENABLED
⚠️  NO allowlist provided - 0 write tools will be registered
⚠️  Read-only tools will still be available
⚠️  To enable write operations, add: --write-tools 'pattern'
```

#### Write Tools Allowlist (MANDATORY)

The allowlist provides **two-tier security**:

1. ✅ **First Gate**: `--enable-write-tools` must be set (global unlock)
2. ✅ **Second Gate**: Explicit allowlist determines which write tools are registered (MANDATORY)

**Allowlist Examples:**

```bash
# Enable ONLY specific write tools with wildcards
zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zpa_delete_*"

# Enable specific tools without wildcards
zscaler-mcp --enable-write-tools --write-tools "zpa_create_application_segment,zia_create_rule_label"

# Enable all ZPA write operations (but no ZIA/ZDX/ZTW)
zscaler-mcp --enable-write-tools --write-tools "zpa_*"
```

Or via environment variable:

```bash
export ZSCALER_MCP_WRITE_ENABLED=true
export ZSCALER_MCP_WRITE_TOOLS="zpa_create_*,zpa_delete_*"
zscaler-mcp
```

**Wildcard patterns supported:**

- `zpa_create_*` - Allow all ZPA creation tools
- `zpa_delete_*` - Allow all ZPA deletion tools
- `zpa_*` - Allow all ZPA write tools
- `*_application_segment` - Allow all operations on application segments
- `zpa_create_application_segment` - Exact match (no wildcard)

When using a valid allowlist, you'll see:

```text
⚠️  WRITE TOOLS MODE ENABLED
⚠️  Explicit allowlist provided - only listed write tools will be registered
⚠️  Allowed patterns: zpa_create_*, zpa_delete_*
⚠️  Server can CREATE, MODIFY, and DELETE Zscaler resources
🔒 Security: 85 write tools blocked by allowlist, 8 allowed
```

### Tool Design Philosophy

Each operation is a **separate, single-purpose tool** with explicit naming that makes its intent clear:

#### ✅ Good (Verb-Based - Current Design)

```text
zpa_list_application_segments    ← Read-only, safe to allow-list
zpa_get_application_segment      ← Read-only, safe to allow-list
zpa_create_application_segment   ← Write operation, requires --enable-write-tools
zpa_update_application_segment   ← Write operation, requires --enable-write-tools
zpa_delete_application_segment   ← Destructive, requires --enable-write-tools
```

This design allows AI assistants (Claude, Cursor, GitHub Copilot) to:

- Allow-list read-only tools for autonomous exploration
- Require explicit user confirmation for write operations
- Clearly understand the intent of each tool from its name

### Security Layers

The server implements multiple layers of security (defense-in-depth):

1. **Read-Only Tools Always Enabled**: Safe `list_*` and `get_*` operations are always available (110+ tools)
2. **Default Write Mode Disabled**: Write tools are disabled unless explicitly enabled via `--enable-write-tools`
3. **Mandatory Allowlist**: Write operations require explicit `--write-tools` allowlist (wildcard support)
4. **Verb-Based Tool Naming**: Each tool clearly indicates its purpose (`list`, `get`, `create`, `update`, `delete`)
5. **Tool Metadata Annotations**: All tools are annotated with `readOnlyHint` or `destructiveHint` for AI agent frameworks
6. **AI Agent Confirmation**: All write tools marked with `destructiveHint=True` trigger permission dialogs in AI assistants
7. **Double Confirmation for DELETE**: Delete operations require both permission dialog AND server-side confirmation (extra protection for irreversible actions)
8. **Environment Variable Control**: `ZSCALER_MCP_WRITE_ENABLED` and `ZSCALER_MCP_WRITE_TOOLS` can be managed centrally
9. **Audit Logging**: All operations are logged for tracking and compliance

This multi-layered approach ensures that even if one security control is bypassed, others remain in place to prevent unauthorized operations.

**Key Security Principles**:

- No "enable all write tools" backdoor exists - allowlist is **mandatory**
- AI agents must request permission before executing any write operation (`destructiveHint`)
- Every destructive action requires explicit user approval through the AI agent's permission framework

### Best Practices

- **Read-Only by Default**: No configuration needed for safe operations - read-only tools are always available
- **Mandatory Allowlist**: Always provide explicit `--write-tools` allowlist when enabling write mode
- **Development/Testing**: Use narrow allowlists (e.g., `--write-tools "zpa_create_application_segment"`)
- **Production/Agents**: Keep server in read-only mode (default) for AI agents performing autonomous operations
- **CI/CD**: Never set `ZSCALER_MCP_WRITE_ENABLED=true` without a corresponding `ZSCALER_MCP_WRITE_TOOLS` allowlist
- **Least Privilege**: Use narrowest possible allowlist patterns for your use case
- **Wildcard Usage**: Use wildcards for service-level control (e.g., `zpa_create_*`) or operation-level control (e.g., `*_create_*`)
- **Audit Review**: Regularly review which write tools are allowlisted and remove unnecessary ones

## Supported Tools

The Zscaler Integrations MCP Server provides tools for all major Zscaler services. Each service offers specific functionality for managing and querying Zscaler resources.

### ZCC Features

All ZCC tools are **read-only** operations:

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zcc_list_devices` | Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal | Read-only |
| `zcc_devices_csv_exporter` | Downloads ZCC device information or service status as a CSV file | Read-only |
| `zcc_list_trusted_networks` | Returns the list of Trusted Networks By Company ID in the Client Connector Portal | Read-only |
| `zcc_list_forwarding_profiles` | Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal | Read-only |

### ZDX Features

All ZDX tools are **read-only** operations:

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zdx_list_departments` | Discover ZDX departments | Read-only |
| `zdx_list_locations` | Discover ZDX locations | Read-only |
| `zdx_list_devices` | List ZDX devices using various filters | Read-only |
| `zdx_get_device` | Get details for a specific ZDX device | Read-only |
| `zdx_list_applications` | List all active applications configured in ZDX | Read-only |
| `zdx_get_application` | Get details for a specific application | Read-only |
| `zdx_get_application_score_trend` | Get an application's ZDX score trend | Read-only |
| `zdx_get_application_metric` | Retrieve ZDX metrics for an application (PFT, DNS, availability) | Read-only |
| `zdx_list_application_users` | List users/devices for an application | Read-only |
| `zdx_get_application_user` | Get details for a specific application user | Read-only |
| `zdx_list_software` | List software inventory | Read-only |
| `zdx_get_software_details` | Get users/devices for a specific software key | Read-only |
| `zdx_list_alerts` | List ongoing alerts | Read-only |
| `zdx_get_alert` | Get details for a specific alert | Read-only |
| `zdx_list_alert_affected_devices` | List devices affected by an alert | Read-only |
| `zdx_list_historical_alerts` | List historical alert rules (ended alerts) | Read-only |
| `zdx_list_device_deep_traces` | List deep traces for a device | Read-only |
| `zdx_get_device_deep_trace` | Get details for a specific deep trace | Read-only |

### ZIdentity Features

All ZIdentity tools are **read-only** operations:

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zidentity_get_groups` | Retrieves Zidentity group information | Read-only |
| `zidentity_get_users` | Retrieves Zidentity user information | Read-only |
| `zidentity_search` | Search across Zidentity resources | Read-only |

### ZIA Features

ZIA provides both **read-only** and **write** tools. Write operations require `--enable-write-tools` flag:

#### Cloud Firewall Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_cloud_firewall_rules` | List ZIA cloud firewall rules | Read-only |
| `zia_get_cloud_firewall_rule` | Get a specific cloud firewall rule | Read-only |
| `zia_create_cloud_firewall_rule` | Create a new cloud firewall rule | Write |
| `zia_update_cloud_firewall_rule` | Update an existing cloud firewall rule | Write |
| `zia_delete_cloud_firewall_rule` | Delete a cloud firewall rule | Write |

#### URL Filtering Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_url_filtering_rules` | List ZIA URL filtering rules | Read-only |
| `zia_get_url_filtering_rule` | Get a specific URL filtering rule | Read-only |
| `zia_create_url_filtering_rule` | Create a new URL filtering rule | Write |
| `zia_update_url_filtering_rule` | Update an existing URL filtering rule | Write |
| `zia_delete_url_filtering_rule` | Delete a URL filtering rule | Write |

#### Web DLP Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_web_dlp_rules` | List ZIA web DLP rules | Read-only |
| `zia_list_web_dlp_rules_lite` | List ZIA web DLP rules (lite) | Read-only |
| `zia_get_web_dlp_rule` | Get a specific web DLP rule | Read-only |
| `zia_create_web_dlp_rule` | Create a new web DLP rule | Write |
| `zia_update_web_dlp_rule` | Update an existing web DLP rule | Write |
| `zia_delete_web_dlp_rule` | Delete a web DLP rule | Write |

#### Configuration Activation

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_get_activation_status` | Check ZIA configuration activation status | Read-only |
| `zia_activate_configuration` | Activate pending ZIA configuration changes | Write |

#### Cloud Applications

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_cloud_applications` | List ZIA cloud applications | Read-only |
| `zia_list_cloud_application_tags` | List cloud application tags | Read-only |
| `zia_bulk_update_cloud_applications` | Bulk update cloud applications | Write |

#### URL Categories

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_url_categories` | List URL categories | Read-only |
| `zia_get_url_category` | Get a specific URL category | Read-only |
| `zia_add_urls_to_category` | Add URLs to a category | Write |
| `zia_remove_urls_from_category` | Remove URLs from a category | Write |

#### GRE Tunnels & Ranges

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_gre_tunnels` | List GRE tunnels | Read-only |
| `zia_get_gre_tunnel` | Get a specific GRE tunnel | Read-only |
| `zia_get_gre_tunnel_info` | Get GRE tunnel information | Read-only |
| `zia_create_gre_tunnel` | Create a new GRE tunnel | Write |
| `zia_update_gre_tunnel` | Update an existing GRE tunnel | Write |
| `zia_delete_gre_tunnel` | Delete a GRE tunnel | Write |
| `zia_list_gre_ranges` | List available GRE IP ranges | Read-only |

#### Locations & VPN

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_locations` | List ZIA locations | Read-only |
| `zia_list_locations_lite` | List ZIA locations (lite) | Read-only |
| `zia_get_location` | Get a specific location | Read-only |
| `zia_create_location` | Create a new location | Write |
| `zia_update_location` | Update an existing location | Write |
| `zia_delete_location` | Delete a location | Write |
| `zia_list_vpn_credentials` | List VPN credentials | Read-only |
| `zia_get_vpn_credential` | Get specific VPN credential | Read-only |
| `zia_create_vpn_credential` | Create new VPN credential | Write |
| `zia_update_vpn_credential` | Update VPN credential | Write |
| `zia_delete_vpn_credential` | Delete VPN credential | Write |
| `zia_bulk_delete_vpn_credentials` | Bulk delete VPN credentials | Write |

#### Static IPs

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_static_ips` | List static IPs | Read-only |
| `zia_get_static_ip` | Get a specific static IP | Read-only |
| `zia_create_static_ip` | Create a new static IP | Write |
| `zia_update_static_ip` | Update an existing static IP | Write |
| `zia_delete_static_ip` | Delete a static IP | Write |

#### ATP & Security

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_atp_malicious_urls` | List ATP malicious URLs | Read-only |
| `zia_create_atp_malicious_url` | Add URL to denylist | Write |
| `zia_delete_atp_malicious_url` | Remove URL from denylist | Write |
| `zia_list_auth_exempt_urls` | List authentication exempt URLs | Read-only |
| `zia_create_auth_exempt_url` | Add URL to auth exempt list | Write |
| `zia_delete_auth_exempt_url` | Remove URL from auth exempt list | Write |

#### Groups & Users

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_ip_source_groups` | List IP source groups | Read-only |
| `zia_get_ip_source_group` | Get a specific IP source group | Read-only |
| `zia_create_ip_source_group` | Create a new IP source group | Write |
| `zia_update_ip_source_group` | Update an existing IP source group | Write |
| `zia_delete_ip_source_group` | Delete an IP source group | Write |
| `zia_list_ip_destination_groups` | List IP destination groups | Read-only |
| `zia_get_ip_destination_group` | Get a specific IP destination group | Read-only |
| `zia_create_ip_destination_group` | Create a new IP destination group | Write |
| `zia_update_ip_destination_group` | Update an existing IP destination group | Write |
| `zia_delete_ip_destination_group` | Delete an IP destination group | Write |
| `zia_list_network_app_groups` | List network application groups | Read-only |
| `zia_get_network_app_group` | Get a specific network app group | Read-only |
| `zia_create_network_app_group` | Create a new network app group | Write |
| `zia_update_network_app_group` | Update an existing network app group | Write |
| `zia_delete_network_app_group` | Delete a network app group | Write |
| `zia_list_user_groups` | List user groups | Read-only |
| `zia_get_user_group` | Get a specific user group | Read-only |
| `zia_list_user_departments` | List user departments | Read-only |
| `zia_get_user_department` | Get a specific user department | Read-only |
| `zia_list_users` | List users | Read-only |
| `zia_get_user` | Get a specific user | Read-only |

#### Labels & Utilities

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_rule_labels` | List rule labels | Read-only |
| `zia_get_rule_label` | Get a specific rule label | Read-only |
| `zia_create_rule_label` | Create a new rule label | Write |
| `zia_update_rule_label` | Update an existing rule label | Write |
| `zia_delete_rule_label` | Delete a rule label | Write |
| `zia_geo_search` | Perform geographical lookup | Read-only |
| `zia_get_sandbox_report` | Get sandbox report for a hash | Read-only |
| `zia_get_sandbox_quota` | Get sandbox quota information | Read-only |

#### DLP Management

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_dlp_dictionaries` | List DLP dictionaries | Read-only |
| `zia_get_dlp_dictionary` | Get a specific DLP dictionary | Read-only |
| `zia_list_dlp_engines` | List DLP engines | Read-only |
| `zia_get_dlp_engine` | Get a specific DLP engine | Read-only |

### ZPA Features

ZPA provides both **read-only** and **write** tools. Write operations require `--enable-write-tools` flag:

#### Application Segments

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_application_segments` | List application segments | Read-only |
| `zpa_get_application_segment` | Get a specific application segment | Read-only |
| `zpa_create_application_segment` | Create a new application segment | Write |
| `zpa_update_application_segment` | Update an existing application segment | Write |
| `zpa_delete_application_segment` | Delete an application segment | Write |
| `zpa_list_app_segments_by_type` | List application segments by type | Read-only |

#### App Connector Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_app_connector_groups` | List app connector groups | Read-only |
| `zpa_get_app_connector_group` | Get a specific app connector group | Read-only |
| `zpa_create_app_connector_group` | Create a new app connector group | Write |
| `zpa_update_app_connector_group` | Update an existing app connector group | Write |
| `zpa_delete_app_connector_group` | Delete an app connector group | Write |

#### Server Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_server_groups` | List server groups | Read-only |
| `zpa_get_server_group` | Get a specific server group | Read-only |
| `zpa_create_server_group` | Create a new server group | Write |
| `zpa_update_server_group` | Update an existing server group | Write |
| `zpa_delete_server_group` | Delete a server group | Write |

#### Service Edge Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_service_edge_groups` | List service edge groups | Read-only |
| `zpa_get_service_edge_group` | Get a specific service edge group | Read-only |
| `zpa_create_service_edge_group` | Create a new service edge group | Write |
| `zpa_update_service_edge_group` | Update an existing service edge group | Write |
| `zpa_delete_service_edge_group` | Delete a service edge group | Write |

#### Segment Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_segment_groups` | List segment groups | Read-only |
| `zpa_get_segment_group` | Get a specific segment group | Read-only |
| `zpa_create_segment_group` | Create a new segment group | Write |
| `zpa_update_segment_group` | Update an existing segment group | Write |
| `zpa_delete_segment_group` | Delete a segment group | Write |

#### Application Servers

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_application_servers` | List application servers | Read-only |
| `zpa_get_application_server` | Get a specific application server | Read-only |
| `zpa_create_application_server` | Create a new application server | Write |
| `zpa_update_application_server` | Update an existing application server | Write |
| `zpa_delete_application_server` | Delete an application server | Write |

#### Access Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_access_policy_rules` | List access policy rules | Read-only |
| `zpa_get_access_policy_rule` | Get a specific access policy rule | Read-only |
| `zpa_create_access_policy_rule` | Create a new access policy rule | Write |
| `zpa_update_access_policy_rule` | Update an existing access policy rule | Write |
| `zpa_delete_access_policy_rule` | Delete an access policy rule | Write |
| `zpa_reorder_access_policy_rule` | Reorder access policy rules | Write |

#### Forwarding Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_forwarding_policy_rules` | List forwarding policy rules | Read-only |
| `zpa_get_forwarding_policy_rule` | Get a specific forwarding policy rule | Read-only |
| `zpa_create_forwarding_policy_rule` | Create a new forwarding policy rule | Write |
| `zpa_update_forwarding_policy_rule` | Update an existing forwarding policy rule | Write |
| `zpa_delete_forwarding_policy_rule` | Delete a forwarding policy rule | Write |

#### Timeout Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_timeout_policy_rules` | List timeout policy rules | Read-only |
| `zpa_get_timeout_policy_rule` | Get a specific timeout policy rule | Read-only |
| `zpa_create_timeout_policy_rule` | Create a new timeout policy rule | Write |
| `zpa_update_timeout_policy_rule` | Update an existing timeout policy rule | Write |
| `zpa_delete_timeout_policy_rule` | Delete a timeout policy rule | Write |

#### Isolation Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_isolation_policy_rules` | List isolation policy rules | Read-only |
| `zpa_get_isolation_policy_rule` | Get a specific isolation policy rule | Read-only |
| `zpa_create_isolation_policy_rule` | Create a new isolation policy rule | Write |
| `zpa_update_isolation_policy_rule` | Update an existing isolation policy rule | Write |
| `zpa_delete_isolation_policy_rule` | Delete an isolation policy rule | Write |

#### App Protection Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_app_protection_rules` | List app protection rules | Read-only |
| `zpa_get_app_protection_rule` | Get a specific app protection rule | Read-only |
| `zpa_create_app_protection_rule` | Create a new app protection rule | Write |
| `zpa_update_app_protection_rule` | Update an existing app protection rule | Write |
| `zpa_delete_app_protection_rule` | Delete an app protection rule | Write |

#### Provisioning Keys

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_provisioning_keys` | List provisioning keys | Read-only |
| `zpa_get_provisioning_key` | Get a specific provisioning key | Read-only |
| `zpa_create_provisioning_key` | Create a new provisioning key | Write |
| `zpa_update_provisioning_key` | Update an existing provisioning key | Write |
| `zpa_delete_provisioning_key` | Delete a provisioning key | Write |

#### PRA Credentials

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_pra_credentials` | List PRA credentials | Read-only |
| `zpa_get_pra_credential` | Get a specific PRA credential | Read-only |
| `zpa_create_pra_credential` | Create a new PRA credential | Write |
| `zpa_update_pra_credential` | Update an existing PRA credential | Write |
| `zpa_delete_pra_credential` | Delete a PRA credential | Write |

#### PRA Portals

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_pra_portals` | List PRA portals | Read-only |
| `zpa_get_pra_portal` | Get a specific PRA portal | Read-only |
| `zpa_create_pra_portal` | Create a new PRA portal | Write |
| `zpa_update_pra_portal` | Update an existing PRA portal | Write |
| `zpa_delete_pra_portal` | Delete a PRA portal | Write |

#### SCIM Attributes

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_scim_attributes` | List SCIM attributes | Read-only |
| `zpa_get_scim_attribute_values` | Get SCIM attribute values | Read-only |
| `zpa_get_scim_attribute_by_idp` | Get SCIM attributes by IdP | Read-only |

#### Browser Access Certificates

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_ba_certificates` | List browser access certificates | Read-only |
| `zpa_get_ba_certificate` | Get a specific BA certificate | Read-only |
| `zpa_create_ba_certificate` | Create a new BA certificate | Write |
| `zpa_delete_ba_certificate` | Delete a BA certificate | Write |

#### Read-Only Resources

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_app_protection_profiles` | List app protection profiles | Read-only |
| `zpa_get_app_protection_profile` | Get a specific app protection profile | Read-only |
| `zpa_list_enrollment_certificates` | List enrollment certificates | Read-only |
| `zpa_get_enrollment_certificate` | Get a specific enrollment certificate | Read-only |
| `zpa_list_isolation_profiles` | List isolation profiles | Read-only |
| `zpa_get_isolation_profile` | Get a specific isolation profile | Read-only |
| `zpa_list_posture_profiles` | List posture profiles | Read-only |
| `zpa_get_posture_profile` | Get a specific posture profile | Read-only |
| `zpa_list_saml_attributes` | List SAML attributes | Read-only |
| `zpa_get_saml_attribute_values` | Get SAML attribute values | Read-only |
| `zpa_list_scim_groups` | List SCIM groups | Read-only |
| `zpa_get_scim_group_by_name` | Get SCIM group by name | Read-only |
| `zpa_list_trusted_networks` | List trusted networks | Read-only |
| `zpa_get_trusted_network` | Get a specific trusted network | Read-only |

### ZTW Features

ZTW provides both **read-only** and **write** tools. Write operations require `--enable-write-tools` flag:

#### IP Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_ip_groups` | List ZTW IP groups | Read-only |
| `ztw_get_ip_group` | Get a specific IP group | Read-only |
| `ztw_list_ip_groups_lite` | List IP groups (lite) | Read-only |
| `ztw_create_ip_group` | Create a new IP group | Write |
| `ztw_update_ip_group` | Update an existing IP group | Write |
| `ztw_delete_ip_group` | Delete an IP group | Write |

#### IP Source Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_ip_source_groups` | List IP source groups | Read-only |
| `ztw_get_ip_source_group` | Get a specific IP source group | Read-only |
| `ztw_create_ip_source_group` | Create a new IP source group | Write |
| `ztw_update_ip_source_group` | Update an existing IP source group | Write |
| `ztw_delete_ip_source_group` | Delete an IP source group | Write |

#### IP Destination Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_ip_destination_groups` | List IP destination groups | Read-only |
| `ztw_get_ip_destination_group` | Get a specific IP destination group | Read-only |
| `ztw_create_ip_destination_group` | Create a new IP destination group | Write |
| `ztw_update_ip_destination_group` | Update an existing IP destination group | Write |
| `ztw_delete_ip_destination_group` | Delete an IP destination group | Write |

#### Network Service Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_network_service_groups` | List network service groups | Read-only |
| `ztw_get_network_service_group` | Get a specific network service group | Read-only |
| `ztw_create_network_service_group` | Create a new network service group | Write |
| `ztw_update_network_service_group` | Update an existing network service group | Write |
| `ztw_delete_network_service_group` | Delete a network service group | Write |

#### Administration

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_roles` | List all admin roles | Read-only |
| `ztw_list_admins` | List all admin users | Read-only |
| `ztw_get_admin` | Get a specific admin user | Read-only |

## Installation & Setup

### Prerequisites

- Python 3.11 or higher
- [`uv`](https://docs.astral.sh/uv/) or pip
- Zscaler API credentials (see below)

### Environment Configuration

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Then edit `.env` with your Zscaler API credentials:

**Required Configuration (OneAPI):**

- `ZSCALER_CLIENT_ID`: Your Zscaler OAuth client ID
- `ZSCALER_CLIENT_SECRET`: Your Zscaler OAuth client secret
- `ZSCALER_CUSTOMER_ID`: Your Zscaler customer ID
- `ZSCALER_VANITY_DOMAIN`: Your Zscaler vanity domain

**Optional Configuration:**

- `ZSCALER_CLOUD`: (Optional) Zscaler cloud environment (e.g., `beta`) - Required when interacting with Beta Tenant ONLY.
- `ZSCALER_USE_LEGACY`: Enable legacy API mode (`true`/`false`, default: `false`)
- `ZSCALER_MCP_SERVICES`: Comma-separated list of services to enable (default: all services)
- `ZSCALER_MCP_TRANSPORT`: Transport method - `stdio`, `sse`, or `streamable-http` (default: `stdio`)
- `ZSCALER_MCP_DEBUG`: Enable debug logging - `true` or `false` (default: `false`)
- `ZSCALER_MCP_HOST`: Host for HTTP transports (default: `127.0.0.1`)
- `ZSCALER_MCP_PORT`: Port for HTTP transports (default: `8000`)

*Alternatively, you can set these as environment variables instead of using a `.env` file.*

> **Important**: Ensure your API client has the necessary permissions for the services you plan to use. You can always update permissions later in the Zscaler console.

### Installation

#### Install with VS Code (Quick Setup)

[![VS Code Install](https://img.shields.io/badge/VS%20Code-Install-blue?logo=visual-studio-code&logoColor=white&style=for-the-badge)](https://vscode.dev/redirect?url=vscode:mcp/install?%7B%22name%22%3A%22zscaler-mcp-server%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zscaler-mcp%22%5D%2C%22env%22%3A%7B%22ZSCALER_CLIENT_ID%22%3A%22%3CYOUR_CLIENT_ID%3E%22%2C%22ZSCALER_CLIENT_SECRET%22%3A%22%3CYOUR_CLIENT_SECRET%3E%22%2C%22ZSCALER_CUSTOMER_ID%22%3A%22%3CYOUR_CUSTOMER_ID%3E%22%2C%22ZSCALER_VANITY_DOMAIN%22%3A%22%3CYOUR_VANITY_DOMAIN%3E%22%7D%7D)

> **Note**: This will open VS Code and prompt you to configure the MCP server. You'll need to replace the placeholder values (`<YOUR_CLIENT_ID>`, etc.) with your actual Zscaler credentials.

#### Install using uv (recommended)

```bash
uv tool install zscaler-mcp
```

#### Install from source using uv (development)

```bash
uv pip install -e .
```

#### Install from source using pip

```bash
pip install -e .
```

#### Install using make (convenience)

```bash
make install-dev
```

> [!TIP]
> If `zscaler-mcp-server` isn't found, update your shell PATH.

For installation via code editors/assistants, see the [Using the MCP Server with Agents](#using-the-mcp-server-with-agents) section below.

## Usage

> [!NOTE]
> **Default Security Mode**: All examples below run in **read-only mode** by default (only `list_*` and `get_*` operations). To enable write operations (`create_*`, `update_*`, `delete_*`), add the `--enable-write-tools` flag to any command, or set `ZSCALER_MCP_WRITE_ENABLED=true` in your environment.

### Command Line

Run the server with default settings (stdio transport, read-only mode):

```bash
zscaler-mcp
```

Run the server with write operations enabled:

```bash
zscaler-mcp --enable-write-tools
```

Run with SSE transport:

```bash
zscaler-mcp --transport sse
```

Run with streamable-http transport:

```bash
zscaler-mcp --transport streamable-http
```

Run with streamable-http transport on custom port:

```bash
zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8080
```

### Service Configuration

The Zscaler Integrations MCP Server supports multiple ways to specify which services to enable:

#### 1. Command Line Arguments (highest priority)

Specify services using comma-separated lists:

```bash
# Enable specific services
zscaler-mcp --services zia,zpa,zdx

# Enable only one service
zscaler-mcp --services zia
```

#### 2. Environment Variable (fallback)

Set the `ZSCALER_MCP_SERVICES` environment variable:

```bash
# Export environment variable
export ZSCALER_MCP_SERVICES=zia,zpa,zdx
zscaler-mcp

# Or set inline
ZSCALER_MCP_SERVICES=zia,zpa,zdx zscaler-mcp
```

#### 3. Default Behavior (all services)

If no services are specified via command line or environment variable, all available services are enabled by default.

**Service Priority Order:**

1. Command line `--services` argument (overrides all)
2. `ZSCALER_MCP_SERVICES` environment variable (fallback)
3. All services (default when none specified)

### Additional Command Line Options

```bash
# Enable write operations (create, update, delete)
zscaler-mcp --enable-write-tools

# Enable debug logging
zscaler-mcp --debug

# Combine multiple options
zscaler-mcp --services zia,zpa --enable-write-tools --debug
```

For all available options:

```bash
zscaler-mcp --help
```

Available command-line flags:

- `--transport`: Transport protocol (`stdio`, `sse`, `streamable-http`)
- `--services`: Comma-separated list of services to enable
- `--tools`: Comma-separated list of specific tools to enable
- `--enable-write-tools`: Enable write operations (disabled by default for safety)
- `--debug`: Enable debug logging
- `--host`: Host for HTTP transports (default: `127.0.0.1`)
- `--port`: Port for HTTP transports (default: `8000`)

### Supported Agents

- [Claude](https://claude.ai/)
- [Cursor](https://cursor.so/)
- [VS Code](https://code.visualstudio.com/download) or [VS Code Insiders](https://code.visualstudio.com/insiders)

## Zscaler API Credentials & Authentication

The Zscaler Integrations MCP Server supports two authentication methods: OneAPI (recommended) and Legacy API. Choose the method that best fits your setup.

### Zscaler OneAPI Authentication

Before using the Zscaler Integrations MCP Server, you need to create API credentials in your Zidentity console. The Zscaler Integrations MCP Server supports Zscaler's OneAPI authentication via OAuth2.0 as the default and preferred method.

- [OneAPI](https://help.zscaler.com/oneapi/understanding-oneapi): If you are using the OneAPI entrypoint you must have a API Client created in the [Zidentity platform](https://help.zscaler.com/zidentity/about-api-clients)

Create a `.env` file in your project root with the following:

```env
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_CUSTOMER_ID=your_customer_id
ZSCALER_VANITY_DOMAIN=your_vanity_domain
ZSCALER_CLOUD=beta
```

⚠️ Do not commit `.env` to source control. Add it to your `.gitignore`.

You can provide credentials via the `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_VANITY_DOMAIN`, `ZSCALER_CLOUD` environment variables, representing your Zidentity OneAPI credentials `clientId`, `clientSecret`, `vanityDomain` and `cloud` respectively.

| Argument     | Description | Environment variable |
|--------------|-------------|-------------------|
| `clientId`       | *(String)* Zscaler API Client ID, used with `clientSecret` or `PrivateKey` OAuth auth mode.| `ZSCALER_CLIENT_ID` |
| `clientSecret`       | *(String)* A string that contains the password for the API admin.| `ZSCALER_CLIENT_SECRET` |
| `vanityDomain`       | *(String)* Refers to the domain name used by your organization i.e `acme` | `ZSCALER_VANITY_DOMAIN` |
| `cloud`       | *(String)* The Zidentity cloud to authenticate to i.e `beta`| `ZSCALER_CLOUD` |
| `use_legacy`       | *(Boolean)* Whether to use legacy API clients instead of OneAPI. Can be set to `true` or `false`.| `ZSCALER_USE_LEGACY` |

### Using Legacy Mode with Environment Variable

To enable legacy API mode for all tools, set the `ZSCALER_USE_LEGACY` environment variable:

```env
# Enable legacy mode for all tools
ZSCALER_USE_LEGACY=true

# Legacy ZPA credentials
ZPA_CLIENT_ID=your_zpa_client_id
ZPA_CLIENT_SECRET=your_zpa_client_secret
ZPA_CUSTOMER_ID=your_zpa_customer_id
ZPA_CLOUD=BETA

# Legacy ZIA credentials
ZIA_USERNAME=your_zia_username
ZIA_PASSWORD=your_zia_password
ZIA_API_KEY=your_zia_api_key
ZIA_CLOUD=beta

# Legacy ZCC credentials
ZCC_CLIENT_ID=your_zcc_client_id
ZCC_CLIENT_SECRET=your_zcc_client_secret
ZCC_CLOUD=beta

# Legacy ZDX credentials
ZDX_CLIENT_ID=your_zdx_client_id
ZDX_CLIENT_SECRET=your_zdx_client_secret
ZDX_CLOUD=beta
```

When `ZSCALER_USE_LEGACY=true` is set, all tools will use legacy API clients by default. You can still override this per tool call by explicitly setting `use_legacy: false` in the tool parameters.

**Note**: When using legacy mode, the MCP server will initialize without creating a client during startup. Clients are created on-demand when individual tools are called, which allows the server to work with different legacy services (ZPA, ZIA, ZDX) without requiring a specific service to be specified during initialization.

**Important**: Legacy credentials are only loaded when `ZSCALER_USE_LEGACY=true` is set. In OneAPI mode, legacy credentials are ignored to prevent conflicts.

## Zscaler Legacy API Login

### ZIA Legacy Authentication

You can provide credentials via the `ZIA_USERNAME`, `ZIA_PASSWORD`, `ZIA_API_KEY`, `ZIA_CLOUD` environment variables, representing your ZIA `username`, `password`, `api_key` and `cloud` respectively.

```env
ZIA_USERNAME=username
ZIA_PASSWORD=password
ZIA_API_KEY=api_key
ZIA_CLOUD=cloud
```

⚠️ Do not commit `.env` to source control. Add it to your `.gitignore`.

| Argument     | Description | Environment variable |
|--------------|-------------|-------------------|
| `username`       | *(String)* A string that contains the email ID of the API admin.| `ZIA_USERNAME` |
| `password`       | *(String)* A string that contains the password for the API admin.| `ZIA_PASSWORD` |
| `api_key`       | *(String)* A string that contains the obfuscated API key (i.e., the return value of the obfuscateApiKey() method).| `ZIA_API_KEY` |
| `cloud`       | *(String)* The cloud name to authenticate to i.e `zscalertwo`| `ZIA_CLOUD` |

The following cloud environments are supported:

- `zscaler`
- `zscalerone`
- `zscalertwo`
- `zscalerthree`
- `zscloud`
- `zscalerbeta`
- `zscalergov`
- `zscalerten`
- `zspreview`

### ZPA Legacy Authentication

You can provide credentials via the `ZPA_CLIENT_ID`, `ZPA_CLIENT_SECRET`, `ZPA_CUSTOMER_ID`, `ZPA_CLOUD` environment variables, representing your ZPA `clientId`, `clientSecret`, `customerId` and `cloud` of your ZPA account, respectively.

```env
ZPA_CLIENT_ID=client_id
ZPA_CLIENT_SECRET=client_secret
ZPA_CUSTOMER_ID=customer_id
ZPA_CLOUD=cloud
```

⚠️ Do not commit `.env` to source control. Add it to your `.gitignore`.

| Argument     | Description | Environment variable |
|--------------|-------------|-------------------|
| `clientId`       | *(String)* The ZPA API client ID generated from the ZPA console.| `ZPA_CLIENT_ID` |
| `clientSecret`       | *(String)* The ZPA API client secret generated from the ZPA console.| `ZPA_CLIENT_SECRET` |
| `customerId`       | *(String)* The ZPA tenant ID found in the Administration > Company menu in the ZPA console.| `ZPA_CUSTOMER_ID` |
| `microtenantId`       | *(String)* The ZPA microtenant ID found in the respective microtenant instance under Configuration & Control > Public API > API Keys menu in the ZPA console.| `ZPA_MICROTENANT_ID` |
| `cloud`       | *(String)* The Zscaler cloud for your tenancy.| `ZPA_CLOUD` |

### ZCC Legacy Authentication

You can provide credentials via the `ZCC_CLIENT_ID`, `ZCC_CLIENT_SECRET`, `ZCC_CLOUD` environment variables, representing your ZIA `api_key`, `secret_key`, and `cloud` respectively.

~> **NOTE** `ZCC_CLOUD` environment variable is required, and is used to identify the correct API gateway where the API requests should be forwarded to.

```env
ZCC_CLIENT_ID=api_key
ZCC_CLIENT_SECRET=secret_key
ZCC_CLOUD=cloud
```

⚠️ Do not commit `.env` to source control. Add it to your `.gitignore`.

| Argument     | Description | Environment variable |
|--------------|-------------|-------------------|
| `api_key`       | *(String)* A string that contains the apiKey for the Mobile Portal.| `ZCC_CLIENT_ID` |
| `secret_key`       | *(String)* A string that contains the secret key for the Mobile Portal.| `ZCC_CLIENT_SECRET` |
| `cloud`       | *(String)* The cloud name to authenticate to i.e `zscalertwo`| `ZCC_CLOUD` |

The following cloud environments are supported:

- `zscaler`
- `zscalerone`
- `zscalertwo`
- `zscalerthree`
- `zscloud`
- `zscalerbeta`
- `zscalergov`
- `zscalerten`
- `zspreview`

### ZDX Legacy Authentication

You can provide credentials via the `ZDX_CLIENT_ID`, `ZDX_CLIENT_SECRET` environment variables, representing your ZDX `key_id`, `key_secret` of your ZDX account, respectively.

```env
ZDX_CLIENT_ID=api_key
ZDX_CLIENT_SECRET=secret_key
ZDX_CLOUD=cloud
```

⚠️ Do not commit `.env` to source control. Add it to your `.gitignore`.

| Argument     | Description | Environment variable |
|--------------|-------------|-------------------|
| `key_id`       | *(String)* A string that contains the key_id for the ZDX Portal.| `ZDX_CLIENT_ID` |
| `key_secret`       | *(String)* A string that contains the key_secret key for the ZDX Portal.| `ZDX_CLIENT_SECRET` |
| `cloud`            | *(String)* The cloud name prefix that identifies the correct API endpoint.| `ZDX_CLOUD` |

### Internal Environment Variables

The Zscaler Integrations MCP Server uses the following internal environment variables for configuration:

#### MCP Server Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ZSCALER_MCP_TRANSPORT` | `stdio` | Transport protocol to use (`stdio`, `sse`, or `streamable-http`) |
| `ZSCALER_MCP_SERVICES` | `""` | Comma-separated list of services to enable (empty = all services). Supported values: `zcc`, `zdx`, `zia`, `zidentity`, `zpa` |
| `ZSCALER_MCP_TOOLS` | `""` | Comma-separated list of specific tools to enable (empty = all tools) |
| `ZSCALER_MCP_WRITE_ENABLED` | `false` | Enable write operations (`true`/`false`). When `false`, only read-only tools are available. Set to `true` or use `--enable-write-tools` flag to unlock write mode. |
| `ZSCALER_MCP_WRITE_TOOLS` | `""` | **MANDATORY** comma-separated allowlist of write tools (supports wildcards like `zpa_create_*`). Requires `ZSCALER_MCP_WRITE_ENABLED=true`. If empty when write mode enabled, 0 write tools registered. |
| `ZSCALER_MCP_DEBUG` | `false` | Enable debug logging (`true`/`false`) |
| `ZSCALER_MCP_HOST` | `127.0.0.1` | Host to bind to for HTTP transports |
| `ZSCALER_MCP_PORT` | `8000` | Port to listen on for HTTP transports |
| `ZSCALER_MCP_USER_AGENT_COMMENT` | `""` | Additional information to include in User-Agent comment section |

#### User-Agent Header

The MCP server automatically includes a custom User-Agent header in all API requests to Zscaler services. The format is:

```sh
User-Agent: zscaler-mcp-server/<version> python/<python_version> <os>/<architecture>
```

**Example:**

```sh
User-Agent: zscaler-mcp-server/0.3.1 python/3.11.8 darwin/arm64
```

**With Custom Comment:**

You can append additional information (such as the AI agent details) using the `ZSCALER_MCP_USER_AGENT_COMMENT` environment variable or the `--user-agent-comment` CLI flag:

```bash
# Via environment variable
export ZSCALER_MCP_USER_AGENT_COMMENT="Claude Desktop 1.2024.10.23"

# Via CLI flag
zscaler-mcp --user-agent-comment "Claude Desktop 1.2024.10.23"
```

This results in:

```sh
User-Agent: zscaler-mcp-server/0.3.1 python/3.11.8 darwin/arm64 Claude Desktop 1.2024.10.23
```

The User-Agent helps Zscaler identify API traffic from the MCP server and can be useful for support, analytics, and debugging purposes.

#### OneAPI Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZSCALER_CLIENT_ID` | Yes | Zscaler OAuth client ID |
| `ZSCALER_CLIENT_SECRET` | Yes | Zscaler OAuth client secret |
| `ZSCALER_CUSTOMER_ID` | Yes | Zscaler customer ID |
| `ZSCALER_VANITY_DOMAIN` | Yes | Zscaler vanity domain |
| `ZSCALER_CLOUD` | No | Zscaler cloud environment (e.g., `beta`, `zscalertwo`) |
| `ZSCALER_PRIVATE_KEY` | No | OAuth private key for JWT-based authentication |
| `ZSCALER_USE_LEGACY` | `false` | Enable legacy API mode (`true`/`false`) |

#### Legacy Authentication (when `ZSCALER_USE_LEGACY=true`)

**ZPA Legacy:**

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZPA_CLIENT_ID` | Yes | ZPA API client ID |
| `ZPA_CLIENT_SECRET` | Yes | ZPA API client secret |
| `ZPA_CUSTOMER_ID` | Yes | ZPA tenant ID |
| `ZPA_CLOUD` | Yes | Zscaler cloud for ZPA tenancy |

**ZIA Legacy:**

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZIA_USERNAME` | Yes | ZIA API admin email |
| `ZIA_PASSWORD` | Yes | ZIA API admin password |
| `ZIA_API_KEY` | Yes | ZIA obfuscated API key |
| `ZIA_CLOUD` | Yes | Zscaler cloud for ZIA |

**ZCC Legacy:**

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZCC_CLIENT_ID` | Yes | ZCC API key |
| `ZCC_CLIENT_SECRET` | Yes | ZCC secret key |
| `ZCC_CLOUD` | Yes | Zscaler cloud for ZCC |

**ZDX Legacy:**

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZDX_CLIENT_ID` | Yes | ZDX key ID |
| `ZDX_CLIENT_SECRET` | Yes | ZDX secret key |
| `ZDX_CLOUD` | Yes | Zscaler cloud for ZDX |

### As a Library

You can use the Zscaler Integrations MCP Server as a Python library in your own applications:

```python
from zscaler_mcp.server import ZscalerMCPServer

# Create server with read-only mode (default - safe)
server = ZscalerMCPServer(
    debug=True,  # Optional, enable debug logging
    enabled_services={"zia", "zpa", "zdx"},  # Optional, defaults to all services
    enabled_tools={"zia_list_rule_labels", "zpa_list_application_segments"},  # Optional, defaults to all tools
    user_agent_comment="My Custom App",  # Optional, additional User-Agent info
    enable_write_tools=False  # Optional, defaults to False (read-only mode)
)

# Run with stdio transport (default)
server.run()

# Or run with SSE transport
server.run("sse")

# Or run with streamable-http transport
server.run("streamable-http")

# Or run with streamable-http transport on custom host/port
server.run("streamable-http", host="0.0.0.0", port=8080)
```

**Example with write operations enabled:**

```python
from zscaler_mcp.server import ZscalerMCPServer

# Create server with write operations enabled
server = ZscalerMCPServer(
    debug=True,
    enabled_services={"zia", "zpa"},
    enable_write_tools=True  # Enable create/update/delete operations
)

# Run the server
server.run("stdio")
```

**Available Services**: `zcc`, `zdx`, `zia`, `zidentity`, `zpa`

**Example with Environment Variables**:

```python
from zscaler_mcp.server import ZscalerMCPServer
import os

# Load from environment variables
server = ZscalerMCPServer(
    debug=True,
    enabled_services={"zia", "zpa"}
)

# Run the server
server.run("stdio")
```

### Running Examples

```bash
# Run with stdio transport
python examples/basic_usage.py

# Run with SSE transport
python examples/sse_usage.py

# Run with streamable-http transport
python examples/streamable_http_usage.py
```

## Container Usage

The Zscaler Integrations MCP Server is available as a pre-built container image for easy deployment:

### Using Pre-built Image (Recommended)

```bash
# Pull the latest pre-built image
docker pull quay.io/zscaler/zscaler-mcp-server:latest

# Run with .env file (recommended)
docker run --rm --env-file /path/to/.env quay.io/zscaler/zscaler-mcp-server:latest

# Run with .env file and SSE transport
docker run --rm -p 8000:8000 --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --transport sse --host 0.0.0.0

# Run with .env file and streamable-http transport
docker run --rm -p 8000:8000 --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0

# Run with .env file and custom port
docker run --rm -p 8080:8080 --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0 --port 8080

# Run with .env file and specific services
docker run --rm --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --services zia,zpa,zdx

# Use a specific version instead of latest
docker run --rm --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:1.2.3

# Alternative: Individual environment variables
docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
  -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain \
  quay.io/zscaler/zscaler-mcp-server:latest
```

### Building Locally (Development)

For development or customization purposes, you can build the image locally:

```bash
# Build the Docker image
docker build -t zscaler-mcp-server .

# Run the locally built image
docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
  -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain zscaler-mcp-server
```

**Note**: When using HTTP transports in Docker, always set `--host 0.0.0.0` to allow external connections to the container.

## Editor/Assistant Integration

You can integrate the Zscaler Integrations MCP server with your editor or AI assistant. Here are configuration examples for popular MCP clients:

### Using `uvx` (recommended)

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/path/to/.env", "zscaler-mcp-server"]
    }
  }
}
```

### With Service Selection

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": [
        "--env-file", "/path/to/.env",
        "zscaler-mcp-server",
        "--services", "zia,zpa,zdx"
      ]
    }
  }
}
```

### Using Individual Environment Variables

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["zscaler-mcp-server"],
      "env": {
        "ZSCALER_CLIENT_ID": "your-client-id",
        "ZSCALER_CLIENT_SECRET": "your-client-secret",
        "ZSCALER_CUSTOMER_ID": "your-customer-id",
        "ZSCALER_VANITY_DOMAIN": "your-vanity-domain"
      }
    }
  }
}
```

### Docker Version

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/full/path/to/.env",
        "quay.io/zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

## Additional Deployment Options

### Amazon Bedrock AgentCore

To deploy the MCP Server as a tool in Amazon Bedrock AgentCore, please refer to the [following document](./docs/deployment/amazon_bedrock_agentcore.md).

## Using the MCP Server with Agents

Once your server is running (via Docker or source), you can access its tools through AI-integrated editors or platforms.

> [!IMPORTANT]
> **Read-Only Mode**: By default, the server exposes only **read-only tools** (`list_*`, `get_*`). If you need write capabilities (`create_*`, `update_*`, `delete_*`), you must explicitly enable write tools in your MCP configuration by adding `--enable-write-tools` to the command or setting `ZSCALER_MCP_WRITE_ENABLED=true`. See [Security & Permissions](#-security--permissions) for details.

### 🧠 Claude Desktop

#### Option 1: Using Docker (Recommended)

##### Step 1: Pull the Docker image

```bash
docker pull quay.io/zscaler/zscaler-mcp-server:latest
```

##### Step 2: Create your credentials file

Create a file named `.env` with your Zscaler credentials:

```bash
# Example: ~/zscaler-mcp/.env
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_CUSTOMER_ID=your_customer_id
ZSCALER_VANITY_DOMAIN=your_vanity_domain
ZSCALER_CLOUD=production

# Optional: Enable write operations (use with caution!)
# ZSCALER_MCP_WRITE_ENABLED=true
# ZSCALER_MCP_WRITE_TOOLS=zpa_create_*,zpa_delete_*
```

##### Step 3: Configure Claude Desktop

1. Open Claude Desktop
2. Go to: **Settings → Developer → Edit Config**
3. This opens `claude_desktop_config.json`
4. Add the following configuration:

```json
{
  "mcpServers": {
    "zscaler-mcp-docker": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/absolute/path/to/your/.env",
        "quay.io/zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

**Important**: Replace `/absolute/path/to/your/.env` with the full path to your `.env` file.

Example paths:

- macOS/Linux: `/Users/yourname/zscaler-mcp/.env`
- Windows: `C:\\Users\\yourname\\zscaler-mcp\\.env`

##### Step 4: Restart Claude Desktop

Completely quit and reopen Claude Desktop for changes to take effect.

##### Step 5: Test the connection

Ask Claude: `"List my ZPA application segments"` or `"Check Zscaler connectivity"`

#### Option 2: Using Python (Development)

If you have Python installed and want to run from source:

1. Install the package:

```bash
pip install zscaler-mcp
```

1. Configure Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "zscaler-mcp": {
      "command": "zscaler-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "ZSCALER_CLIENT_ID": "your_client_id",
        "ZSCALER_CLIENT_SECRET": "your_client_secret",
        "ZSCALER_CUSTOMER_ID": "your_customer_id",
        "ZSCALER_VANITY_DOMAIN": "your_vanity_domain",
        "ZSCALER_CLOUD": "production"
      }
    }
  }
}
```

1. Restart Claude Desktop

#### Troubleshooting Claude Configuration

**Server not appearing:**

- Check Claude Desktop logs: Settings → Developer → Open Logs Folder
- Verify Docker is running: `docker ps`
- Test server manually: `docker run -i --rm --env-file .env quay.io/zscaler/zscaler-mcp-server:latest`

**Connection errors:**

- Verify `.env` file path is absolute (not relative)
- Check credentials are correct and not expired
- Ensure Docker has permission to read the `.env` file

**No tools available:**

- Default: Only read-only tools (`list_*`, `get_*`) are available
- For write tools: Add `ZSCALER_MCP_WRITE_ENABLED=true` and `ZSCALER_MCP_WRITE_TOOLS=...` to `.env`

### 💻 Cursor

1. Open Cursor, then settings
2. In Cursor Settings, select "Tools & Integrations"
3. In the MCP Tools section, turn on `zscaler-mcp-server`
4. Select `View` and `Command Palette` and `Chat: Open Chat Agent`
5. In chat, switch to [Agent Mode](https://docs.cursor.com/chat/agent).
6. Try prompts like "List ZPA Segment Groups" or "List ZIA Rule Labels"
7. Click "Submit"

### Visual Studio Code + GitHub Copilot

Install

After installation, select GitHub Copilot Agent Mode and refresh the tools list. Learn more about Agent Mode in the [VS Code Documentation](https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode).

1. Open VS Code and launch GitHub Copilot
2. Switch to Agent Mode (via the gear menu)
3. Start the MCP Server
4. Refresh the tools list
5. Try a prompt like: `Create a ZPA segment group named "DevServices"`

📚 Learn more about Agent Mode in the [VS Code Copilot documentation](https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode)

#### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running
- Zscaler API credentials

## Troubleshooting

See the [Troubleshooting guide](./docs/TROUBLESHOOTING.md) for help with common issues and logging.

## Contributing

### Getting Started for Contributors

1. Clone the repository:

   ```bash
   git clone https://github.com/zscaler/zscaler-mcp-server.git
   cd zscaler-mcp-server
   ```

2. Install in development mode:

   ```bash
   # Create .venv and install dependencies
   uv sync --all-extras

   # Activate the venv
   source .venv/bin/activate
   ```

> [!IMPORTANT]
> This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated releases and semantic versioning. Please follow the commit message format outlined in our [Contributing Guide](docs/CONTRIBUTING.md) when submitting changes.

### Running Tests

```bash
# Run all tests
pytest

# Run end-to-end tests
pytest --run-e2e tests/e2e/

# Run end-to-end tests with verbose output (note: -s is required to see output)
pytest --run-e2e -v -s tests/e2e/
```

## Privacy Policy

This MCP server connects to the Zscaler API to manage and retrieve information about your Zscaler resources. When using this server, data is transmitted between your local environment and Zscaler's cloud services.

**Data Handling:**

- This MCP server acts as a client to the Zscaler API and does not store or log any data locally beyond what is necessary for operation
- All API communications are made directly to Zscaler's cloud infrastructure
- Authentication credentials (Client ID, Client Secret, Customer ID) are used only for API authentication and are not transmitted to any third parties
- The server operates in read-only mode by default; write operations require explicit enablement via the `--enable-write-tools` flag

**User Responsibility:**

- Users are responsible for securing their Zscaler API credentials
- Users should review and understand which tools they enable and grant to AI agents
- Users should be aware that AI agents with access to this server can query and (if enabled) modify Zscaler resources within the scope of the provided credentials

For information about how Zscaler handles data and privacy, please refer to the [Zscaler Privacy Policy](https://www.zscaler.com/privacy/company-privacy-policy).

## License

Copyright (c) 2025 [Zscaler](https://github.com/zscaler)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
