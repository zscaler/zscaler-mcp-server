# Deploying to Google Cloud (Cloud Run, Vertex AI Agent Engine, and Agentspace)

The Zscaler MCP Server can be deployed to Google Cloud using the [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit).

## Overview

Google ADK provides a framework for building and deploying AI agents that can leverage tools from MCP servers. The Zscaler MCP Server integrates seamlessly with ADK, enabling deployment to:

- **Google Cloud Run** - Containerized deployment with automatic scaling
- **Vertex AI Agent Engine** - Managed AI agent runtime
- **Agentspace** - Enterprise agent management and access control

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            Google ADK Agent (agent.py)                   │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │   LlmAgent (Gemini/Vertex AI)                   │    │    │
│  │  │   └── MCPToolset                                │    │    │
│  │  │       └── StdioConnectionParams                 │    │    │
│  │  │           └── zscaler-mcp (via stdio)           │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

The ADK agent wraps the Zscaler MCP Server, which runs as a subprocess and communicates via stdio (standard I/O). This means **no modifications to the MCP server are required** - it works with the standard installation.

## Quick Start

For detailed instructions, refer to the [Google ADK example](../../examples/adk/README.md).

### Prerequisites

- Python 3.11+
- Google Cloud account with billing enabled
- Zscaler API credentials (from Zidentity console)
- Google AI API key (for local development) or Vertex AI access (for cloud deployment)

### Local Development

```bash
# Clone the repository
git clone https://github.com/zscaler/zscaler-mcp-server.git
cd zscaler-mcp-server/examples/adk

# Setup environment
python3 -m venv .venv
. .venv/bin/activate
pip install -r zscaler_agent/requirements.txt

# Configure and run
chmod +x adk_agent_operations.sh
./adk_agent_operations.sh  # Creates .env template
# Edit zscaler_agent/.env with your credentials
./adk_agent_operations.sh local_run
```

### Cloud Run Deployment

```bash
./adk_agent_operations.sh cloudrun_deploy
```

### Vertex AI Agent Engine Deployment

```bash
./adk_agent_operations.sh agent_engine_deploy
```

### Agentspace Registration

```bash
./adk_agent_operations.sh agentspace_register
```

## Configuration

The agent is configured via environment variables in `zscaler_agent/.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `ZSCALER_CLIENT_ID` | Yes | Zscaler OAuth client ID |
| `ZSCALER_CLIENT_SECRET` | Yes | Zscaler OAuth client secret |
| `ZSCALER_VANITY_DOMAIN` | Yes | Your Zscaler vanity domain |
| `ZSCALER_CUSTOMER_ID` | ZPA only | Required only for ZPA service |
| `ZSCALER_MCP_SERVICES` | No | Comma-separated list of services to enable |
| `GOOGLE_MODEL` | Yes | Gemini model to use (e.g., `gemini-2.0-flash`) |
| `GOOGLE_API_KEY` | Local only | Required for local development |
| `PROJECT_ID` | Cloud only | GCP project ID |
| `REGION` | Cloud only | GCP region (e.g., `us-central1`) |

## Available Zscaler Services

The agent can access the following Zscaler services:

| Service | Description |
|---------|-------------|
| `zia` | Zscaler Internet Access - Firewall, URL filtering, DLP |
| `zpa` | Zscaler Private Access - Application segments, policies |
| `zdx` | Zscaler Digital Experience - Device monitoring, alerts |
| `zcc` | Zscaler Client Connector - Device enrollment |
| `zeasm` | External Attack Surface Management - Findings, lookalike domains |
| `zidentity` | Identity management - Users, groups |
| `ztw` | Zscaler Workload Communications - Workload segmentation |

To limit which services are available, set `ZSCALER_MCP_SERVICES` in your `.env` file:

```bash
ZSCALER_MCP_SERVICES=zia,zpa,zdx
```

## Security Considerations

1. **Credentials**: Store Zscaler credentials securely. For Cloud Run, consider using [Secret Manager](https://cloud.google.com/secret-manager).

2. **Access Control**:
   - Cloud Run: Enable IAM authentication (default)
   - Agentspace: Use Discovery Engine User role

3. **Read-Only Mode**: The MCP server operates in read-only mode by default. Write operations require explicit enablement.

## Troubleshooting

### Agent fails to start

- Verify all required environment variables are set
- Check Zscaler credentials are valid
- Ensure `zscaler-mcp` package is installed

### Tools not appearing

- Check `ZSCALER_MCP_SERVICES` configuration
- Verify Zscaler API permissions
- Enable debug logging: `ZSCALER_MCP_DEBUG=true`

### Cloud Run deployment fails

- Ensure required GCP APIs are enabled
- Check IAM permissions
- Verify billing is enabled

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/docs/agents)
- [Agentspace Documentation](https://cloud.google.com/agentspace)
- [Zscaler API Documentation](https://help.zscaler.com/oneapi)
