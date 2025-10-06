![Zscaler MCP](https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/docs/media/zscaler.svg)

[![PyPI version](https://badge.fury.io/py/zscaler-mcp.svg)](https://badge.fury.io/py/zscaler-mcp)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zscaler-mcp)](https://pypi.org/project/zscaler-mcp/)
[![Documentation Status](https://readthedocs.org/projects/zscaler-mcp-server/badge/?version=latest)](https://zscaler-mcp-server.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/github/license/zscaler/zscaler-mcp-server.svg)](https://github.com/zscaler/zscaler-mcp-server)
[![Zscaler Community](https://img.shields.io/badge/zscaler-community-blue)](https://community.zscaler.com/)

**zscaler-mcp-server** is a Model Context Protocol (MCP) server that connects AI agents with the Zscaler Zero Trust Exchange platform.

## Support Disclaimer

-> **Disclaimer:** Please refer to our [General Support Statement](docs/guides/support.md) before proceeding with the use of this provider. You can also refer to our [troubleshooting guide](docs/guides/troubleshooting.md) for guidance on typical problems.

> [!IMPORTANT]
> **🚧 Public Preview**: This project is currently in public preview and under active development. Features and functionality may change before the stable 1.0 release. While we encourage exploration and testing, please avoid production deployments. We welcome your feedback through [GitHub Issues](https://github.com/zscaler/zscaler-mcp-server/issues) to help shape the final release.

## 📄 Table of contents

- [📺 Overview](#-overview)
- [⚙️ Supported Tools](#️-supported-tools)
  - [ZCC Features](#zcc-features)
  - [ZDX Features](#zdx-features)
  - [ZIdentity Features](#zidentity-features)
  - [ZIA Features](#zia-features)
  - [ZPA Features](#zpa-features)
  - [ZTW Features](#ztw-features)
- [Installation & Setup](#installation--setup)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Installation](#installation)
- [Usage](#usage)
  - [Command Line](#command-line)
  - [Service Configuration](#service-configuration)
  - [Additional Command Line Options](#additional-command-line-options)
- [Zscaler API Credentials & Authentication](#zscaler-api-credentials--authentication)
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
  - [Legacy Authentication](#legacy-authentication-when-zscaler_use_legacytrue)
- [As a Library](#as-a-library)
- [🐳 Container Usage](#container-usage)
  - [Using Pre-built Image (Recommended)](#using-pre-built-image-recommended)
  - [Building Locally (Development)](#building-locally-development)
- [🔧 Editor/Assistant Integration](#editorassistant-integration)
  - [Using `uvx` (recommended)](#using-uvx-recommended)
  - [With Service Selection](#with-service-selection)
  - [Using Individual Environment Variables](#using-individual-environment-variables)
  - [Docker Version](#docker-version)
- [🚀 Additional Deployment Options](#additional-deployment-options)
  - [Amazon Bedrock AgentCore](#amazon-bedrock-agentcore)
- [🔦 Using the MCP Server with Agents](#-using-the-mcp-server-with-agents)
  - [🧠 Claude](#-claude)
  - [💻 Cursor](#-cursor)
  - [Visual Studio Code + GitHub Copilot](#visual-studio-code--github-copilot)
- [📝 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#contributing)
  - [Getting Started for Contributors](#getting-started-for-contributors)
  - [Running Tests](#running-tests)
- [📄 License](#license)

## 📺 Overview

The Zscaler Integrations MCP Server brings context to your agents. Try prompts like:

- "List my ZPA Application segments"
- "List my ZPA Segment Groups"
- "List my ZIA Rule Labels"

## ⚙️ Supported Tools

The Zscaler Integrations MCP Server provides tools for all major Zscaler services. Each service offers specific functionality for managing and querying Zscaler resources.

### ZCC Features

| Tool Name | Description |
|-----------|-------------|
| `zcc_list_devices` | Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal |
| `zcc_devices_csv_exporter` | Downloads ZCC device information or service status as a CSV file |
| `zcc_list_trusted_networks` | Returns the list of Trusted Networks By Company ID in the Client Connector Portal |
| `zcc_list_forwarding_profiles` | Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal |

### ZDX Features

| Tool Name | Description |
|-----------|-------------|
| `zdx_administration` | Discover ZDX departments or locations |
| `zdx_active_devices` | List ZDX devices using various filters |
| `zdx_list_applications` | List all active applications configured in ZDX |
| `zdx_list_application_score` | Get an application's ZDX score or score trend |
| `zdx_get_application_metric` | Retrieve ZDX metrics for an application (PFT, DNS, availability) |
| `zdx_get_application_user` | List users/devices for an app or details for a specific user |
| `zdx_list_software_inventory` | List software inventory or users/devices for a software key |
| `zdx_list_alerts` | List ongoing alerts, get alert details, or list affected devices |
| `zdx_list_historical_alerts` | List historical alert rules (ended alerts) |
| `zdx_list_deep_traces` | Retrieve deep trace information for troubleshooting device connectivity issues |

### ZIdentity Features

| Tool Name | Description |
|-----------|-------------|
| `zidentity_groups` | Retrieves Zidentity group information |
| `zidentity_users` | Retrieves Zidentity user information |

### ZIA Features

| Tool Name | Description |
|-----------|-------------|
| `zia_activation` | Tool to check or activate ZIA configuration changes |
| `zia_atp_malicious_urls` | Manages the malicious URL denylist in the ZIA Advanced Threat Protection (ATP) policy |
| `zia_auth_exempt_urls` | Manages the list of cookie authentication exempt URLs in ZIA |
| `zia_cloud_applications` | Tool for managing ZIA Shadow IT Cloud Applications |
| `zia_cloud_firewall_rule` | Manages ZIA Cloud Firewall Rules |
| `zia_geo_search` | Performs geographical lookup actions using the ZIA Locations API |
| `zia_gre_range` | Tool for discovering available GRE internal IP ranges in ZIA |
| `zia_gre_tunnels` | Tool for managing ZIA GRE Tunnels and associated static IPs |
| `zia_ip_destination_groups` | Manages ZIA IP Destination Groups |
| `zia_ip_source_group` | Performs CRUD operations on ZIA IP Source Groups |
| `zia_user_groups` | Lists and retrieves ZIA User Groups with pagination, filtering and sorting |
| `zia_user_departments` | Lists and retrieves ZIA User Departments with pagination, filtering and sorting |
| `zia_users` | Lists ZIA Users with filtering and pagination |
| `zia_location_management` | Tool for managing ZIA Locations |
| `zia_network_app_group` | Manages ZIA Network Application Groups |
| `zia_rule_labels` | Tool for managing ZIA Rule Labels |
| `zia_sandbox_info` | Tool for retrieving ZIA Sandbox information |
| `zia_static_ips` | Tool for managing ZIA Static IP addresses |
| `zia_url_categories` | Tool for managing ZIA URL Categories |
| `zia_vpn_credentials` | Tool for managing ZIA VPN Credentials |

### ZPA Features

| Tool Name | Description |
|-----------|-------------|
| `zpa_access_policy` | CRUD handler for ZPA Access Policy Rules |
| `zpa_app_connector_groups` | CRUD handler for ZPA App Connector Groups |
| `zpa_app_protection_policy` | CRUD handler for ZPA Inspection Policy Rules |
| `zpa_app_protection_profiles` | Tool for listing and searching ZPA App Protection Profiles (Inspection Profiles) |
| `zpa_app_segments_by_type` | Tool to retrieve ZPA application segments by type |
| `zpa_application_segments` | CRUD handler for ZPA Application Segments |
| `zpa_application_servers` | Tool for managing ZPA Application Servers |
| `zpa_ba_certificates` | Tool for managing ZPA Browser Access (BA) Certificates |
| `zpa_enrollment_certificates` | Get-only tool for retrieving ZPA Enrollment Certificates |
| `zpa_forwarding_policy` | CRUD handler for ZPA Client Forwarding Policy Rules |
| `zpa_isolation_policy` | CRUD handler for ZPA Isolation Policy Rules |
| `zpa_isolation_profile` | Tool for retrieving ZPA Cloud Browser Isolation (CBI) profiles |
| `zpa_posture_profiles` | Tool for retrieving ZPA Posture Profiles |
| `zpa_pra_credentials` | Tool for managing ZPA Privileged Remote Access (PRA) Credentials |
| `zpa_pra_portals` | Tool for managing ZPA Privileged Remote Access (PRA) Portals |
| `zpa_provisioning_key` | Tool for managing ZPA Provisioning Keys |
| `zpa_saml_attributes` | Tool for querying ZPA SAML Attributes |
| `zpa_scim_attributes` | Tool for managing ZPA SCIM Attributes |
| `zpa_scim_groups` | Tool for retrieving ZPA SCIM groups under a given Identity Provider (IdP) |
| `zpa_segment_groups` | Tool for managing Segment Groups |
| `zpa_server_groups` | CRUD handler for ZPA Server Groups |
| `zpa_service_edge_groups` | CRUD handler for ZPA Service Edge Groups |
| `zpa_timeout_policy` | CRUD handler for ZPA Timeout Policy Rules |
| `zpa_trusted_networks` | Tool for retrieving ZPA Trusted Networks |

### ZTW Features

| Tool Name | Description |
|-----------|-------------|
| `ztw_ip_destination_groups` | Manages ZTW IP Destination Groups |
| `ztw_ip_group` | Manages ZTW IP Groups |
| `ztw_ip_source_groups` | Manages ZTW IP Source Groups |
| `ztw_network_service_groups` | Manages ZTW Network Service Groups |
| `ztw_list_roles` | List all existing admin roles in Zscaler Cloud & Branch Connector (ZTW) |
| `ztw_list_admins` | List all existing admin users or get details for a specific admin user in Zscaler Cloud & Branch Connector (ZTW) |

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

#### Install using uv (recommended)

```bash
uv tool install zscaler-mcp-server
```

> **Note**: This method requires the package to be published to PyPI. Currently, this package is in development and not yet published. Use one of the source installation methods below.

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

For installation via code editors/assistants, see the [Using the MCP Server with Agents](#-using-the-mcp-server-with-agents) section below.

## Usage

### Command Line

Run the server with default settings (stdio transport):

```bash
zscaler-mcp
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

For all available options:

```bash
zscaler-mcp --help
```

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
| `ZSCALER_MCP_DEBUG` | `false` | Enable debug logging (`true`/`false`) |
| `ZSCALER_MCP_HOST` | `127.0.0.1` | Host to bind to for HTTP transports |
| `ZSCALER_MCP_PORT` | `8000` | Port to listen on for HTTP transports |
| `ZSCALER_MCP_USER_AGENT_COMMENT` | `""` | Additional information to include in User-Agent comment section |

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

# Create and run the server
server = ZscalerMCPServer(
    debug=True,  # Optional, enable debug logging
    enabled_services={"zia", "zpa", "zdx"},  # Optional, defaults to all services
    enabled_tools={"zia_rule_labels", "zpa_application_segments"},  # Optional, defaults to all tools
    user_agent_comment="My Custom App"  # Optional, additional User-Agent info
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

## 🔦 Using the MCP Server with Agents

Once your server is running (via Docker or source), you can access its tools through AI-integrated editors or platforms.

### 🧠 Claude

1. Open Claude
2. In Chat, select the "Search & Tools"
3. The server appears in the tools list `zscaler-mcp-server`
4. Try prompts like "List ZPA Segment Groups" or "List ZIA Rule Labels"
5. Select the tool and click "Submit"

### 💻 Cursor

1. Open Cursor, then settings
2. In Curos Settings, select "Tools & Integrations"
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

## 📝 Troubleshooting

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
