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
  - [Quick Start: Choose Your Authentication Method](#quick-start-choose-your-authentication-method)
  - [OneAPI Authentication (Recommended)](#oneapi-authentication-recommended)
  - [Legacy API Authentication](#legacy-api-authentication)
  - [Authentication Troubleshooting](#authentication-troubleshooting)
  - [MCP Server Configuration](#mcp-server-configuration)
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

#### SSL Inspection Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_ssl_inspection_rules` | List SSL inspection rules | Read-only |
| `zia_get_ssl_inspection_rule` | Get a specific SSL inspection rule | Read-only |
| `zia_create_ssl_inspection_rule` | Create a new SSL inspection rule | Write |
| `zia_update_ssl_inspection_rule` | Update an existing SSL inspection rule | Write |
| `zia_delete_ssl_inspection_rule` | Delete an SSL inspection rule | Write |

#### Labels & Utilities

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_rule_labels` | List rule labels | Read-only |
| `zia_get_rule_label` | Get a specific rule label | Read-only |
| `zia_create_rule_label` | Create a new rule label | Write |
| `zia_update_rule_label` | Update an existing rule label | Write |
| `zia_delete_rule_label` | Delete a rule label | Write |
| `zia_geo_search` | Perform geographical lookup | Read-only |
| `zia_get_sandbox_quota` | Retrieve current sandbox quota information | Read-only |
| `zia_get_sandbox_behavioral_analysis` | Retrieve sandbox behavioral analysis hash list | Read-only |
| `zia_get_sandbox_file_hash_count` | Retrieve sandbox file hash usage counts | Read-only |
| `zia_get_sandbox_report` | Retrieve sandbox report for a specific hash | Read-only |

> **Note:** The legacy `zia_sandbox_info` tool is still available for backward compatibility, but new automations should call the more specific sandbox tools above for clearer intent matching.

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

#### Network Services

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_network_services` | List network services with optional filtering | Read-only |

#### Administration

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_roles` | List all admin roles | Read-only |
| `ztw_list_admins` | List all admin users | Read-only |
| `ztw_get_admin` | Get a specific admin user | Read-only |

#### Public Cloud Info

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_public_cloud_info` | List public cloud accounts with metadata | Read-only |
| `ztw_list_public_account_details` | List detailed public cloud account information | Read-only |

#### Discovery Service

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_get_discovery_settings` | Get workload discovery service settings | Read-only |

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

The Zscaler Integrations MCP Server supports two authentication methods: **OneAPI (recommended)** and **Legacy API**. You must choose **ONE** method - do not mix them.

> [!IMPORTANT]
> **⚠️ CRITICAL: Choose ONE Authentication Method**
>
> - **OneAPI**: Single credential set for ALL services (ZIA, ZPA, ZCC, ZDX)
> - **Legacy**: Separate credentials required for EACH service
> - **DO NOT** set both OneAPI and Legacy credentials simultaneously
> - **DO NOT** set `ZSCALER_USE_LEGACY=true` if using OneAPI

### Quick Start: Choose Your Authentication Method

#### Option A: OneAPI (Recommended - Single Credential Set)

- ✅ **One set of credentials** works for ALL services (ZIA, ZPA, ZCC, ZDX, ZTW)
- ✅ Modern OAuth2.0 authentication via Zidentity
- ✅ Easier to manage and maintain
- ✅ Default authentication method (no flag needed)
- **Use this if:** You have access to Zidentity console and want simplicity

#### Option B: Legacy Mode (Per-Service Credentials)

- ⚠️ **Separate credentials** required for each service you want to use
- ⚠️ Different authentication methods per service (OAuth for ZPA, API key for ZIA, etc.)
- ⚠️ Must set `ZSCALER_USE_LEGACY=true` environment variable
- **Use this if:** You don't have OneAPI access or need per-service credential management

#### Decision Tree

```text
Do you have access to Zidentity console?
├─ YES → Use OneAPI (Option A)
└─ NO  → Use Legacy Mode (Option B)
```

---

### OneAPI Authentication (Recommended)

OneAPI provides a single set of credentials that authenticate to all Zscaler services. This is the default and recommended method.

#### Prerequisites

Before using OneAPI, you need to:

1. Create an API Client in the [Zidentity platform](https://help.zscaler.com/zidentity/about-api-clients)
2. Obtain your credentials: `clientId`, `clientSecret`, `customerId`, and `vanityDomain`
3. Learn more: [Understanding OneAPI](https://help.zscaler.com/oneapi/understanding-oneapi)

#### Quick Setup

Create a `.env` file in your project root (or where you'll run the MCP server):

```env
# OneAPI Credentials (Required)
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_CUSTOMER_ID=your_customer_id
ZSCALER_VANITY_DOMAIN=your_vanity_domain

# Optional: Only required for Beta tenants
ZSCALER_CLOUD=beta
```

⚠️ **Security**: Do not commit `.env` to source control. Add it to your `.gitignore`.

#### OneAPI Environment Variables

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZSCALER_CLIENT_ID` | Yes | Zscaler OAuth client ID from Zidentity console |
| `ZSCALER_CLIENT_SECRET` | Yes | Zscaler OAuth client secret from Zidentity console |
| `ZSCALER_CUSTOMER_ID` | Yes | Zscaler customer ID |
| `ZSCALER_VANITY_DOMAIN` | Yes | Your organization's vanity domain (e.g., `acme`) |
| `ZSCALER_CLOUD` | No | Zscaler cloud environment (e.g., `beta`, `zscalertwo`). **Only required for Beta tenants** |
| `ZSCALER_PRIVATE_KEY` | No | OAuth private key for JWT-based authentication (alternative to client secret) |

#### Verification

After setting up your `.env` file, test the connection:

```bash
# Test with a simple command
zscaler-mcp
```

If authentication is successful, the server will start without errors. If you see authentication errors, verify:

- All required environment variables are set correctly
- Your API client has the necessary permissions in Zidentity
- Your credentials are valid and not expired

---

### Legacy API Authentication

Legacy mode requires separate credentials for each Zscaler service. This method is only needed if you don't have access to OneAPI.

> [!WARNING]
> **⚠️ IMPORTANT**: When using Legacy mode:
>
> - You **MUST** set `ZSCALER_USE_LEGACY=true` in your `.env` file
> - You **MUST** provide credentials for each service you want to use
> - OneAPI credentials are **ignored** when `ZSCALER_USE_LEGACY=true` is set
> - Clients are created on-demand when tools are called (not at startup)

#### Quick Setup

Create a `.env` file with the following structure:

```env
# Enable Legacy Mode (REQUIRED - set once at the top)
ZSCALER_USE_LEGACY=true

# ZPA Legacy Credentials (if using ZPA)
ZPA_CLIENT_ID=your_zpa_client_id
ZPA_CLIENT_SECRET=your_zpa_client_secret
ZPA_CUSTOMER_ID=your_zpa_customer_id
ZPA_CLOUD=BETA

# ZIA Legacy Credentials (if using ZIA)
ZIA_USERNAME=your_zia_username
ZIA_PASSWORD=your_zia_password
ZIA_API_KEY=your_zia_api_key
ZIA_CLOUD=zscalertwo

# ZCC Legacy Credentials (if using ZCC)
ZCC_CLIENT_ID=your_zcc_client_id
ZCC_CLIENT_SECRET=your_zcc_client_secret
ZCC_CLOUD=zscalertwo

# ZDX Legacy Credentials (if using ZDX)
ZDX_CLIENT_ID=your_zdx_client_id
ZDX_CLIENT_SECRET=your_zdx_client_secret
ZDX_CLOUD=zscalertwo
```

⚠️ **Security**: Do not commit `.env` to source control. Add it to your `.gitignore`.

#### Legacy Authentication by Service

##### ZPA Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZPA_CLIENT_ID` | Yes | ZPA API client ID from ZPA console |
| `ZPA_CLIENT_SECRET` | Yes | ZPA API client secret from ZPA console |
| `ZPA_CUSTOMER_ID` | Yes | ZPA tenant ID (found in Administration > Company menu) |
| `ZPA_CLOUD` | Yes | Zscaler cloud for ZPA tenancy (e.g., `BETA`, `zscalertwo`) |
| `ZPA_MICROTENANT_ID` | No | ZPA microtenant ID (if using microtenants) |

**Where to find ZPA credentials:**

- API Client ID/Secret: ZPA console > Configuration & Control > Public API > API Keys
- Customer ID: ZPA console > Administration > Company

##### ZIA Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZIA_USERNAME` | Yes | ZIA API admin email address |
| `ZIA_PASSWORD` | Yes | ZIA API admin password |
| `ZIA_API_KEY` | Yes | ZIA obfuscated API key (from obfuscateApiKey() method) |
| `ZIA_CLOUD` | Yes | Zscaler cloud name (see supported clouds below) |

**Supported ZIA Cloud Environments:**

- `zscaler`, `zscalerone`, `zscalertwo`, `zscalerthree`
- `zscloud`, `zscalerbeta`, `zscalergov`, `zscalerten`, `zspreview`

**Where to find ZIA credentials:**

- Username/Password: Your ZIA admin account
- API Key: ZIA Admin Portal > Administration > API Key Management

##### ZCC Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZCC_CLIENT_ID` | Yes | ZCC API key (Mobile Portal) |
| `ZCC_CLIENT_SECRET` | Yes | ZCC secret key (Mobile Portal) |
| `ZCC_CLOUD` | Yes | Zscaler cloud name (see supported clouds below) |

> **NOTE**: `ZCC_CLOUD` is required and identifies the correct API gateway.

**Supported ZCC Cloud Environments:**

- `zscaler`, `zscalerone`, `zscalertwo`, `zscalerthree`
- `zscloud`, `zscalerbeta`, `zscalergov`, `zscalerten`, `zspreview`

##### ZDX Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZDX_CLIENT_ID` | Yes | ZDX key ID |
| `ZDX_CLIENT_SECRET` | Yes | ZDX secret key |
| `ZDX_CLOUD` | Yes | Zscaler cloud name prefix |

**Where to find ZDX credentials:**

- ZDX Portal > API Keys section

#### Legacy Mode Behavior

When `ZSCALER_USE_LEGACY=true`:

- All tools use legacy API clients by default
- You can override per-tool by setting `use_legacy: false` in tool parameters
- The MCP server initializes without creating clients at startup
- Clients are created on-demand when individual tools are called
- This allows the server to work with different legacy services without requiring a specific service during initialization

---

### Authentication Troubleshooting

**Common Issues:**

1. **"Authentication failed" errors:**
   - Verify all required environment variables are set
   - Check that credentials are correct and not expired
   - Ensure you're using the correct cloud environment

2. **"Legacy credentials ignored" warning:**
   - This is normal when using OneAPI mode
   - Legacy credentials are only loaded when `ZSCALER_USE_LEGACY=true`

3. **"OneAPI credentials ignored" warning:**
   - This is normal when using Legacy mode
   - OneAPI credentials are only used when `ZSCALER_USE_LEGACY` is not set or is `false`

4. **Mixed authentication errors:**
   - **DO NOT** set both OneAPI and Legacy credentials
   - **DO NOT** set `ZSCALER_USE_LEGACY=true` if using OneAPI
   - Choose ONE method and stick with it

### MCP Server Configuration

The following environment variables control MCP server behavior (not authentication):

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ZSCALER_MCP_TRANSPORT` | `stdio` | Transport protocol to use (`stdio`, `sse`, or `streamable-http`) |
| `ZSCALER_MCP_SERVICES` | `""` | Comma-separated list of services to enable (empty = all services). Supported values: `zcc`, `zdx`, `zia`, `zidentity`, `zpa`, `ztw` |
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

## Additional Deployment Options

### Amazon Bedrock AgentCore

> [!IMPORTANT]
> **AWS Marketplace Image Available**: For Amazon Bedrock AgentCore deployments, we provide a dedicated container image optimized for Bedrock's stateless HTTP environment. This image includes a custom web server wrapper that handles session management and is specifically designed for AWS Bedrock AgentCore Runtime.

**🚀 Quick Start with AWS Marketplace:**

The easiest way to deploy the Zscaler Integrations MCP Server to Amazon Bedrock AgentCore is through the [AWS Marketplace listing](https://aws.amazon.com/marketplace/pp/prodview-dtjfklwemb54y?sr=0-1&ref_=beagle&applicationId=AWSMPContessa). The Marketplace image includes:

- ✅ Pre-configured for Bedrock AgentCore Runtime
- ✅ Custom web server wrapper for stateless HTTP environments
- ✅ Session management handled automatically
- ✅ Health check endpoints for ECS compatibility
- ✅ Optimized for AWS Bedrock AgentCore's requirements

**📚 Full Deployment Guide:**

For detailed deployment instructions, IAM configuration, and troubleshooting, please refer to the comprehensive [Amazon Bedrock AgentCore deployment guide](./docs/deployment/amazon_bedrock_agentcore.md).

The deployment guide covers:

- Prerequisites and AWS VPC requirements
- IAM role and trust policy configuration
- Step-by-step deployment instructions
- Environment variable configuration
- Write mode configuration (for CREATE/UPDATE/DELETE operations)
- Troubleshooting and verification steps

> [!NOTE]
> The AWS Marketplace image uses a different architecture than the standard `streamable-http` transport. It includes a FastAPI-based web server wrapper (`web_server.py`) that bypasses the MCP protocol's session initialization requirements, making it compatible with Bedrock's stateless HTTP environment. This is why the Marketplace image is recommended for Bedrock deployments.

## Using the MCP Server with Agents

This section provides instructions for configuring the Zscaler Integrations MCP Server with popular AI agents. **Before starting, ensure you have:**

1. ✅ Completed [Installation & Setup](#installation-setup)
2. ✅ Configured [Authentication](#zscaler-api-credentials-authentication)
3. ✅ Created your `.env` file with credentials

### Claude Desktop

You can install the Zscaler MCP Server in Claude Desktop using either method:

#### Option 1: Install as Extension (Recommended)

1. Open Claude Desktop
2. Go to **Settings** → **Extensions** → **Browse Extensions**
3. In the search box, type `zscaler`
4. Select **Zscaler MCP Server** from the results
5. Click **Install** or **Add**
6. Configure your `.env` file path when prompted (or edit the configuration after installation)
7. Restart Claude Desktop completely (quit and reopen)
8. Verify by asking Claude: "What Zscaler tools are available?"

#### Option 2: Manual Configuration

1. Open Claude Desktop
2. Go to **Settings** → **Developer** → **Edit Config**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/absolute/path/to/your/.env", "zscaler-mcp-server"]
    }
  }
}
```

> **Important**: Replace `/absolute/path/to/your/.env` with the **absolute path** to your `.env` file. Relative paths will not work.

1. Save the configuration file
2. Restart Claude Desktop completely (quit and reopen)
3. Verify by asking Claude: "What Zscaler tools are available?"

**Troubleshooting:**

- **"MCP server not found"**: Verify the `.env` file path is absolute and correct
- **"Authentication failed"**: Check that your `.env` file contains valid credentials
- **Tools not appearing**: Check Claude Desktop logs (Help > View Logs) for errors
- **Extension not found**: Ensure you're searching in the "Desktop extensions" tab, not "Web"

### Cursor

1. Open Cursor
2. Go to **Settings** → **Cursor Settings** → **Tools & MCP** → **New MCP Server**
3. The configuration will be saved to `~/.cursor/mcp.json`. Add the following configuration:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/absolute/path/to/your/.env", "zscaler-mcp-server"]
    }
  }
}
```

> **Alternative**: You can also use Docker instead of `uvx`:
>
> ```json
> {
>   "mcpServers": {
>     "zscaler-mcp-server": {
>       "command": "docker",
>       "args": [
>         "run",
>         "-i",
>         "--rm",
>         "--env-file",
>         "/absolute/path/to/your/.env",
>         "quay.io/zscaler/zscaler-mcp-server:latest"
>       ]
>     }
>   }
> }
> ```

1. Save the configuration file
2. Restart Cursor completely (quit and reopen)
3. Verify by asking: "List my ZIA rule labels"

**Troubleshooting:**

- Check Cursor's MCP logs (View > Output > MCP) for connection errors
- Verify the `.env` file path is absolute and credentials are correct
- The configuration file is located at `~/.cursor/mcp.json` (or `%USERPROFILE%\.cursor\mcp.json` on Windows)

### General Troubleshooting for All Agents

**Common Issues:**

1. **"Command not found: uvx"**
   - Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Or use Docker: Replace `uvx` with `docker run --rm --env-file /path/to/.env quay.io/zscaler/zscaler-mcp-server:latest`

2. **".env file not found"**
   - Use absolute paths, not relative paths
   - Verify the file exists at the specified path
   - Check file permissions (should be readable)

3. **"Authentication failed"**
   - Verify all required environment variables are in `.env`
   - Check that credentials are correct and not expired
   - Ensure you're using the correct authentication method (OneAPI vs Legacy)

4. **"Tools not appearing"**
   - Some agents require you to enable tools in their UI
   - Check agent logs for connection errors
   - Verify the MCP server is running (check agent's MCP status)

5. **"Server connection timeout"**
   - Ensure the MCP server can start successfully
   - Test manually: `uvx --env-file /path/to/.env zscaler-mcp-server`
   - Check for port conflicts if using HTTP transports

**Getting Help:**

- Check agent-specific logs (usually in Help/View menu)
- Test the server manually to isolate agent vs server issues
- Review the [Troubleshooting](#troubleshooting) section for more details
